"""Role-based discovery, bounded contracts, incident correlation and persistence."""
import json
from pathlib import Path
import tempfile
import unittest

from changan_ugv.agents.services import HostServices
from changan_ugv.nodes.controller import Registry
from changan_ugv.nodes.inventory import defaults
from changan_ugv.protocol.messages import encode
from changan_ugv.tasks.ports import NodeSnapshot,SendReceipt
from changan_ugv.tasks.runtime import Runtime
from changan_ugv.tasks.workflows import MODE, config_valid
from workflow_reference import WorkflowReference

OPS=('start','pause','resume','cancel','query')


class Channel:
    def __init__(self):self.entries={};self.sent=[]
    def is_connected(self):return True
    def ready_count(self):return len(self.entries)
    def snapshot(self,node):return self.entries.get(node,NodeSnapshot())
    def send(self,node,p):self.sent.append((node,p));return SendReceipt(True)
    def notify(self,owner,p):encode(p);return SendReceipt(True)


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.now=1000.;self.counter=0
        self.inventory=defaults()
        self.inventory['nodes'] += [dict(node_id=node,role=role,root_id='ugv-root',enabled=True)
            for node,role in [('scout-A','uav'),('tiny-A','micro_uav'),('tiny-B','micro_uav')]]
        self.channel=Channel()
        for node,kind in [('scout-A','anomaly_review'),('tiny-A','patrol'),('tiny-B','patrol')]:
            self.channel.entries[node]=NodeSnapshot(True,'boot-'+node,('diagnostics',kind),MODE,OPS)
        self.runtime=Runtime(self.channel,database=self.root/'tasks.db',inventory_loader=lambda:self.inventory,
            executor_factory=lambda emit,snapshot:HostServices(self.root/'agent','ugv-root',emit,snapshot,probe=lambda *a,**k:dict(ok=True),network_snapshot=lambda _:None))
        self.runtime.store.clock=lambda:self.now
        self.addCleanup(self.runtime.close)

    def call(self,message_type,owner='http-local',**fields):
        self.counter+=1
        reply=self.runtime.handle(dict(v=1,type=message_type,msg_id=str(self.counter),**fields),owner)
        encode(reply);return reply

    def patrol(self,task='patrol',target='tiny-A',**extra):
        config=dict(execution_mode=MODE,area_id='A01',point_ids=['P01','P02','P03'],point_duration_s=1,anomaly_point=2)
        config.update(extra)
        return self.call('task.create',task_id=task,target=target,kind='patrol',config=config)

    def start(self,task):
        self.call('task.control',task_id=task,op='start',expected_revision=1);self.runtime.tick()
        return next(p for _,p in reversed(self.channel.sent) if p['task_id']==task and p['op']=='start')

    def event(self,packet,seq=1,state='RUNNING',done=2,**result):
        return dict(v=1,type='task.event',node_id=packet['target'],task_id=packet['task_id'],msg_id=packet['msg_id'],
            boot_id=packet['boot_id'],revision=packet['revision'],seq=seq,state=state,progress=66,
            result=dict(mode=MODE,stage='point_check',done=done,total=3,point='P03',**result))

    def incident(self):
        self.patrol();packet=self.start('patrol')
        self.assertTrue(self.runtime.receive('tiny-A',self.event(packet,event_id='patrol')))
        return packet

    def test_every_registered_role_gets_its_own_service_and_old_firmware_is_unavailable(self):
        rows={r['service_id']:r for r in self.runtime.service_snapshot('http-local')}
        for node in ('tiny-A','tiny-B'):
            self.assertEqual(('available',MODE),(rows[node+'/patrol']['availability'],rows[node+'/patrol']['execution_mode']))
        self.assertEqual('available',rows['scout-A/anomaly-review']['availability'])
        self.channel.entries['tiny-B']=NodeSnapshot(True,'boot-tiny-B',('diagnostics','patrol'),MODE,OPS,'previous-task','UNKNOWN')
        pending=next(r for r in self.runtime.service_snapshot('http-local') if r['service_id']=='tiny-B/patrol')
        self.assertEqual(('busy','UNKNOWN'),(pending['availability'],pending['task_status']))
        self.assertEqual('firmware_required',rows['uav-001/anomaly-review']['reason'])
        self.channel.entries['tiny-A']=NodeSnapshot(False,'boot-tiny-A',('diagnostics','patrol'),MODE,OPS)
        row=next(r for r in self.runtime.service_snapshot('http-local') if r['service_id']=='tiny-A/patrol')
        self.assertEqual(('unavailable','node_not_ready'),(row['availability'],row['reason']))
        self.inventory['nodes']=[e for e in self.inventory['nodes'] if e['node_id']!='tiny-B']
        self.assertNotIn('tiny-B/patrol',{r['service_id'] for r in self.runtime.service_snapshot('http-local')})

    def test_role_and_firmware_gates_and_explicit_test_mode(self):
        with self.assertRaisesRegex(ValueError,'workflow_role_mismatch'):
            self.patrol(target='scout-A')
        with self.assertRaisesRegex(ValueError,'esp32_test_mode_required'):self.patrol(execution_mode='hardware')
        with self.assertRaisesRegex(ValueError,'invalid_patrol_points'):self.patrol(point_ids=['P01','P01'])
        self.patrol('old',target='micro-001')
        self.channel.entries['micro-001']=NodeSnapshot(True,'oldboot',('diagnostics',))
        with self.assertRaisesRegex(ValueError,'node_task_firmware_required'):self.start('old')

    def test_patrol_events_are_authorized_deduplicated_and_review_references_them(self):
        packet=self.incident()
        self.assertTrue(self.runtime.receive('tiny-A',self.event(packet,seq=2,event_id='patrol')))
        incidents=self.call('task.events',scope='incidents',cursor=0)
        self.assertEqual(1,len(incidents['items']))
        event=incidents['items'][0]
        self.assertEqual(('patrol','P02',True),(event['source_task_id'],event['point_id'],event['test']))
        self.assertEqual([],self.call('task.events',scope='incidents',cursor=0,owner='local-console')['items'][1:])
        self.assertFalse(self.runtime.receive('tiny-A',self.event(packet,seq=3,event_id='forged')))
        self.assertEqual([],self.runtime.store.request(dict(type='task.events',msg_id='private',scope='incidents'),'other',self.runtime.targets('http-local'))['items'])
        self.call('task.create',task_id='review',target='scout-A',kind='anomaly_review',
            config=dict(execution_mode=MODE,event_id='patrol',test_verdict='cleared',duration_s=2))
        review=self.start('review')
        reply=dict(v=1,type='task.event',node_id='scout-A',task_id='review',msg_id=review['msg_id'],boot_id=review['boot_id'],revision=1,seq=1,state='SUCCEEDED',progress=100,
            result=dict(mode=MODE,stage='test_done',event_id='patrol',verdict='cleared'))
        self.assertTrue(self.runtime.receive('scout-A',reply))
        self.assertEqual('cleared',self.call('task.get',task_id='review')['task']['result']['verdict'])

    def test_missing_events_wrong_mode_and_deletion_references_are_rejected(self):
        with self.assertRaisesRegex(ValueError,'test_event_not_found'):
            self.call('task.create',task_id='review',target='scout-A',kind='anomaly_review',config=dict(execution_mode=MODE,event_id='missing'))
        packet=self.incident()
        self.assertFalse(self.runtime.receive('tiny-A',dict(self.event(packet,seq=3),result=dict(mode='hardware',done=3))))
        self.call('task.create',task_id='review',target='scout-A',kind='anomaly_review',config=dict(execution_mode=MODE,event_id='patrol'))
        self.assertTrue(self.runtime.receive('tiny-A',self.event(packet,seq=3,state='SUCCEEDED',done=3,event_id='patrol')))
        with self.assertRaisesRegex(ValueError,'task_in_use_by_review'):
            self.call('task.control',task_id='patrol',op='delete',expected_revision=1)
        self.call('task.control',task_id='review',op='cancel',expected_revision=1)
        self.assertTrue(self.call('task.control',task_id='patrol',op='delete',expected_revision=1)['deleted'])
        self.assertEqual(1,len(self.call('task.events',scope='incidents')['items']))

    def test_busy_queue_parallel_nodes_monitor_and_restart_preserve_test_context(self):
        packet=self.incident();self.patrol('second');self.patrol('parallel',target='tiny-B')
        self.start('parallel')
        self.call('task.control',task_id='second',op='start',expected_revision=1);self.runtime.tick()
        self.assertEqual('QUEUED',self.call('task.get',task_id='second')['task']['state'])
        self.assertEqual('point_check',self.runtime.monitor_snapshot('patrol',10)['stage'])
        self.assertEqual(MODE,self.runtime.monitor_snapshot('patrol',10)['mode'])
        self.runtime.close()
        from changan_ugv.tasks.store import Store
        restored=Store(self.root/'tasks.db')
        try:
            self.assertEqual('RECONCILING',restored._row('patrol')['state'])
            self.assertEqual('P02',restored.request(dict(type='task.events',scope='incidents',msg_id='restore'),'http-local',self.runtime.targets('http-local'))['items'][0]['point_id'])
        finally:restored.close()

    def test_long_identifiers_frames_and_config_updates(self):
        self.patrol('t'*32,area_id='A'*12,point_ids=['P'*12,'Q'*12,'R'*12],point_duration_s=60,anomaly_point=3)
        self.call('task.update',task_id='t'*32,expected_revision=1,config=dict(execution_mode=MODE,area_id='B01',point_ids=['P01'],point_duration_s=2,anomaly_point=1))
        self.assertEqual(2,self.call('task.get',task_id='t'*32)['task']['revision'])
        self.patrol('max')
        packet=self.start('max')
        self.assertLessEqual(len(json.dumps(packet,separators=(',',':')).encode()),512)
        self.assertTrue(self.runtime.receive('tiny-A',self.event(packet,event_id='max')))
        row=self.call('task.get',task_id='max')['task']
        self.assertLessEqual(len(encode(dict(v=1,type='task.reply',msg_id='x'*64,ok=True,node_id='ugv-service',task=row))),1032)

    def test_registry_requires_role_and_test_mode_for_new_capabilities(self):
        registry=Registry(nodes=['tiny-A'])
        packet=dict(v=1,type='capabilities',node_id='tiny-A',boot_id='boot',operations=['ping'],
            task_types=['diagnostics','patrol'],task_role='micro_uav',execution_mode=MODE,task_operations=list(OPS))
        self.assertTrue(registry.receive('mesh/v1/nodes/tiny-A/capabilities',packet))
        self.assertFalse(registry.receive('mesh/v1/nodes/tiny-A/capabilities',dict(packet,task_role='uav')))
        self.assertFalse(registry.receive('mesh/v1/nodes/tiny-A/capabilities',dict(packet,execution_mode='hardware')))
        self.assertFalse(registry.receive('mesh/v1/nodes/tiny-A/capabilities',dict(packet,task_status='FLYING')))
        self.assertFalse(registry.receive('mesh/v1/nodes/tiny-A/capabilities',dict(packet,task_operations=[{}])))


if __name__=='__main__':unittest.main()
