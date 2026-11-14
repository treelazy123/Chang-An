"""Bounded asynchronous task dispatch, node reconciliation and UGV-local diagnostics."""
import json
from pathlib import Path
import time
import uuid
from task_store import Store, TERMINAL, dumps
from node_inventory import load_inventory

from task_agents.ugv import HostDiagnostics

class Runtime:
    def __init__(self, controller, root, ugv_id='ugv-001', database=None):
        self.controller, self.root, self.ugv_id = controller, Path(root), ugv_id
        self.store = Store(database or self.root/'host/runtime/tasks.sqlite3')
        self.queries = {}
        self.query_at = {}
        self.notify_cursor = self.store.db.execute('SELECT COALESCE(MAX(cursor),0) FROM task_events').fetchone()[0]
        try:
            self.local = HostDiagnostics(self.root/'host/runtime/ugv-task-agent.json', ugv_id,
                                         lambda body:self.receive(ugv_id,body), self.ready_count)
        except BaseException:
            self.store.close()
            raise

    def ready_count(self):
        with self.controller.condition:
            return sum(self.controller.registry.ready(n) for n in self.controller.registry.nodes)

    def targets(self, owner):
        entries = load_inventory(self.root)['nodes']
        enabled = [e for e in entries if e.get('enabled', True) and e.get('ugv_id','ugv-001')==self.ugv_id]
        if owner != 'local-console' and not any(e['node_id']==owner and e['role']=='pc_root' for e in enabled):
            raise ValueError('terminal_not_authorized_for_ugv')
        return {e['node_id'] for e in enabled}

    def handle(self, packet, owner):
        if packet.get('type')=='task.control' and packet.get('op')=='start':
            with self.store.lock:
                task=self.store._row(packet.get('task_id'),owner)
            if task['target']!=self.ugv_id:
                with self.controller.condition:
                    entry=self.controller.registry.nodes.get(task['target'],{})
                    if self.controller.registry.ready(task['target']) and 'diagnostics' not in entry.get('capabilities',{}).get('task_types',[]):
                        raise ValueError('node_task_firmware_required')
        return self.store.request(packet, owner, self.targets(owner))

    def endpoint(self, node):
        if node not in self.targets('local-console'):
            return None
        if node == self.ugv_id:
            return self.local.boot
        with self.controller.condition:
            registry = self.controller.registry
            entry = registry.nodes.get(node,{})
            cap = entry.get('capabilities',{})
            if registry.ready(node) and 'diagnostics' in cap.get('task_types',[]):
                return entry['presence']['boot_id']
        return None

    def publish(self, node, packet):
        if node == self.ugv_id:
            self.local.handle(packet)
            return True
        return self.controller.client.publish(f'mesh/v1/nodes/{node}/task_commands', dumps(packet), qos=1, retain=False).rc == 0

    def receive(self, node, body):
        if not isinstance(body.get('msg_id'),str):return False
        if node not in self.targets('local-console'):
            return False
        if node != self.ugv_id:
            with self.controller.condition:
                entry = self.controller.registry.nodes.get(node,{})
                if body.get('boot_id') != entry.get('presence',{}).get('boot_id'):
                    return False
        query = self.queries.get(body.get('msg_id'))
        matched = bool(query and query[0]==node and query[1]==body.get('task_id') and query[2]==body.get('boot_id') and query[3]>=time.monotonic())
        accepted = self.store.receive(node,body,query=matched)
        if matched and accepted:
            self.queries.pop(body['msg_id'],None)
        return accepted

    def tick(self):
        connected = self.controller.connected.is_set()
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
            self.controller.client.publish(f"mesh/v1/terminals/{row['owner']}/events",dumps(body),qos=1,retain=False)

    def close(self):
        self.store.close()
