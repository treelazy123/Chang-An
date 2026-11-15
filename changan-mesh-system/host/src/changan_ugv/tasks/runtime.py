"""Bounded asynchronous task dispatch, node reconciliation and UGV-local diagnostics."""
import json
import time
import uuid
from changan_ugv.tasks.store import Store
from changan_ugv.tasks.ports import NodeChannel, ExecutorFactory


class Runtime:
    def __init__(self, channel: NodeChannel, *, database, executor_factory: ExecutorFactory, inventory_loader, ugv_id='ugv-001'):
        self.channel, self.ugv_id = channel, ugv_id
        self.inventory_loader = inventory_loader
        self.closed = False
        self.store = Store(database)
        self.queries = {}
        self.query_at = {}
        self.notify_cursor = self.store.db.execute('SELECT COALESCE(MAX(cursor),0) FROM task_events').fetchone()[0]
        try:
            self.local = executor_factory(lambda body:self.receive(ugv_id,body), self.ready_count)
        except BaseException:
            self.store.close()
            raise

    def ready_count(self):
        return self.channel.ready_count()

    def targets(self, owner):
        entries = self.inventory_loader()['nodes']
        enabled = [e for e in entries if e.get('enabled', True) and e.get('ugv_id','ugv-001')==self.ugv_id]
        if owner != 'local-console' and not any(e['node_id']==owner and e['role']=='pc_root' for e in enabled):
            raise ValueError('terminal_not_authorized_for_ugv')
        return {e['node_id'] for e in enabled}

    def handle(self, packet, owner):
        if packet.get('type')=='task.control' and packet.get('op')=='start':
            with self.store.lock:
                task=self.store._row(packet.get('task_id'),owner)
            if task['target']!=self.ugv_id:
                entry=self.channel.snapshot(task['target'])
                if entry.ready and 'diagnostics' not in entry.task_types:
                    raise ValueError('node_task_firmware_required')
        return self.store.request(packet, owner, self.targets(owner))

    def endpoint(self, node):
        if node not in self.targets('local-console'):
            return None
        if node == self.ugv_id:
            return self.local.boot
        entry = self.channel.snapshot(node)
        if entry.ready and 'diagnostics' in entry.task_types:
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
            boot = self.endpoint(op['target'])
            if not boot:
                continue
            packet = self.store.dispatch(op,boot)
            if packet and not self.publish(op['target'],packet):
                self.store.uncertain(op['command_id'],'publish_failed')
        now = time.monotonic()
        self.queries = {k:v for k,v in self.queries.items() if v[3]>=now}
        for row in self.store.reconcile_rows():
            boot = self.endpoint(row['target'])
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
        # Live notifications are best effort; durable cursor queries are authoritative.
        for row in self.store.notifications(self.notify_cursor):
            self.notify_cursor = row['cursor']
            if row['owner'] == 'local-console':
                continue
            try:
                self.targets(row['owner'])
            except ValueError:
                continue
            body = dict(v=1,type='task.event',node_id='ugv-service',cursor=row['cursor'],**json.loads(row['body']))
            self.channel.notify(row['owner'],body)

    def close(self):
        if self.closed:return
        self.closed=True
        try:self.local.close()
        finally:self.store.close()
