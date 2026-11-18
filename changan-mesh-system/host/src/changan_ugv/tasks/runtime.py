"""Bounded asynchronous task dispatch, node reconciliation and UGV-local diagnostics."""
import json
import time
import uuid
from changan_ugv.tasks.store import Store, HOST_KINDS, TERMINAL
from changan_ugv.tasks.ports import NodeChannel, ExecutorFactory
from changan_ugv.tasks.workflows import WORKFLOW_ROLES, WORKFLOW_KINDS, SERVICE_SUFFIX, MODE
from changan_ugv.nodes.inventory import root_of


class Runtime:
    def __init__(self, channel: NodeChannel, *, database, executor_factory: ExecutorFactory, inventory_loader, ugv_id='ugv-root', operators=('http-local',)):
        self.channel, self.ugv_id = channel, ugv_id
        self.inventory_loader = inventory_loader
        self.operators=frozenset(operators)
        self.closed = False
        self.store = Store(database)
        self.queries = {}
        self.query_at = {}
        try:
            self.local = executor_factory(lambda body:self.receive(ugv_id,body), self.ready_count)
            if hasattr(self.local, 'bind_runtime'):
                self.local.bind_runtime(self)
        except BaseException:
            self.store.close()
            raise

    def ready_count(self):
        return self.channel.ready_count()

    def targets(self, owner):
        entries = self.inventory_loader()['nodes']
        enabled = [e for e in entries if e.get('enabled', True) and e.get('trust_status','trusted')=='trusted' and root_of(e)==self.ugv_id]
        if owner != 'local-console' and owner not in self.operators:
            raise ValueError('terminal_not_authorized_for_ugv')
        return {e['node_id'] for e in enabled}

    def handle(self, packet, owner):
        if packet.get('type')=='task.create' and packet.get('kind') in WORKFLOW_KINDS:
            self.validate_workflow_role(packet.get('target'),packet['kind'])
        if packet.get('type') == 'task.create' and packet.get('kind') in HOST_KINDS:
            if packet.get('target') != self.ugv_id:
                raise ValueError('host_service_requires_ugv')
            if packet['kind'] not in getattr(self.local, 'concurrent_kinds', ()):
                raise ValueError('host_service_not_available')
            config = packet.get('config')
            if packet['kind'] == 'network_diagnostics' and isinstance(config, dict) and config.get('probe_node') == self.ugv_id:
                raise ValueError('probe_requires_remote_node')
        if packet.get('type') == 'task.update':
            with self.store.lock:
                task = self.store._row(packet.get('task_id'), owner)
            config = packet.get('config')
            if task['kind'] == 'network_diagnostics' and isinstance(config, dict) and config.get('probe_node') == self.ugv_id:
                raise ValueError('probe_requires_remote_node')
        if packet.get('type')=='task.control' and packet.get('op')=='start':
            with self.store.lock:
                task=self.store._row(packet.get('task_id'),owner)
            if task['kind'] in WORKFLOW_KINDS:self.validate_workflow_role(task['target'],task['kind'])
            if task['target']!=self.ugv_id:
                entry=self.channel.snapshot(task['target'])
                if entry.ready and task['kind'] not in entry.task_types:
                    raise ValueError('node_task_firmware_required')
                if task['kind'] in WORKFLOW_KINDS and entry.ready and entry.execution_mode!=MODE:
                    raise ValueError('esp32_test_firmware_required')
        return self.store.request(packet, owner, self.targets(owner))

    def validate_workflow_role(self,node,kind):
        role=next((e['role'] for e in self.inventory_loader()['nodes'] if e['node_id']==node and e.get('enabled',True)),None)
        if role!=WORKFLOW_ROLES[kind]:raise ValueError('workflow_role_mismatch')

    def service_snapshot(self, owner):
        allowed=self.targets(owner)
        if self.ugv_id not in allowed:
            return []
        with self.store.lock:
            rows = []
            for kind in getattr(self.local, 'concurrent_kinds', ()):
                active = self.store.db.execute("SELECT task_id,state FROM tasks WHERE target=? AND kind=? AND state NOT IN ('CREATED','QUEUED','SUCCEEDED','FAILED','CANCELLED','REJECTED','EXPIRED') LIMIT 1", (self.ugv_id, kind)).fetchone()
                rows.append(dict(service_id=self.ugv_id + '/' + kind, node_id=self.ugv_id,
                                 agent_type='ugv', service_type=kind,
                                 capabilities=['ping','rtt','availability'] if kind == 'network_diagnostics' else ['state','progress','feedback_age'],
                                 operations=['start','pause','resume','cancel','query'],
                                 availability='unavailable' if not self.channel.is_connected() else ('busy' if active else 'available'),
                                 task_status=active['state'] if active else 'IDLE',
                                 task_id=active['task_id'] if active and owner == self.store._row(active['task_id'])['owner'] else None,
                                 boot_id=self.local.boot,execution_mode='host',announced=True,reason=None))
            for entry in self.inventory_loader()['nodes']:
                node=entry['node_id']
                if node not in allowed:continue
                kind=next((k for k,r in WORKFLOW_ROLES.items() if r==entry['role']),None)
                if kind is None:continue
                snapshot=self.channel.snapshot(node)
                announced=kind in snapshot.task_types and snapshot.execution_mode==MODE
                active=self.store.db.execute("SELECT task_id,state,owner FROM tasks WHERE target=? AND state NOT IN ('CREATED','QUEUED','SUCCEEDED','FAILED','CANCELLED','REJECTED','EXPIRED') LIMIT 1",(node,)).fetchone()
                reason='firmware_required' if not announced else ('node_not_ready' if not snapshot.ready else None)
                device_busy=snapshot.task_state not in (None,'IDLE',*TERMINAL)
                rows.append(dict(service_id=node+'/'+SERVICE_SUFFIX[kind],node_id=node,agent_type=entry['role'],
                                 service_type=kind,capabilities=['test_points','test_incident'] if kind=='patrol' else ['test_event_review','test_verdict'],
                                 operations=list(snapshot.task_operations) if announced else [],
                                 execution_mode=MODE if announced else 'not_reported',announced=announced,reason=reason,
                                 availability='unavailable' if reason else ('busy' if active or device_busy else 'available'),
                                 task_status=active['state'] if active else (snapshot.task_state or ('IDLE' if not reason else 'UNKNOWN')),
                                 task_id=active['task_id'] if active and owner in (active['owner'],'local-console') else None,
                                 boot_id=snapshot.boot_id))
            return rows

    def monitor_snapshot(self, task_id, stale_after_s):
        with self.store.lock:
            try:
                row = self.store._row(task_id)
            except ValueError:
                return dict(task_id=task_id, health='not_found')
            # Recheck authorization on every sample, including after inventory changes.
            try:
                allowed = row['target'] in self.targets(row['owner'])
            except ValueError:
                allowed = False
            if not allowed:
                return dict(task_id=task_id, health='not_authorized')
            age = round(max(0, self.store.clock() - row['feedback_at']), 1) if row['feedback_at'] is not None else None
            if row['state'] in TERMINAL:
                health = 'finished'
            elif row['state'] in ('CREATED', 'QUEUED'):
                health = 'waiting'
            elif row['target'] != self.ugv_id and not self.channel.snapshot(row['target']).ready:
                health = 'node_not_ready'
            elif age is None or age > stale_after_s:
                health = 'feedback_stale'
            else:
                health = 'reporting'
            result=json.loads(row['result']) if row['result'] else {}
            sample=dict(task_id=task_id, target=row['target'], state=row['state'], progress=row['progress'],
                        age_s=age, health=health,
                        error=row['error'].encode('utf-8')[:48].decode('utf-8', errors='ignore') if row['error'] else None)
            if row['kind'] in WORKFLOW_KINDS:
                sample.update(mode=MODE,stage=result.get('stage'))
            return sample

    def endpoint(self, node, kind=None):
        if node not in self.targets('local-console'):
            return None
        if node == self.ugv_id:
            return self.local.boot
        if kind in WORKFLOW_KINDS:
            try:self.validate_workflow_role(node,kind)
            except ValueError:return None
        entry = self.channel.snapshot(node)
        if entry.ready and (kind in entry.task_types if kind else bool(entry.task_types)):
            if kind in WORKFLOW_KINDS and entry.execution_mode!=MODE:return None
            return entry.boot_id
        return None

    def publish(self, node, packet):
        if node == self.ugv_id:
            self.local.handle(packet)
            return True
        return self.channel.send(node,packet).queued

    def receive(self, node, body):
        if not isinstance(body.get('msg_id'),str):return False
        if node not in self.targets('local-console'):
            return False
        if node != self.ugv_id:
            if body.get('boot_id') != self.channel.snapshot(node).boot_id:
                return False
        query = self.queries.get(body.get('msg_id'))
        matched = bool(query and query[0]==node and query[1]==body.get('task_id') and query[2]==body.get('boot_id') and query[3]>=time.monotonic())
        accepted = self.store.receive(node,body,query=matched)
        if matched and accepted:
            self.queries.pop(body['msg_id'],None)
        return accepted

    def tick(self):
        connected = self.channel.is_connected()
        self.local.tick(connected)
        self.store.expire_waits()
        if not connected:
            return
        for op in self.store.waiting():
            boot = self.endpoint(op['target'],op['kind'])
            if not boot:
                continue
            kinds = getattr(self.local, 'concurrent_kinds', ()) if op['target'] == self.ugv_id else ()
            packet = self.store.dispatch(op,boot,concurrent_kinds=kinds)
            if packet and not self.publish(op['target'],packet):
                self.store.uncertain(op['command_id'],'publish_failed')
        now = time.monotonic()
        self.queries = {k:v for k,v in self.queries.items() if v[3]>=now}
        for row in self.store.reconcile_rows():
            boot = self.endpoint(row['target'],row['kind'])
            if not boot:
                if row['state'] not in ('RECONCILING','UNKNOWN') and row['error']!='node_offline':
                    with self.store.lock,self.store.db:
                        pending=row['state'] in ('PAUSE_PENDING','RESUME_PENDING','CANCEL_PENDING')
                        self.store._change(row['task_id'],state=row['state'] if pending else 'RECONCILING',error='node_offline')
                continue
            needs = row['state'] in ('RECONCILING','UNKNOWN') or row['error']=='node_offline' or (row['boot'] and row['boot'] != boot)
            if needs and self.query_at.get(row['task_id'],0)<=now:
                identity = uuid.uuid4().hex
                packet = dict(v=1,type='task.command',op='query',target=row['target'],task_id=row['task_id'],
                              msg_id=identity,revision=row['revision'],boot_id=boot,deadline_unix=int(time.time())+15)
                self.queries[identity] = (row['target'],row['task_id'],boot,now+15)
                self.query_at[row['task_id']] = now+5
                self.publish(row['target'],packet)
    def close(self):
        if self.closed:return
        self.closed=True
        try:self.local.close()
        finally:self.store.close()
