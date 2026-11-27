"""Durable capability receipt measurements. Node-local RTT is a one-way upper bound."""
import csv
import io
import json
import math
import re
import time
import uuid

IDENTIFIER=re.compile(r'^[A-Za-z0-9_-]{1,32}$')
TERMINAL={'PASS','UPPER_BOUND_EXCEEDED','TIMEOUT','ERROR','NOT_READY','INTERRUPTED'}


class CapabilityMeasurements:
    def __init__(self, store, node_info, send, *, clock=time.time):
        self.store,self.node_info,self.send,self.clock=store,node_info,send,clock
        with store.lock,store.db:
            store.db.executescript('''
                CREATE TABLE IF NOT EXISTS cap_batches (
                    batch_id TEXT PRIMARY KEY, canonical TEXT NOT NULL, created REAL NOT NULL,
                    count INTEGER NOT NULL, period_ms INTEGER NOT NULL, nodes TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS cap_probes (
                    probe_id TEXT PRIMARY KEY, batch_id TEXT NOT NULL, node_id TEXT NOT NULL,
                    boot_id TEXT NOT NULL, ordinal INTEGER NOT NULL, state TEXT NOT NULL,
                    sent REAL, cap_id TEXT, error TEXT);
                CREATE INDEX IF NOT EXISTS cap_probe_batch ON cap_probes(batch_id,ordinal);
                CREATE TABLE IF NOT EXISTS cap_announcements (
                    node_id TEXT NOT NULL, cap_id TEXT NOT NULL, boot_id TEXT NOT NULL,
                    cap_seq INTEGER NOT NULL, sent_us INTEGER NOT NULL, raw TEXT NOT NULL,
                    received REAL NOT NULL, registered REAL NOT NULL, token TEXT NOT NULL,
                    probe_id TEXT, elapsed_us INTEGER, confirmed_us INTEGER, result_raw TEXT,
                    error TEXT, duplicates INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY(node_id,cap_id));
            ''')
            store.db.execute("UPDATE cap_probes SET state='INTERRUPTED',error='manager_restarted' WHERE state IN ('WAIT','SENT','RECEIVED')")

    def start(self, body):
        if not isinstance(body,dict) or set(body)-{'batch_id','nodes','count','period_ms'}:
            raise ValueError('invalid_capability_test_fields')
        batch=body.get('batch_id');nodes=body.get('nodes');count=body.get('count',30);period=body.get('period_ms',1000)
        if not isinstance(batch,str) or not re.fullmatch('[0-9a-f]{32}',batch):raise ValueError('invalid_batch_id')
        if (not isinstance(nodes,list) or not 1<=len(nodes)<=16 or any(not isinstance(n,str) or not IDENTIFIER.fullmatch(n) for n in nodes)
                or len(set(nodes))!=len(nodes)):raise ValueError('select_1_to_16_distinct_nodes')
        if type(count) is not int or not 1<=count<=100:raise ValueError('count_must_be_1_to_100')
        if type(period) is not int or not 200<=period<=10000:raise ValueError('period_ms_must_be_200_to_10000')
        canonical=json.dumps(dict(nodes=nodes,count=count,period_ms=period),sort_keys=True)
        with self.store.lock,self.store.db:
            old=self.store.db.execute('SELECT canonical FROM cap_batches WHERE batch_id=?',(batch,)).fetchone()
            if old:
                if old[0]!=canonical:raise ValueError('batch_id_conflict')
                return self.get(batch)
            if self.store.db.execute("SELECT 1 FROM cap_probes WHERE state IN ('WAIT','SENT','RECEIVED') LIMIT 1").fetchone():
                raise ValueError('capability_test_already_running')
            info={node:self.node_info(node) for node in nodes}
            if any(not v or not v.get('ready') or not v.get('supported') or not isinstance(v.get('boot_id'),str)
                   or not re.fullmatch('[0-9a-f]{16}',v['boot_id']) for v in info.values()):
                raise ValueError('node_not_ready_or_measurement_firmware_required')
            self.store.db.execute('INSERT INTO cap_batches VALUES (?,?,?,?,?,?)',
                                  (batch,canonical,self.clock(),count,period,json.dumps(nodes)))
            for ordinal in range(count):
                for node in nodes:
                    self.store.db.execute('INSERT INTO cap_probes VALUES (?,?,?,?,?,?,NULL,NULL,NULL)',
                        (uuid.uuid4().hex,batch,node,info[node]['boot_id'],ordinal,'WAIT'))
        return self.get(batch)

    def tick(self):
        now=self.clock()
        with self.store.lock,self.store.db:
            self.store.db.execute("UPDATE cap_probes SET state='TIMEOUT',error='confirmation_missing' WHERE state IN ('SENT','RECEIVED') AND sent<?",(now-5,))
            waiting=self.store.db.execute("SELECT p.*,b.period_ms FROM cap_probes p JOIN cap_batches b USING(batch_id) WHERE state='WAIT' AND ordinal=(SELECT MIN(q.ordinal) FROM cap_probes q WHERE q.batch_id=p.batch_id AND q.node_id=p.node_id AND q.state='WAIT') ORDER BY ordinal,node_id").fetchall()
        for row in waiting:
            node=row['node_id']
            with self.store.lock:
                busy=self.store.db.execute("SELECT 1 FROM cap_probes WHERE node_id=? AND state IN ('SENT','RECEIVED')",(node,)).fetchone()
                last=self.store.db.execute('SELECT MAX(sent) FROM cap_probes WHERE batch_id=? AND node_id=?',(row['batch_id'],node)).fetchone()[0]
            if busy or (last is not None and now-last<row['period_ms']/1000):continue
            info=self.node_info(node)
            valid=bool(info and info.get('ready') and info.get('supported') and info.get('boot_id')==row['boot_id'])
            with self.store.lock,self.store.db:
                self.store.db.execute('UPDATE cap_probes SET state=?,sent=?,error=? WHERE probe_id=? AND state=\'WAIT\'',
                    ('SENT' if valid else 'NOT_READY',now,None if valid else 'node_unavailable_or_rebooted',row['probe_id']))
            if not valid:continue
            packet=dict(v=1,type='cap.request',target=node,boot_id=row['boot_id'],batch_id=row['batch_id'],
                        probe_id=row['probe_id'],deadline_unix=int(now)+10)
            try:sent=self.send(node,packet)
            except (OSError,ValueError):sent=False
            if not sent:
                with self.store.lock,self.store.db:
                    self.store.db.execute("UPDATE cap_probes SET state='ERROR',error='request_publish_failed' WHERE probe_id=?",(row['probe_id'],))

    def announcement(self,node,body,retained,received,*,wire=None):
        """Called only after Registry.receive accepted the topic-bound capability."""
        if (retained or type(body.get('v')) is not int or body.get('v')!=1 or body.get('type')!='capabilities' or body.get('node_id')!=node or
                type(body.get('cap_measure_v')) is not int or body.get('cap_measure_v')!=1):return
        info=self.node_info(node)
        if not info:return
        if (not isinstance(body.get('task_types'),list) or not body['task_types'] or
                not all(isinstance(kind,str) for kind in body['task_types']) or
                body.get('task_status') not in ('IDLE','ACCEPTED','RUNNING','PAUSED','UNKNOWN','SUCCEEDED','FAILED','CANCELLED','REJECTED')):return
        cap=body.get('cap_id');boot=body.get('boot_id');seq=body.get('cap_seq');sent=body.get('sent_us')
        if (not isinstance(cap,str) or not IDENTIFIER.fullmatch(cap) or not isinstance(boot,str) or not re.fullmatch('[0-9a-f]{16}',boot)
                or type(seq) is not int or not 1<=seq<=0xffffffff or type(sent) is not int or not 0<=sent<2**53
                or cap!=f'{boot}-{seq:08x}' or body.get('task_role')!=info['role']):return
        raw=json.dumps(body if wire is None else wire,sort_keys=True,separators=(',',':'),allow_nan=False)
        probe=body.get('probe_id');batch=body.get('batch_id')
        if probe is not None and (not isinstance(probe,str) or not IDENTIFIER.fullmatch(probe)):return
        with self.store.lock,self.store.db:
            previous=self.store.db.execute('SELECT * FROM cap_announcements WHERE node_id=? AND cap_id=?',(node,cap)).fetchone()
            if previous:
                if previous['raw']!=raw:return
                self.store.db.execute('UPDATE cap_announcements SET duplicates=duplicates+1 WHERE node_id=? AND cap_id=?',(node,cap))
                token=previous['token']
            else:
                if probe is not None:
                    p=self.store.db.execute('SELECT * FROM cap_probes WHERE probe_id=?',(probe,)).fetchone()
                    if not p or p['node_id']!=node or p['boot_id']!=boot or p['batch_id']!=batch or p['state']!='SENT':return
                elif batch is not None:return
                token=uuid.uuid4().hex
                self.store.db.execute('INSERT INTO cap_announcements(node_id,cap_id,boot_id,cap_seq,sent_us,raw,received,registered,token,probe_id) VALUES(?,?,?,?,?,?,?,?,?,?)',
                    (node,cap,boot,seq,sent,raw,received,self.clock(),token,probe))
                if probe:
                    self.store.db.execute("UPDATE cap_probes SET state='RECEIVED',cap_id=? WHERE probe_id=?",(cap,probe))
        # Commit precedes the application receipt. PUBACK alone is never used as evidence.
        try:self.send(node,dict(v=1,type='cap.receipt',target=node,boot_id=boot,cap_id=cap,cap_seq=seq,receipt_token=token))
        except (OSError,ValueError):pass

    def result(self,node,body,retained=False):
        if retained or not self.node_info(node) or type(body.get('v')) is not int or body.get('v')!=1 or body.get('type')!='cap.result' or body.get('node_id')!=node:return
        cap=body.get('cap_id')
        if not isinstance(cap,str) or not IDENTIFIER.fullmatch(cap):return
        with self.store.lock,self.store.db:
            row=self.store.db.execute('SELECT * FROM cap_announcements WHERE node_id=? AND cap_id=?',(node,cap)).fetchone()
            if (not row or row['result_raw'] is not None or body.get('boot_id')!=row['boot_id'] or
                type(body.get('cap_seq')) is not int or body['cap_seq']!=row['cap_seq']):return
            error=body.get('error')
            elapsed=body.get('elapsed_us');confirmed=body.get('confirmed_us')
            if error is None:
                if (body.get('receipt_token')!=row['token'] or body.get('cap_seq')!=row['cap_seq'] or
                    type(elapsed) is not int or type(confirmed) is not int or not 0<=elapsed<=2000000 or
                    confirmed-row['sent_us']!=elapsed):return
            elif error!='receipt_timeout':return
            self.store.db.execute('UPDATE cap_announcements SET elapsed_us=?,confirmed_us=?,result_raw=?,error=? WHERE node_id=? AND cap_id=?',
                (elapsed if not error else None,confirmed if not error else None,json.dumps(body,separators=(',',':')),error,node,cap))
            if row['probe_id']:
                state='TIMEOUT' if error else ('PASS' if elapsed<=800000 else 'UPPER_BOUND_EXCEEDED')
                self.store.db.execute("UPDATE cap_probes SET state=?,error=? WHERE probe_id=? AND state='RECEIVED'",(state,error,row['probe_id']))

    def list(self):
        with self.store.lock:
            return [dict(r) for r in self.store.db.execute('SELECT batch_id,created,count,period_ms,nodes FROM cap_batches ORDER BY created DESC LIMIT 50')]

    def get(self,batch,*,raw=False):
        with self.store.lock:
            head=self.store.db.execute('SELECT * FROM cap_batches WHERE batch_id=?',(batch,)).fetchone()
            if not head:raise ValueError('capability_test_not_found')
            rows=self.store.db.execute('''SELECT p.*,a.cap_seq,a.sent_us,a.confirmed_us,a.elapsed_us,a.received,a.registered,a.duplicates,
                a.raw,a.result_raw FROM cap_probes p LEFT JOIN cap_announcements a ON p.node_id=a.node_id AND p.cap_id=a.cap_id
                WHERE p.batch_id=? ORDER BY p.ordinal,p.node_id''',(batch,)).fetchall()
        items=[]
        for r in rows:
            item=dict(r);announcement=json.loads(item.pop('raw') or '{}');result=item.pop('result_raw')
            item.update(agent_type=announcement.get('task_role'),basic_capabilities=announcement.get('task_types',[]),
                        operations=announcement.get('operations',[]),task_status=announcement.get('task_status'),
                        elapsed_ms=item['elapsed_us']/1000 if item['elapsed_us'] is not None else None)
            if raw:item.update(announcement=announcement,result=json.loads(result) if result else None)
            items.append(item)
        values=sorted(r['elapsed_us'] for r in items if r['elapsed_us'] is not None and r['state'] in ('PASS','UPPER_BOUND_EXCEEDED'))
        states={s:sum(r['state']==s for r in items) for s in TERMINAL|{'WAIT','SENT','RECEIVED'}}
        summary=dict(total=len(items),registered=sum(r['cap_id'] is not None for r in items),confirmed=len(values),proved_within_800ms=states['PASS'],states=states,
            complete=all(r['state'] in TERMINAL for r in items),
            proved_percent=100*states['PASS']/len(items),
            all_proved=all(r['state']=='PASS' for r in items),
            avg_ms=sum(values)/len(values)/1000 if values else None,
            p95_ms=values[math.ceil(len(values)*.95)-1]/1000 if values else None,
            max_ms=max(values)/1000 if values else None)
        return dict(v=1,batch_id=batch,nodes=json.loads(head['nodes']),count=head['count'],period_ms=head['period_ms'],
                    created=head['created'],metric='capability_receipt_rtt_upper_bound',threshold_ms=800,summary=summary,items=items)

    def export(self,batch,format):
        body=self.get(batch,raw=True)
        if format=='jsonl':return '\n'.join(json.dumps(r,ensure_ascii=False) for r in [dict(kind='summary',**{k:v for k,v in body.items() if k!='items'}),*body['items']])+'\n'
        if format!='csv':raise ValueError('unsupported_export_format')
        output=io.StringIO(newline='');items=body['items']
        writer=csv.DictWriter(output,fieldnames=['metric','threshold_ms',*items[0].keys()]);writer.writeheader()
        for item in items:
            writer.writerow(dict(metric=body['metric'],threshold_ms=800,**{k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in item.items()}))
        return output.getvalue()
