"""Deployment and task boundary behavior, without hardware access."""
from pathlib import Path
import tempfile
import time
import unittest
from changan_ugv.config import BrokerEndpoint,ServiceConfig
from changan_ugv.deployment import render_broker_config
from changan_ugv.nodes.inventory import defaults,load_inventory
from changan_ugv.tasks.ports import NodeSnapshot,SendReceipt
from changan_ugv.tasks.runtime import Runtime

class Configuration(unittest.TestCase):
    def test_file_relative_paths_do_not_depend_on_repository_layout(self):
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder);file=folder/'service.toml'
            file.write_text('[broker]\nhost="192.0.2.10"\nport=9443\nserver_name="ugv-broker.lab"\nca_file="pki/ca.pem"\nclient_cert="pki/controller.pem"\nclient_key="pki/controller.key"\n[paths]\ninventory_file="admin/nodes.json"\ntask_database="data/tasks.db"\nagent_journal="data/agent.json"\nlock_file="state/controller.lock"\n[service]\nugv_id="ugv-001"\nrpc_port=18787\n',encoding='utf-8')
            cfg=ServiceConfig.from_file(file)
            self.assertEqual(folder/'pki/ca.pem',cfg.broker.ca_file)
            self.assertEqual(folder/'data/tasks.db',cfg.paths.task_database)
            self.assertEqual(folder/'admin/nodes.json',cfg.paths.inventory_file)
            self.assertEqual('192.0.2.10',cfg.broker.endpoint.host)
            self.assertEqual(18787,cfg.rpc_port)
            with self.assertRaises(FileNotFoundError):load_inventory(path=cfg.paths.inventory_file)
    def test_invalid_endpoint_fails_before_network_access(self):
        for kwargs in ({'port':0},{'port':True},{'port':65536},{'host':'a\nb'},{'server_name':''}):
            with self.assertRaises(ValueError):BrokerEndpoint(**kwargs)
    def test_listener_render_is_separate_from_client_connection(self):
        values=dict(ca_file='ca.pem',server_cert='server.pem',server_key='server.key',acl_file='acl.conf')
        text=render_broker_config(**values,listeners=[('127.0.0.1',8883),('192.0.2.10',8883)])
        self.assertIn('listener 8883 192.0.2.10',text)
        self.assertIn('require_certificate true',text)
        self.assertIn('tls_version tlsv1.2',text)
        self.assertEqual('127.0.0.1',BrokerEndpoint().host)
        with self.assertRaises(ValueError):render_broker_config(**values,listeners=[('127.0.0.1\nallow_anonymous true',8883)])

class MemoryChannel:
    def __init__(self):
        self.online=True;self.queued=True;self.sent=[];self.events=[]
        self.node=NodeSnapshot(True,'remote-boot',('diagnostics',))
    def is_connected(self):return self.online
    def snapshot(self,node_id):return self.node
    def ready_count(self):return 7
    def send(self,node_id,packet):self.sent.append((node_id,packet));return SendReceipt(self.queued)
    def notify(self,node_id,packet):self.events.append((node_id,packet));return SendReceipt(True)

class Executor:
    boot='local-boot'
    def __init__(self,emit,snapshot):self.emit=emit;self.snapshot=snapshot;self.handled=[];self.ticks=[];self.closed=False
    def handle(self,packet):self.handled.append(packet)
    def tick(self,connected):self.ticks.append(connected)
    def close(self):self.closed=True

class TaskPorts(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.channel=MemoryChannel();self.executors=[];self.sequence=0
        def factory(emit,snapshot):
            executor=Executor(emit,snapshot);self.executors.append(executor);return executor
        self.runtime=Runtime(self.channel,database=Path(self.temp.name)/'state/tasks.db',executor_factory=factory,inventory_loader=defaults)
        self.addCleanup(self.runtime.close)
    def request(self,type,**fields):
        self.sequence+=1
        return self.runtime.handle(dict(v=1,type=type,msg_id=str(self.sequence),deadline_unix=int(time.time())+20,**fields),'pc-root-001')
    def start(self,target='micro-001'):
        self.request('task.create',task_id='test-task',target=target,kind='diagnostics')
        self.request('task.control',task_id='test-task',op='start',expected_revision=1)
        self.runtime.tick()
    def row(self):return self.request('task.get',task_id='test-task')['task']
    def test_queued_send_is_not_execution_ack_and_boot_is_checked(self):
        self.start();self.assertEqual('DISPATCHING',self.row()['state'])
        packet=self.channel.sent[-1][1]
        event=dict(v=1,type='task.event',node_id='micro-001',msg_id=packet['msg_id'],task_id='test-task',revision=1,seq=1,state='RUNNING',progress=10,boot_id='wrong')
        self.assertFalse(self.runtime.receive('micro-001',event))
        self.assertTrue(self.runtime.receive('micro-001',dict(event,boot_id='remote-boot')))
        self.assertEqual('RUNNING',self.row()['state'])
    def test_failed_send_preserves_uncertainty(self):
        self.channel.queued=False;self.start()
        self.assertEqual('RECONCILING',self.row()['state'])
        self.assertEqual('publish_failed',self.row()['error'])
    def test_local_executor_is_injected_and_receives_transport_state(self):
        self.start('ugv-001')
        self.assertEqual('start',self.executors[0].handled[0]['op'])
        self.assertEqual(7,self.executors[0].snapshot())
        self.channel.online=False;self.runtime.tick()
        self.assertEqual(False,self.executors[0].ticks[-1])
        self.assertEqual('DISPATCHING',self.row()['state'])
    def test_executor_closed_on_shutdown(self):
        self.runtime.close();self.assertTrue(self.executors[0].closed)
if __name__=='__main__':unittest.main()
