"""Generic M1 task API, independent of the firmware repository and application scenarios."""
import json
import shlex
import time
import uuid
from .protocol import MAX_COMMAND
from .transport.base import RequestTransport

HELP = """list | services | ping NODE | status NODE | echo NODE TEXT
 task create NODE [DURATION_S=30] [PERIOD_MS=1000]
 task network UGV NODE [DURATION_S=30] [PERIOD_MS=1000]
 task monitor UGV TASK_ID [DURATION_S=30] [PERIOD_MS=1000] [STALE_AFTER_S=10]
 task patrol-test MICRO AREA P01,P02,P03 [POINT_S=3] [ANOMALY_POINT=0]
 task review-test UAV EVENT_ID [VERDICT=inconclusive] [DURATION_S=5]
 task incidents [CURSOR=0]
 task list [CURSOR=0]
 task get TASK_ID
 task start|pause|resume|cancel TASK_ID [REVISION]
 task delete TASK_ID [REVISION]  (terminal history only)
 task update TASK_ID REVISION DURATION_S PERIOD_MS
 task events [CURSOR=0] [TASK_ID]
 watch [TASK_ID] [CURSOR=0]  (Ctrl+C returns to prompt)
 help | quit"""

class TaskClient:
    def __init__(self, transport: RequestTransport):
        self.transport = transport

    def call(self, message_type, **fields):
        packet = dict(v=1,type=message_type,msg_id=uuid.uuid4().hex,deadline_unix=int(time.time())+20,**fields)
        # Leave room for the gateway's authenticated 32-character node_id.
        if len(json.dumps(dict(packet,node_id='x'*32),ensure_ascii=False,separators=(',',':'),allow_nan=False).encode())>MAX_COMMAND:
            raise ValueError('Task request exceeds the gateway command limit')
        response = self.transport.request(packet)
        if response.get('type')=='error':
            raise ValueError(response.get('error','Task request rejected'))
        if response.get('type')!='task.reply' or not response.get('ok'):
            raise ValueError('Invalid task response')
        return response

    def create(self, node, duration_s=30, period_ms=1000, task_id=None, *, kind='diagnostics', **config):
        return self.create_config(node,kind,dict(duration_s=duration_s,period_ms=period_ms,**config),task_id)

    def create_config(self, node, kind, config, task_id=None):
        task_id = task_id or uuid.uuid4().hex
        try:
            return self.call('task.create',target=node,task_id=task_id,kind=kind,config=config)
        except OSError as exc:
            raise OSError(f'{exc}; query task get {task_id} before submitting again') from exc

    def patrol_test(self, node, area, points, point_duration_s=3, anomaly_point=0, task_id=None):
        return self.create_config(node,'patrol',dict(execution_mode='esp32_test',area_id=area,point_ids=points,
            point_duration_s=point_duration_s,anomaly_point=anomaly_point),task_id)

    def review_test(self, node, event_id, verdict='inconclusive', duration_s=5, task_id=None):
        return self.create_config(node,'anomaly_review',dict(execution_mode='esp32_test',event_id=event_id,
            test_verdict=verdict,duration_s=duration_s),task_id)

    def incidents(self, cursor=0):
        return self.call('task.events',scope='incidents',cursor=cursor)

    def update_config(self, task_id, revision, config):
        return self.call('task.update',task_id=task_id,expected_revision=revision,config=config)

    def network(self, ugv, node, duration_s=30, period_ms=1000):
        return self.create(ugv, duration_s, period_ms, kind='network_diagnostics', probe_node=node)

    def monitor(self, ugv, task_id, duration_s=30, period_ms=1000, stale_after_s=10):
        return self.create(ugv, duration_s, period_ms, kind='task_monitor', watch_task_id=task_id, stale_after_s=stale_after_s)

    def services(self):
        packet=dict(v=1,type='list',scope='services',msg_id=uuid.uuid4().hex,deadline_unix=int(time.time())+20)
        reply=self.transport.request(packet)
        if reply.get('type')=='error':raise ValueError(reply.get('error','Service discovery rejected'))
        if reply.get('type')!='nodes':raise ValueError('Invalid service list')
        if any(not isinstance(row,dict) or 'service_id' not in row for row in reply.get('nodes',[])):
            raise ValueError('Backend does not support service discovery; upgrade the UGV service')
        return reply['nodes']

    def get(self, task_id):
        return self.call('task.get',task_id=task_id)

    def list(self, cursor=0):
        return self.call('task.list',cursor=cursor)

    def control(self, task_id, op, revision=None):
        if revision is None:
            revision=self.get(task_id)['task']['revision']
        return self.call('task.control',task_id=task_id,op=op,expected_revision=revision)

    def delete(self, task_id, revision=None):
        # Use the existing gateway whitelist; no firmware update is required.
        return self.control(task_id, 'delete', revision)

    def update(self, task_id, revision, duration_s, period_ms, **config):
        current=self.get(task_id)['task'].get('config',{})
        return self.call('task.update',task_id=task_id,expected_revision=revision,
                         config=dict(current,duration_s=duration_s,period_ms=period_ms,**config))

    def events(self, cursor=0, task_id=None):
        return self.call('task.events',cursor=cursor,**({'task_id':task_id} if task_id else {}))

    def watch(self, task_id=None, cursor=0):
        while True:
            response=self.events(cursor,task_id)
            for event in response['items']:
                yield event
            cursor=response['cursor']
            if not response['more']:
                time.sleep(1)

def task_line(transport, line):
    words=shlex.split(line)
    if words==['services']:
        return TaskClient(transport).services()
    if words==['help']:
        return HELP
    if len(words)<2 or words[0]!='task':
        raise ValueError('Use help for supported task commands')
    api=TaskClient(transport);op=words[1];args=words[2:]
    if op=='create' and 1<=len(args)<=3:
        return api.create(args[0],int(args[1]) if len(args)>1 else 30,int(args[2]) if len(args)>2 else 1000)
    if op=='network' and 2<=len(args)<=4:
        return api.network(args[0],args[1],int(args[2]) if len(args)>2 else 30,int(args[3]) if len(args)>3 else 1000)
    if op=='monitor' and 2<=len(args)<=5:
        return api.monitor(args[0],args[1],int(args[2]) if len(args)>2 else 30,int(args[3]) if len(args)>3 else 1000,int(args[4]) if len(args)>4 else 10)
    if op=='patrol-test' and 3<=len(args)<=5:
        return api.patrol_test(args[0],args[1],args[2].split(','),int(args[3]) if len(args)>3 else 3,int(args[4]) if len(args)>4 else 0)
    if op=='review-test' and 2<=len(args)<=4:
        return api.review_test(args[0],args[1],args[2] if len(args)>2 else 'inconclusive',int(args[3]) if len(args)>3 else 5)
    if op=='incidents' and len(args)<=1:
        return api.incidents(int(args[0]) if args else 0)
    if op=='get' and len(args)==1:
        return api.get(args[0])
    if op=='list' and len(args)<=1:
        return api.list(int(args[0]) if args else 0)
    if op in ('start','pause','resume','cancel') and 1<=len(args)<=2:
        return api.control(args[0],op,int(args[1]) if len(args)>1 else None)
    if op=='delete' and 1<=len(args)<=2:
        return api.delete(args[0],int(args[1]) if len(args)>1 else None)
    if op=='update' and len(args)==4:
        return api.update(args[0],int(args[1]),int(args[2]),int(args[3]))
    if op=='events' and len(args)<=2:
        return api.events(int(args[0]) if args else 0,args[1] if len(args)>1 else None)
    raise ValueError('Invalid task command; use help')
