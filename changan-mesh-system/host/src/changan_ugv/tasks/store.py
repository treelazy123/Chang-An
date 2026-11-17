"""M1 durable task lifecycle. No survey/patrol/media business types."""
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import threading
import time
import uuid
from changan_ugv.tasks.workflows import WORKFLOW_KINDS, MODE, config_valid as workflow_config

ID = re.compile(r'^[A-Za-z0-9_-]{1,32}$')
TERMINAL = {'SUCCEEDED', 'FAILED', 'CANCELLED', 'REJECTED', 'EXPIRED'}
ACTIVE = {'DISPATCHING', 'ACCEPTED', 'RUNNING', 'PAUSE_PENDING', 'PAUSED',
          'RESUME_PENDING', 'CANCEL_PENDING', 'RECONCILING', 'UNKNOWN'}
ACTIONS = {'task.create', 'task.get', 'task.list', 'task.control', 'task.update', 'task.events'}

def dumps(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), sort_keys=True, allow_nan=False)

def identifier(value):
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise ValueError('invalid_task_or_node_id')
    return value

HOST_KINDS = ('network_diagnostics', 'task_monitor')

def config_valid(value, kind='diagnostics'):
    if kind in WORKFLOW_KINDS:
        return workflow_config(value, kind)
    extra = {'network_diagnostics': {'probe_node'}, 'task_monitor': {'watch_task_id', 'stale_after_s'}}.get(kind, set())
    if not isinstance(value, dict) or set(value) - ({'duration_s', 'period_ms'} | extra):
        raise ValueError('invalid_config')
    value = dict(value, duration_s=value.get('duration_s', 30), period_ms=value.get('period_ms', 1000))
    if (type(value['duration_s']) is not int or not 1 <= value['duration_s'] <= 3600 or
        type(value['period_ms']) is not int or not 200 <= value['period_ms'] <= 10000):
        raise ValueError('invalid_config')
    if kind == 'network_diagnostics':
        identifier(value.get('probe_node'))
    if kind == 'task_monitor':
        identifier(value.get('watch_task_id'))
        value.setdefault('stale_after_s', 10)
        if type(value['stale_after_s']) is not int or not 1 <= value['stale_after_s'] <= 3600:
            raise ValueError('invalid_stale_after_s')
    return value

class Store:
    def __init__(self, path, clock=time.time):
        self.clock = clock
        self.lock = threading.RLock()
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY, owner TEXT NOT NULL, target TEXT NOT NULL,
                kind TEXT NOT NULL, state TEXT NOT NULL, revision INTEGER NOT NULL,
                config TEXT NOT NULL, priority INTEGER NOT NULL, execute_before INTEGER,
                created INTEGER NOT NULL, updated INTEGER NOT NULL, state_seq INTEGER NOT NULL DEFAULT 0,
                boot TEXT, node_seq INTEGER NOT NULL DEFAULT -1, progress INTEGER NOT NULL DEFAULT 0,
                result TEXT, error TEXT);
            CREATE TABLE IF NOT EXISTS operations (
                command_id TEXT PRIMARY KEY, task_id TEXT NOT NULL, op TEXT NOT NULL,
                status TEXT NOT NULL, packet TEXT, sent REAL, revision INTEGER NOT NULL, op_seq INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS requests (
                owner TEXT NOT NULL, msg_id TEXT NOT NULL, canonical TEXT NOT NULL, reply TEXT NOT NULL,
                PRIMARY KEY(owner,msg_id));
            CREATE TABLE IF NOT EXISTS task_events (
                cursor INTEGER PRIMARY KEY AUTOINCREMENT, owner TEXT NOT NULL,
                task_id TEXT NOT NULL, body TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS events_owner ON task_events(owner,cursor);
            CREATE TABLE IF NOT EXISTS deleted_tasks (
                task_id TEXT PRIMARY KEY, owner TEXT NOT NULL, revision INTEGER NOT NULL,
                state_seq INTEGER NOT NULL, deleted_at INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS task_sequence (
                singleton INTEGER PRIMARY KEY CHECK(singleton=1), last_rowid INTEGER NOT NULL);
            INSERT OR IGNORE INTO task_sequence SELECT 1, COALESCE(MAX(rowid),0) FROM tasks;
            CREATE TABLE IF NOT EXISTS incidents (
                cursor INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT UNIQUE NOT NULL,
                owner TEXT NOT NULL, source_task_id TEXT NOT NULL, node_id TEXT NOT NULL,
                area_id TEXT NOT NULL, point_id TEXT NOT NULL, created INTEGER NOT NULL);
        """)
        if 'feedback_at' not in {r[1] for r in self.db.execute('PRAGMA table_info(tasks)')}:
            self.db.execute('ALTER TABLE tasks ADD COLUMN feedback_at REAL')
        # Never replay an uncertain physical operation on manager restart.
        with self.lock, self.db:
            for row in self.db.execute("SELECT * FROM tasks WHERE state NOT IN ('CREATED','QUEUED','SUCCEEDED','FAILED','CANCELLED','REJECTED','EXPIRED')").fetchall():
                self._change(row['task_id'], state='RECONCILING', error='manager_restarted')
                self.db.execute("UPDATE operations SET status='uncertain' WHERE task_id=? AND status IN ('waiting','sent')", (row['task_id'],))

    def close(self):
        with self.lock:
            self.db.close()

    def _row(self, task_id, owner=None):
        row = self.db.execute('SELECT * FROM tasks WHERE task_id=?', (identifier(task_id),)).fetchone()
        if row is None or (owner not in (None, 'local-console') and row['owner'] != owner):
            raise ValueError('task_not_found')
        return dict(row)

    def view(self, row):
        keys = ('task_id', 'target', 'kind', 'state', 'revision', 'priority', 'execute_before',
                'created', 'updated', 'state_seq', 'progress', 'error')
        result = {k: row[k] for k in keys}
        operation=self.db.execute('SELECT command_id,op,status,op_seq FROM operations WHERE task_id=? ORDER BY rowid DESC LIMIT 1',(row['task_id'],)).fetchone()
        if operation:result['last_operation']=dict(operation)
        result['config'] = json.loads(row['config'])
        if row.get('feedback_at') is not None:
            result['feedback_at'] = row['feedback_at']
        if row['result']:
            result['result'] = json.loads(row['result'])
        return result

    def _event(self, task_id):
        row = self._row(task_id)
        body = {k: row[k] for k in ('task_id', 'state', 'revision', 'state_seq', 'progress', 'updated', 'error')}
        if row['result']:
            body['result'] = json.loads(row['result'])
        self.db.execute('INSERT INTO task_events(owner,task_id,body) VALUES(?,?,?)',
                        (row['owner'], task_id, dumps(body)))

    def _change(self, task_id, **fields):
        fields.update(updated=int(self.clock()), state_seq=self._row(task_id)['state_seq'] + 1)
        sql = ','.join(k + '=?' for k in fields)
        self.db.execute('UPDATE tasks SET ' + sql + ' WHERE task_id=?', (*fields.values(), task_id))
        self._event(task_id)

    def _operation(self, row, op):
        command_id = uuid.uuid4().hex
        sequence=self.db.execute('SELECT COALESCE(MAX(op_seq),0)+1 FROM operations WHERE task_id=?',(row['task_id'],)).fetchone()[0]
        self.db.execute('INSERT INTO operations VALUES(?,?,?,?,?,?,?,?)',
                        (command_id, row['task_id'], op, 'waiting', None, None, row['revision'],sequence))
        return command_id

    def request(self, packet, owner, targets):
        """Caller has authenticated source, TTL and frame limits. Mutations and replies commit together."""
        kind = packet['type']
        if not isinstance(kind,str) or kind not in ACTIONS:
            raise ValueError('unsupported_task_interface')
        common={'v','type','node_id','msg_id','deadline_unix'}
        fields={
            'task.create':{'task_id','target','kind','config','priority','execute_before'},
            'task.get':{'task_id'}, 'task.list':{'cursor'}, 'task.events':{'cursor','task_id','scope'},
            'task.control':{'task_id','op','expected_revision'},
            'task.update':{'task_id','expected_revision','config','priority','execute_before'},
        }
        if set(packet)-(common|fields[kind]):raise ValueError('unknown_task_fields')
        canonical = hashlib.sha256(dumps(packet).encode()).hexdigest()
        with self.lock, self.db:
            cached = self.db.execute('SELECT canonical,reply FROM requests WHERE owner=? AND msg_id=?',
                                     (owner, packet['msg_id'])).fetchone()
            if cached:
                if cached['canonical'] != canonical:
                    raise ValueError('msg_id_conflict')
                return json.loads(cached['reply'])
            result = self._request(packet, owner, targets)
            reply = dict(v=1, type='task.reply', node_id='ugv-service', msg_id=packet['msg_id'], ok=True, **result)
            from changan_ugv.protocol.frames import encode
            encode(reply)  # Roll back, rather than commit an unrepresentable reply.
            if kind in ('task.create', 'task.control', 'task.update'):
                self.db.execute('INSERT INTO requests VALUES(?,?,?,?)',
                                (owner, packet['msg_id'], canonical, dumps(reply)))
            return reply

    def _request(self, p, owner, targets):
        kind = p['type']
        if kind in ('task.list', 'task.events'):
            cursor = p.get('cursor', 0)
            if type(cursor) is not int or not 0 <= cursor <= 9223372036854775807:
                raise ValueError('invalid_cursor')
            # One result per response; no unbounded bursts through the C6 serial queue.
            scope, args = ('', []) if owner == 'local-console' else (' AND owner=?', [owner])
            event_scope = p.get('scope','tasks')
            if event_scope not in ('tasks','incidents'):
                raise ValueError('invalid_event_scope')
            if kind == 'task.events' and event_scope == 'incidents':
                task = p.get('task_id')
                if task is not None:
                    identifier(task)
                    scope += ' AND source_task_id=?'
                    args.append(task)
                rows = self.db.execute('SELECT * FROM incidents WHERE cursor>?' + scope + ' ORDER BY cursor LIMIT 2', [cursor,*args]).fetchall()
                items = [{k:r[k] for k in ('event_id','source_task_id','node_id','area_id','point_id','created')} | dict(test=True,execution_mode=MODE) for r in rows[:1]]
                return dict(items=items,cursor=rows[0]['cursor'] if rows else cursor,more=len(rows)>1)
            if kind == 'task.list':
                rows = self.db.execute('SELECT rowid AS cursor,* FROM tasks WHERE rowid>?' + scope + ' ORDER BY rowid LIMIT 2', [cursor, *args]).fetchall()
                items = [self.view(dict(row)) for row in rows[:1]]
            else:
                task = p.get('task_id')
                task_filter = ''
                if task is not None:
                    self._row(task, owner)
                    task_filter = ' AND task_id=?'
                    args.append(task)
                rows = self.db.execute('SELECT * FROM task_events WHERE cursor>?' + scope + task_filter + ' ORDER BY cursor LIMIT 2', [cursor, *args]).fetchall()
                items = [dict(json.loads(row['body']), cursor=row['cursor']) for row in rows[:1]]
            return dict(items=items, cursor=rows[0]['cursor'] if rows else cursor, more=len(rows) > 1)
        if kind == 'task.create':
            task_id = identifier(p.get('task_id'))
            if self.db.execute('SELECT 1 FROM deleted_tasks WHERE task_id=?', (task_id,)).fetchone():
                raise ValueError('task_id_deleted')
            target = identifier(p.get('target'))
            if target not in targets:
                raise ValueError('target_not_authorized')
            task_kind = p.get('kind')
            if task_kind not in ('diagnostics', *HOST_KINDS, *WORKFLOW_KINDS):
                raise ValueError('unsupported_task_kind')
            config = config_valid(p.get('config', {}), task_kind)
            self.validate_command_size(task_id,target,task_kind,config)
            self.validate_subject(config, task_kind, owner, targets)
            priority = p.get('priority', 0)
            before = p.get('execute_before')
            if type(priority) is not int or not 0 <= priority <= 9:
                raise ValueError('invalid_priority')
            if before is not None and (type(before) is not int or not self.clock() < before <= 2147483647):
                raise ValueError('invalid_execute_before')
            if self.db.execute('SELECT 1 FROM tasks WHERE task_id=?', (task_id,)).fetchone():
                raise ValueError('task_id_conflict')
            now = int(self.clock())
            # Deleted high-rowid tasks must not make task.list cursors miss new tasks.
            cursor = self.db.execute('SELECT last_rowid+1 FROM task_sequence WHERE singleton=1').fetchone()[0]
            self.db.execute('UPDATE task_sequence SET last_rowid=? WHERE singleton=1', (cursor,))
            self.db.execute('INSERT INTO tasks(rowid,task_id,owner,target,kind,state,revision,config,priority,execute_before,created,updated) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                            (cursor, task_id, owner, target, task_kind, 'CREATED', 1, dumps(config), priority, before, now, now))
            self._event(task_id)
            return dict(stage='UGV_RECEIVED', task=self.view(self._row(task_id)))
        if kind == 'task.control' and p.get('op') == 'delete':
            return self._delete(p, owner)
        row = self._row(p.get('task_id'), owner)
        if kind == 'task.get':
            return dict(task=self.view(row))
        if row['target'] not in targets:
            raise ValueError('target_not_authorized')
        if p.get('expected_revision') != row['revision'] or type(p.get('expected_revision')) is not int:
            raise ValueError('revision_conflict')
        if kind == 'task.update':
            # M1 updates are intentionally limited to not-yet-started tasks.
            if row['state'] != 'CREATED':
                raise ValueError('update_requires_created')
            config = config_valid(p.get('config', json.loads(row['config'])), row['kind'])
            self.validate_command_size(row['task_id'],row['target'],row['kind'],config)
            self.validate_subject(config, row['kind'], owner, targets)
            fields = {'config': dumps(config), 'revision': row['revision'] + 1}
            if 'priority' in p:
                if type(p['priority']) is not int or not 0 <= p['priority'] <= 9:
                    raise ValueError('invalid_priority')
                fields['priority'] = p['priority']
            if 'execute_before' in p:
                if p['execute_before'] is not None and (type(p['execute_before']) is not int or not self.clock() < p['execute_before'] <= 2147483647):
                    raise ValueError('invalid_execute_before')
                fields['execute_before'] = p['execute_before']
            self._change(row['task_id'], **fields)
            return dict(stage='APPLIED', task=self.view(self._row(row['task_id'])))
        op = p.get('op')
        if op == 'start' and row['state'] == 'CREATED':
            state = 'QUEUED'
        elif op == 'pause' and row['state'] == 'RUNNING':
            state = 'PAUSE_PENDING'
        elif op == 'resume' and row['state'] == 'PAUSED':
            state = 'RESUME_PENDING'
        elif op == 'cancel' and row['state'] in ('CREATED', 'QUEUED'):
            self.db.execute("UPDATE operations SET status='cancelled' WHERE task_id=?", (row['task_id'],))
            self._change(row['task_id'], state='CANCELLED')
            return dict(stage='APPLIED', task=self.view(self._row(row['task_id'])))
        elif op == 'cancel' and row['state'] in ACTIVE:
            state = 'CANCEL_PENDING'
        else:
            raise ValueError('invalid_task_transition')
        if self.db.execute("SELECT 1 FROM operations WHERE task_id=? AND status IN ('waiting','sent')", (row['task_id'],)).fetchone():
            raise ValueError('operation_pending')
        command_id = self._operation(row, op)
        self._change(row['task_id'], state=state, error=None)
        return dict(stage='UGV_RECEIVED', command_id=command_id, task=self.view(self._row(row['task_id'])))

    def _delete(self, packet, owner):
        """Called inside request's transaction; physical execution is never controlled here."""
        task_id = identifier(packet.get('task_id'))
        removed = self.db.execute('SELECT * FROM deleted_tasks WHERE task_id=?', (task_id,)).fetchone()
        row = dict(removed) if removed else self._row(task_id, owner)
        if owner != 'local-console' and row['owner'] != owner:
            raise ValueError('task_not_found')
        if type(packet.get('expected_revision')) is not int or packet['expected_revision'] != row['revision']:
            raise ValueError('revision_conflict')
        if not removed:
            if row['state'] not in TERMINAL:
                raise ValueError('delete_requires_terminal')
            monitors = self.db.execute("SELECT config FROM tasks WHERE kind='task_monitor' AND state NOT IN ('SUCCEEDED','FAILED','CANCELLED','REJECTED','EXPIRED')").fetchall()
            if any(json.loads(m['config']).get('watch_task_id') == task_id for m in monitors):
                raise ValueError('task_in_use_by_monitor')
            reviews = self.db.execute("SELECT config FROM tasks WHERE kind='anomaly_review' AND state NOT IN ('SUCCEEDED','FAILED','CANCELLED','REJECTED','EXPIRED')").fetchall()
            if any(json.loads(r['config']).get('event_id') == task_id for r in reviews):
                raise ValueError('task_in_use_by_review')
            row['state_seq'] += 1
            self.db.execute('INSERT INTO deleted_tasks VALUES(?,?,?,?,?)',
                            (task_id,row['owner'],row['revision'],row['state_seq'],int(self.clock())))
            self.db.execute('DELETE FROM operations WHERE task_id=?', (task_id,))
            self.db.execute('DELETE FROM task_events WHERE task_id=?', (task_id,))
            self.db.execute('DELETE FROM tasks WHERE task_id=?', (task_id,))
            # Keep cursor monotonic and notify other clients to remove their cached row.
            self.db.execute('INSERT INTO task_events(owner,task_id,body) VALUES(?,?,?)',
                            (row['owner'],task_id,dumps(dict(task_id=task_id,state='DELETED',state_seq=row['state_seq']))))
            # Preserve request fingerprints but discard historical response payloads.
            # Replayed creates/controls must never return a stale task snapshot.
            for cached in self.db.execute('SELECT owner,msg_id,reply FROM requests').fetchall():
                old = json.loads(cached['reply'])
                if old.get('task',{}).get('task_id') == task_id:
                    reply = dict(v=1,type='task.reply',node_id='ugv-service',msg_id=cached['msg_id'],ok=True,
                                 stage='DELETED',deleted=True,task_id=task_id,state_seq=row['state_seq'])
                    self.db.execute('UPDATE requests SET reply=? WHERE owner=? AND msg_id=?',
                                    (dumps(reply),cached['owner'],cached['msg_id']))
        return dict(stage='DELETED',deleted=True,task_id=task_id,state_seq=row['state_seq'])

    def waiting(self):
        with self.lock:
            return [dict(row) for row in self.db.execute("SELECT o.*,t.target,t.boot,t.config,t.state,t.kind,t.execute_before FROM operations o JOIN tasks t USING(task_id) WHERE o.status='waiting' ORDER BY t.priority DESC,t.created,o.rowid")]

    def validate_subject(self, config, kind, owner, targets):
        if kind == 'network_diagnostics' and config['probe_node'] not in targets:
            raise ValueError('probe_node_not_authorized')
        if kind == 'task_monitor':
            watched = self._row(config['watch_task_id'], owner)
            if watched['target'] not in targets:
                raise ValueError('target_not_authorized')
            if watched['kind'] == 'task_monitor':
                raise ValueError('cannot_monitor_monitor')
        if kind == 'anomaly_review':
            event = self.db.execute('SELECT * FROM incidents WHERE event_id=?',(config['event_id'],)).fetchone()
            if event is None or (owner != 'local-console' and event['owner'] != owner):
                raise ValueError('test_event_not_found')
            if event['node_id'] not in targets:
                raise ValueError('event_source_not_authorized')

    def validate_command_size(self, task_id, target, kind, config):
        if kind not in WORKFLOW_KINDS:return
        packet=dict(v=1,type='task.command',target=target,task_id=task_id,msg_id='x'*32,op='start',
                    op_seq=2147483647,revision=2147483647,boot_id='x'*16,deadline_unix=2147483647,kind=kind,config=config)
        if len(dumps(packet).encode())>512:
            raise ValueError('workflow_command_too_large')

    def dispatch(self, operation, boot, concurrent_kinds=()):
        with self.lock, self.db:
            row = self._row(operation['task_id'])
            if row['state'] in TERMINAL:
                return None
            if operation['op'] == 'start' and row['execute_before'] is not None and row['execute_before'] <= self.clock():
                self.db.execute("UPDATE operations SET status='expired' WHERE command_id=?", (operation['command_id'],))
                self._change(row['task_id'], state='EXPIRED', error='start_deadline_missed')
                return None
            if operation['op'] == 'start':
                lane = ' AND kind=?' if row['kind'] in concurrent_kinds else ''
                args = [row['target'], row['task_id']]
                if lane:args.append(row['kind'])
                elif concurrent_kinds:
                    lane = ' AND kind NOT IN (' + ','.join('?' for _ in concurrent_kinds) + ')'
                    args.extend(concurrent_kinds)
                occupied = self.db.execute("SELECT task_id FROM tasks WHERE target=? AND task_id<>? AND state NOT IN ('CREATED','QUEUED','SUCCEEDED','FAILED','CANCELLED','REJECTED','EXPIRED')" + lane, args).fetchone()
                if occupied:
                    return None
            packet = dict(v=1, type='task.command', target=row['target'], task_id=row['task_id'],
                          msg_id=operation['command_id'], op=operation['op'], op_seq=operation['op_seq'], revision=row['revision'],
                          boot_id=boot, deadline_unix=int(self.clock()) + 15)
            if operation['op'] == 'start':
                packet.update(kind=row['kind'], config=json.loads(row['config']))
            if len(dumps(packet).encode()) > 512:
                raise ValueError('node_command_too_large')
            self.db.execute("UPDATE operations SET status='sent',packet=?,sent=? WHERE command_id=? AND status='waiting'",
                            (dumps(packet), self.clock(), operation['command_id']))
            self._change(row['task_id'], boot=boot, node_seq=-1 if operation['op']=='start' else row['node_seq'],
                         state='DISPATCHING' if operation['op']=='start' else row['state'])
            return packet

    def uncertain(self, command_id, reason):
        with self.lock, self.db:
            op = self.db.execute("SELECT * FROM operations WHERE command_id=? AND status='sent'", (command_id,)).fetchone()
            if op:
                self.db.execute("UPDATE operations SET status='uncertain' WHERE command_id=?", (command_id,))
                if self._row(op['task_id'])['state'] not in TERMINAL:
                    self._change(op['task_id'], state='RECONCILING', error=reason)

    def reconcile_rows(self):
        with self.lock:
            return [dict(r) for r in self.db.execute("SELECT * FROM tasks WHERE state NOT IN ('CREATED','QUEUED','SUCCEEDED','FAILED','CANCELLED','REJECTED','EXPIRED')")]

    def receive(self, node, body, query=False):
        allowed_states = {'ACCEPTED','RUNNING','PAUSED','SUCCEEDED','FAILED','CANCELLED','REJECTED','UNKNOWN','NOT_FOUND'}
        if (body.get('v') != 1 or body.get('type') != 'task.event' or body.get('node_id') != node or
            not isinstance(body.get('state'),str) or body['state'] not in allowed_states or type(body.get('seq')) is not int or not 0 <= body['seq'] <= 4294967295 or
            type(body.get('progress')) is not int or not 0 <= body['progress'] <= 100 or
            not isinstance(body.get('boot_id'),str)):
            return False
        if body.get('error') is not None and (not isinstance(body['error'],str) or len(body['error'])>64):
            return False
        with self.lock, self.db:
            try:
                row = self._row(body.get('task_id'))
            except ValueError:
                return False
            if row['target'] != node or row['state'] in TERMINAL or (type(body.get('revision')) is not int or body['revision'] != row['revision']):
                return False
            if not query:
                operation = self.db.execute('SELECT * FROM operations WHERE command_id=? AND task_id=?', (body.get('msg_id'), row['task_id'])).fetchone()
                if not operation or operation['status'] not in ('sent','acked','uncertain') or row['boot'] != body['boot_id']:
                    return False
            if row['boot'] == body['boot_id'] and body['seq'] <= row['node_seq']:
                return False
            state = 'UNKNOWN' if body['state'] == 'NOT_FOUND' else body['state']
            result = body.get('result')
            if result is not None:
                if not isinstance(result, dict) or len(dumps(result).encode()) > (320 if row['kind'] in HOST_KINDS else 240):
                    return False
                if row['kind'] in WORKFLOW_KINDS:
                    if result.get('mode') != MODE:
                        return False
                    config=json.loads(row['config'])
                    if row['kind']=='patrol':
                        done=result.get('done')
                        if type(done) is not int or not 0 <= done <= len(config['point_ids']):return False
                        event_id=result.get('event_id')
                        if event_id is not None:
                            index=config['anomaly_point']
                            if event_id != row['task_id'] or not index or done < index:return False
                            self.db.execute('INSERT OR IGNORE INTO incidents(event_id,owner,source_task_id,node_id,area_id,point_id,created) VALUES(?,?,?,?,?,?,?)',
                                (event_id,row['owner'],row['task_id'],node,config['area_id'],config['point_ids'][index-1],int(self.clock())))
                    else:
                        if result.get('event_id') != config['event_id']:return False
                        if body['state']=='SUCCEEDED' and result.get('verdict') != config['test_verdict']:return False
            pending = self.db.execute("SELECT command_id FROM operations WHERE task_id=? AND status IN ('waiting','sent') ORDER BY rowid DESC LIMIT 1", (row['task_id'],)).fetchone()
            # An older operation's progress must not acknowledge a newer pause/cancel.
            pending_other = pending and pending['command_id'] != body.get('msg_id') and not query
            next_state = row['state'] if pending_other and state not in TERMINAL else state
            self._change(row['task_id'], state=next_state, progress=body['progress'], node_seq=body['seq'],
                         boot=body['boot_id'], feedback_at=self.clock(), error=body.get('error'), result=dumps(result) if result else row['result'])
            if query:
                self.db.execute("UPDATE operations SET status='reconciled' WHERE task_id=? AND status IN ('sent','uncertain')", (row['task_id'],))
            else:
                self.db.execute("UPDATE operations SET status='acked' WHERE command_id=?", (body.get('msg_id'),))
            if state in TERMINAL:
                self.db.execute("UPDATE operations SET status='superseded' WHERE task_id=? AND status IN ('waiting','sent','uncertain')", (row['task_id'],))
            return True

    def expire_waits(self):
        with self.lock, self.db:
            for row in self.db.execute("SELECT task_id FROM tasks WHERE state='QUEUED' AND execute_before<=?",(self.clock(),)).fetchall():
                self.db.execute("UPDATE operations SET status='expired' WHERE task_id=? AND status='waiting'",(row['task_id'],))
                self._change(row['task_id'],state='EXPIRED',error='start_deadline_missed')
            expired = [r[0] for r in self.db.execute("SELECT command_id FROM operations WHERE status='sent' AND sent<?", (self.clock()-20,))]
        for identity in expired:
            self.uncertain(identity, 'execution_ack_timeout')

    def notifications(self, cursor):
        with self.lock:
            return [dict(r) for r in self.db.execute('SELECT * FROM task_events WHERE cursor>? ORDER BY cursor LIMIT 16', (cursor,))]
