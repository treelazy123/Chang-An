"""Durable M1 lifecycle and fault tests, without firmware builds or devices."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from task_store import Store
from task_runtime import Runtime
from changan_ugv.agents.ugv import HostDiagnostics
from changan_ugv.transport.node_channel import MQTTNodeChannel
from changan_ugv.nodes.controller import Registry
from node_inventory import defaults, write_inventory, write_acl, load_inventory
from changan_ugv.service.requests import Requests
from changan_ugv.protocol.messages import encode

class TaskLifecycle(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'tasks.db';self.now=1000;self.index=0
        self.store=Store(self.path,clock=lambda:self.now);self.addCleanup(lambda:self.store.close())
        self.owner='http-local';self.targets={'micro-001','micro-002'}
    def request(self,message_type,**fields):
        self.index+=1
        return dict(v=1,type=message_type,node_id=self.owner,msg_id=str(self.index),deadline_unix=self.now+20,**fields)
    def call(self,message_type,**fields):
        return self.store.request(self.request(message_type,**fields),self.owner,self.targets)
    def create(self,task='first',target='micro-001',**kwargs):
        return self.call('task.create',task_id=task,target=target,kind='diagnostics',config=dict(duration_s=10,period_ms=1000),**kwargs)
    def get(self,task='first'):
        return self.call('task.get',task_id=task)['task']
    def control(self,op,task='first',revision=1):
        return self.call('task.control',task_id=task,op=op,expected_revision=revision)
    def start(self,task='first',target='micro-001'):
        self.create(task,target);self.control('start',task)
        operation=next(op for op in self.store.waiting() if op['task_id']==task)
        return self.store.dispatch(operation,'boot-a')
    def event(self,packet,state,seq=1,**extra):
        return dict(v=1,type='task.event',node_id=packet['target'],msg_id=packet['msg_id'],
                    task_id=packet['task_id'],revision=packet['revision'],boot_id=packet['boot_id'],
                    state=state,seq=seq,progress=0,**extra)

    def test_durable_create_and_idempotency_are_one_transaction(self):
        p=self.request('task.create',task_id='first',target='micro-001',kind='diagnostics')
        a=self.store.request(p,self.owner,self.targets)
        self.assertEqual(a,self.store.request(p,self.owner,self.targets))
        with self.assertRaisesRegex(ValueError,'msg_id_conflict'):
            self.store.request(dict(p,target='micro-002'),self.owner,self.targets)
        self.store.close();self.store=Store(self.path,clock=lambda:self.now)
        self.assertEqual(a,self.store.request(p,self.owner,self.targets));self.assertEqual('CREATED',self.get()['state'])
        self.assertEqual(1,len(self.call('task.list')['items']))

    def test_parallel_duplicate_creates_do_not_duplicate_tasks(self):
        p=self.request('task.create',task_id='first',target='micro-001',kind='diagnostics')
        with ThreadPoolExecutor(max_workers=8) as pool:
            replies=list(pool.map(lambda _:self.store.request(p,self.owner,self.targets),range(20)))
        self.assertTrue(all(x==replies[0] for x in replies))
        self.assertEqual(1,self.store.db.execute('SELECT count(*) FROM tasks').fetchone()[0])

    def test_acceptance_progress_and_result_are_not_submission_ack(self):
        p=self.start();self.assertEqual('DISPATCHING',self.get()['state'])
        self.assertTrue(self.store.receive('micro-001',self.event(p,'ACCEPTED')))
        e=self.event(p,'RUNNING',2);e['progress']=40;self.store.receive('micro-001',e)
        self.assertEqual(40,self.get()['progress'])
        e=self.event(p,'SUCCEEDED',3,result={'source':'c6','samples':10});e['progress']=100
        self.assertTrue(self.store.receive('micro-001',e));self.assertEqual('SUCCEEDED',self.get()['state'])
        self.assertFalse(self.store.receive('micro-001',self.event(p,'RUNNING',4)))

    def test_old_progress_does_not_ack_a_new_pause_or_cancel(self):
        p=self.start();self.store.receive('micro-001',self.event(p,'RUNNING'))
        pause=self.control('pause')['command_id'];self.store.dispatch(self.store.waiting()[0],'boot-a')
        self.store.receive('micro-001',self.event(p,'RUNNING',2))
        self.assertEqual('PAUSE_PENDING',self.get()['state'])
        self.assertEqual('sent',self.store.db.execute('SELECT status FROM operations WHERE command_id=?',(pause,)).fetchone()[0])
        pause_packet=dict(p,msg_id=pause)
        self.store.receive('micro-001',self.event(pause_packet,'PAUSED',3))
        self.assertEqual('PAUSED',self.get()['state'])
        self.control('resume');resume=self.store.dispatch(self.store.waiting()[0],'boot-a')
        self.store.receive('micro-001',self.event(resume,'RUNNING',4))
        self.control('cancel');cancel=self.store.dispatch(self.store.waiting()[0],'boot-a')
        self.store.receive('micro-001',self.event(resume,'RUNNING',5))
        self.assertEqual('CANCEL_PENDING',self.get()['state'])
        self.store.receive('micro-001',self.event(cancel,'CANCELLED',6))
        self.assertEqual('CANCELLED',self.get()['state'])

    def test_node_independence_and_one_active_task_per_node(self):
        p=self.start();self.start('second','micro-002')
        self.assertEqual('DISPATCHING',self.get('second')['state'])
        self.create('third');self.control('start','third')
        self.assertIsNone(self.store.dispatch(self.store.waiting()[0],'boot-a'))
        self.store.receive('micro-001',self.event(p,'SUCCEEDED'))
        self.assertIsNotNone(self.store.dispatch(self.store.waiting()[0],'boot-a'))

    def test_manager_restart_reconciles_instead_of_replaying_start(self):
        p=self.start();self.store.close();self.store=Store(self.path,clock=lambda:self.now)
        self.assertEqual('RECONCILING',self.get()['state']);self.assertEqual([],self.store.waiting())
        e=self.event(p,'UNKNOWN',1);e['boot_id']='new-boot';e['msg_id']='query-id'
        self.assertFalse(self.store.receive('micro-001',e))
        self.assertTrue(self.store.receive('micro-001',e,query=True))
        self.assertEqual('UNKNOWN',self.get()['state'])
        self.assertEqual([],self.store.waiting())

    def test_timeout_and_missing_task_do_not_create_a_success_or_replay(self):
        p=self.start();self.now+=21;self.store.expire_waits()
        self.assertEqual('RECONCILING',self.get()['state']);self.assertEqual([],self.store.waiting())
        self.store.receive('micro-001',self.event(p,'NOT_FOUND'),query=True)
        self.assertEqual('UNKNOWN',self.get()['state'])

    def test_sequence_boot_identity_and_revision_checks(self):
        p=self.start();e=self.event(p,'RUNNING',4)
        self.assertFalse(self.store.receive('micro-002',e))
        self.assertFalse(self.store.receive('micro-001',dict(e,boot_id='old')))
        self.assertFalse(self.store.receive('micro-001',dict(e,revision=2)))
        self.assertFalse(self.store.receive('micro-001',dict(e,revision=True)))
        self.assertTrue(self.store.receive('micro-001',e))
        self.assertFalse(self.store.receive('micro-001',self.event(p,'ACCEPTED',3)))

    def test_config_revision_and_unsupported_scenarios(self):
        self.create()
        with self.assertRaisesRegex(ValueError,'revision_conflict'):
            self.call('task.update',task_id='first',expected_revision=2,config={})
        self.call('task.update',task_id='first',expected_revision=1,config={'duration_s':20})
        self.assertEqual(2,self.get()['revision']);self.assertEqual(20,self.get()['config']['duration_s'])
        self.control('start',revision=2)
        with self.assertRaisesRegex(ValueError,'update_requires_created'):
            self.call('task.update',task_id='first',expected_revision=2,config={})
        for kind in ['survey','flight','verify']:
            with self.assertRaisesRegex(ValueError,'unsupported_task_kind'):
                self.call('task.create',task_id=kind,target='micro-001',kind=kind)

    def test_permissions_and_invalid_configuration(self):
        self.create()
        p=self.request('task.get',task_id='first')
        with self.assertRaisesRegex(ValueError,'task_not_found'):
            self.store.request(p,'another-car',self.targets)
        with self.assertRaisesRegex(ValueError,'target_not_authorized'):
            self.call('task.create',task_id='unknown',target='unknown',kind='diagnostics')
        for config in [{'duration_s':True},{'period_ms':0},{'waypoints':[]},[]]:
            with self.assertRaisesRegex(ValueError,'invalid_config'):
                self.call('task.create',task_id='bad',target='micro-001',kind='diagnostics',config=config)
        with self.assertRaisesRegex(ValueError,'unknown_task_fields'):
            self.call('task.create',task_id='bad',target='micro-001',kind='diagnostics',event_id='e')

    def test_offline_queue_deadline_and_cancellation(self):
        self.create(execute_before=1002);self.control('start');self.now=1003;self.store.expire_waits()
        self.assertEqual('EXPIRED',self.get()['state']);self.assertEqual([],self.store.waiting())
        self.create('second');self.control('cancel','second');self.assertEqual('CANCELLED',self.get('second')['state'])

    def test_cursor_queries_and_maximum_id_frames_fit_c6(self):
        for i in range(3):self.create('t'+str(i),'micro-001')
        page=self.call('task.list');self.assertEqual(1,len(page['items']));self.assertTrue(page['more'])
        seen=[];cursor=0
        while True:
            page=self.call('task.events',cursor=cursor)
            seen.extend(page['items']);cursor=page['cursor'];encode(page)
            if not page['more']:break
        self.assertEqual(3,len(seen))
        self.assertEqual([],self.call('task.events',cursor=cursor)['items'])
        self.targets.add('n'*32)
        created=self.create('t'*32,'n'*32)
        self.assertLessEqual(len(encode(created)),1032)

class LocalAgent(unittest.TestCase):
    def test_real_sampler_pause_cancel_and_restart_journal(self):
        with tempfile.TemporaryDirectory() as directory:
            now=[0];events=[];path=Path(directory)/'agent.json'
            agent=HostDiagnostics(path,'ugv-test',events.append,lambda:3,lambda:now[0])
            command=dict(op='start',op_seq=1,msg_id='a',task_id='task',revision=1,config=dict(duration_s=3,period_ms=200))
            agent.handle(command);self.assertEqual(['ACCEPTED','RUNNING'],[e['state'] for e in events])
            now[0]=1;agent.tick(True);self.assertEqual(1,events[-1]['result']['samples'])
            self.assertEqual('ugv_host',events[-1]['result']['source'])
            now[0]=2;agent.tick(False);self.assertEqual('PAUSED',agent.row['state'])
            recovered=HostDiagnostics(path,'ugv-test',events.append,lambda:3,lambda:now[0])
            self.assertEqual('UNKNOWN',recovered.row['state'])
            recovered.handle(dict(command,op='cancel',op_seq=2,msg_id='b'));self.assertEqual('CANCELLED',recovered.row['state'])

    def test_sampler_duplicate_start_does_not_reset_progress(self):
        with tempfile.TemporaryDirectory() as directory:
            now=[0];events=[]
            agent=HostDiagnostics(Path(directory)/'agent.json','ugv',events.append,lambda:1,lambda:now[0])
            p=dict(op='start',op_seq=1,msg_id='a',task_id='task',revision=1,config=dict(duration_s=3,period_ms=200))
            agent.handle(p);now[0]=1;agent.tick(True);elapsed=agent.row['elapsed']
            agent.handle(p);self.assertEqual(elapsed,agent.row['elapsed'])
            now[0]=4;agent.tick(True);self.assertEqual('SUCCEEDED',agent.row['state'])

    def test_missing_task_cancel_tombstone_blocks_late_start(self):
        with tempfile.TemporaryDirectory() as directory:
            events=[];agent=HostDiagnostics(Path(directory)/'agent.json','ugv',events.append,lambda:1)
            p=dict(op='cancel',op_seq=2,msg_id='cancel',task_id='missing',revision=1)
            agent.handle(p);self.assertEqual('CANCELLED',agent.row['state'])
            agent.handle(dict(p,op='start',op_seq=1,msg_id='old-start',config=dict(duration_s=1,period_ms=1000)))
            self.assertEqual('CANCELLED',agent.row['state']);self.assertEqual(0,agent.row['samples'])

    def test_old_pause_cannot_pause_a_resumed_task_again(self):
        with tempfile.TemporaryDirectory() as directory:
            agent=HostDiagnostics(Path(directory)/'agent.json','ugv',lambda e:None,lambda:1)
            start=dict(op='start',op_seq=1,msg_id='start',task_id='task',revision=1,config=dict(duration_s=30,period_ms=1000))
            agent.handle(start)
            pause=dict(start,op='pause',op_seq=2,msg_id='pause');agent.handle(pause)
            self.assertEqual('PAUSED',agent.row['state'])
            agent.handle(dict(start,op='resume',op_seq=3,msg_id='resume'));self.assertEqual('RUNNING',agent.row['state'])
            agent.handle(pause);self.assertEqual('RUNNING',agent.row['state'])

class TaskIntegration(unittest.TestCase):
    def test_http_router_scope_and_malformed_type(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);write_inventory(root,defaults())
            connected=threading.Event();connected.set()
            c=SimpleNamespace(connected=connected,condition=threading.Condition(),registry=Registry(nodes=['micro-001']))
            c.client=SimpleNamespace(publish=lambda *args,**kwargs:SimpleNamespace(rc=0))
            runtime=Runtime(MQTTNodeChannel(c),database=root/'runtime/ugv-root/tasks.sqlite3',
                            executor_factory=lambda emit,snapshot:HostDiagnostics(root/'runtime/ugv-root/agent.json','ugv-root',emit,snapshot),
                            inventory_loader=lambda:load_inventory(root));c.tasks=runtime
            try:
                api=Requests(c,root,clock=lambda:1000)
                base=dict(v=1,type='task.create',node_id='http-local',msg_id='create',deadline_unix=1020,
                          task_id='task',target='micro-001',kind='diagnostics')
                self.assertEqual('task.reply',api.handle(base,local=True)[0]['type'])
                self.assertEqual('http_transport_required',api.handle(base,local=False)[0]['error'])
                self.assertEqual('invalid_request',api.handle(dict(base,type={}),local=True)[0]['error'])
                inv=defaults();inv['nodes'][-1]['enabled']=False;write_inventory(root,inv)
                self.assertIn('authorized',api.handle(dict(base,msg_id='new'),local=True)[0]['error'])
            finally:runtime.close()

    def test_new_topic_permissions_are_per_node_and_car(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);write_acl(root,defaults());text=(root/'runtime/ugv-root/acl.conf').read_text()
            micro=text.split('user micro-001\n')[1].split('\n\n')[0]
            self.assertIn('read mesh/v1/nodes/micro-001/task_commands',micro)
            self.assertIn('write mesh/v1/nodes/micro-001/task_events',micro)
            self.assertNotIn('nodes/+',micro);self.assertNotIn('terminals/',micro)
            self.assertNotIn('terminals/',text)
            self.assertNotIn('user ugv-root\n',text)

if __name__=='__main__':unittest.main()
