"""Isolated actual-Mosquitto integration. Never touches COM ports or the user's Broker."""
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'))
from provision_mqtt import provision
from changan_ugv.agents.ugv import HostDiagnostics
from ugv_service import ServiceController
from node_inventory import load_inventory
from node_identity import enroll
from workflow_reference import WorkflowReference
BROKER=shutil.which('mosquitto') or r'D:\Program Files (x86)\Mosquitto\mosquitto.exe'
CAR=Path(os.environ.get('CHANGAN_CAR_TERMINAL', str(ROOT.parent/'changan-car-terminal')))
if CAR.is_dir():sys.path.insert(0,str(CAR))

class Node:
    """Host test executor; validates actual TLS/ACL/routing, not the C implementation."""
    def __init__(self,root,node,port):
        import paho.mqtt.client as mqtt
        from mqtt_controller import BrokerTLSContext
        import ssl
        self.lock=threading.RLock()
        self.node=node;self.stopped=threading.Event();self.ready=threading.Event();self.seen=[];self.command_packets=[]
        self.agent=WorkflowReference(root/(node+'.json'),node,self.emit,lambda:1)
        role=next(e['role'] for e in load_inventory(root)['nodes'] if e['node_id']==node)
        flow={'uav':'anomaly_review','micro_uav':'patrol'}.get(role)
        self.client=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,client_id=node,clean_session=True)
        context=BrokerTLSContext(ssl.PROTOCOL_TLS_CLIENT)
        context.load_verify_locations(str(root/'secrets/ca.pem'))
        context.load_cert_chain(str(root/'secrets'/node/'client.pem'),str(root/'secrets'/node/'client.key'))
        self.client.tls_set_context(context)
        def connected(client,userdata,flags,reason,properties):
            client.subscribe([(f'mesh/v1/nodes/{node}/task_commands',1),(f'mesh/v1/nodes/{node}/commands',1)])
        def subscribed(*args):
            self.ready.set()
            self.send('presence',dict(type='presence',online=True,boot_id=self.agent.boot),retain=True)
            self.send('capabilities',dict(type='capabilities',operations=['ping','status','echo'],task_types=['diagnostics',*([flow] if flow else [])],
                task_role=role,execution_mode='esp32_test',task_operations=['start','pause','resume','cancel','query'],boot_id=self.agent.boot),retain=True)
            self.telemetry()
        def received(client,userdata,message):
            self.seen.append(message.topic)
            if message.topic==f'mesh/v1/nodes/{node}/commands':
                packet=json.loads(message.payload)
                self.send('acks',dict(type='ack',msg_id=packet['msg_id'],ok=True,payload={}))
            if message.topic==f'mesh/v1/nodes/{node}/task_commands':
                with self.lock:
                    packet=json.loads(message.payload);self.command_packets.append(packet);self.agent.handle(packet)
        self.client.on_connect=connected;self.client.on_subscribe=subscribed;self.client.on_message=received
        self.client.connect('127.0.0.1',port,15);self.client.loop_start()
        if not self.ready.wait(5):raise RuntimeError('Test node not subscribed')
        self.thread=threading.Thread(target=self.loop,daemon=True);self.thread.start()
    def send(self,suffix,body,retain=False):
        packet=dict(v=1,node_id=self.node);packet.update(body)
        self.client.publish(f'mesh/v1/nodes/{self.node}/{suffix}',json.dumps(packet),qos=1,retain=retain)
    def telemetry(self):self.send('telemetry',dict(type='telemetry',boot_id=self.agent.boot,payload={'role':'test_executor'}))
    def emit(self,body):self.send('task_events',body)
    def loop(self):
        next_telemetry=0
        while not self.stopped.wait(.05):
            with self.lock:self.agent.tick(True)
            if time.monotonic()>=next_telemetry:self.telemetry();next_telemetry=time.monotonic()+1
    def close(self):
        self.stopped.set();self.thread.join(2);self.client.disconnect();self.client.loop_stop()

@unittest.skipUnless(Path(BROKER).is_file() and CAR.is_dir(),'Requires local Mosquitto and independent car repo')
class RealBrokerM1(unittest.TestCase):
    def test_tls_car_two_nodes_lifecycle_and_new_topic_acl(self):
        from car_terminal.client import MQTTClient
        from car_terminal.tasks import TaskClient
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with contextlib.redirect_stdout(io.StringIO()):provision(root)
            enroll(root,'micro_uav','micro-002')
            with socket.socket() as listener:listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
            def quote(path):return '"'+path.as_posix()+'"'
            conf=root/'isolated.conf'
            from changan_ugv.deployment import render_broker_config
            with socket.socket() as listener:listener.bind(('127.0.0.1',0));second_port=listener.getsockname()[1]
            config=render_broker_config(ca_file=root/'secrets/ca.pem',server_cert=root/'secrets/ugv-broker.lab/client.pem',
                server_key=root/'secrets/ugv-broker.lab/client.key',acl_file=root/'runtime/acl.conf',
                listeners=[('127.0.0.1',port),('127.0.0.1',second_port)])
            conf.write_text(config+'\nlog_dest stderr\n',encoding='utf-8')
            log=(root/'broker.log').open('w')
            process=subprocess.Popen([BROKER,'-c',str(conf)],stdout=log,stderr=log,
                                     creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            service=None;nodes=[];car=None
            try:
                for _ in range(100):
                    try:
                        with socket.create_connection(('127.0.0.1',port),timeout=.1):break
                    except OSError:
                        if process.poll() is not None:raise RuntimeError('Isolated Broker exited '+str(process.returncode)+': '+(root/'broker.log').read_text(errors='replace'))
                        time.sleep(.05)
                # Both listener blocks must enforce mutual TLS, not just the last.
                import ssl
                for endpoint_port in (port,second_port):
                    missing=ssl.create_default_context(cafile=str(root/'secrets/ca.pem'))
                    missing.maximum_version=ssl.TLSVersion.TLSv1_2
                    with socket.create_connection(('127.0.0.1',endpoint_port),timeout=2) as raw:
                        with self.assertRaises((ssl.SSLError,ConnectionResetError)):missing.wrap_socket(raw,server_hostname='ugv-broker.lab')
                    valid=ssl.create_default_context(cafile=str(root/'secrets/ca.pem'))
                    valid.load_cert_chain(str(root/'secrets/controller-001/client.pem'),str(root/'secrets/controller-001/client.key'))
                    with socket.create_connection(('127.0.0.1',endpoint_port),timeout=2) as raw:
                        with valid.wrap_socket(raw,server_hostname='ugv-broker.lab') as authenticated:
                            self.assertIsNotNone(authenticated.getpeercert())
                service=ServiceController(root/'secrets',port,load_inventory(root),root/'config/nodes.json',root=root)
                nodes=[Node(root,node,port) for node in ['micro-001','micro-002','uav-001']]
                deadline=time.monotonic()+5
                while not all(service.registry.ready(n.node) for n in nodes):
                    if time.monotonic()>deadline:raise AssertionError('Nodes did not become ready')
                    time.sleep(.05)
                car=MQTTClient('127.0.0.1',port,'pc-root-001',root/'secrets/pc-root-001');api=TaskClient(car)
                first=api.create('micro-001',5,200,task_id='first')['task']['task_id']
                second=api.create('micro-002',2,200,task_id='second')['task']['task_id']
                api.control(first,'start');api.control(second,'start')
                def wait_state(task,states):
                    limit=time.monotonic()+8
                    while time.monotonic()<limit:
                        row=api.get(task)['task']
                        if row['state'] in states:return row
                        time.sleep(.05)
                    self.fail('Task state timeout: '+str(row))
                wait_state(first,{'RUNNING'});api.control(first,'pause');wait_state(first,{'PAUSED'})
                services=api.services()
                self.assertEqual({'network_diagnostics','task_monitor','patrol','anomaly_review'},{s['service_type'] for s in services})
                network=api.network('ugv-001','micro-001',2,200)['task']['task_id']
                monitor=api.monitor('ugv-001',first,2,200,10)['task']['task_id']
                api.control(network,'start');api.control(monitor,'start')
                wait_state(network,{'RUNNING'});wait_state(monitor,{'RUNNING'})
                self.assertTrue(all(s['availability']=='busy' for s in api.services() if s['agent_type']=='ugv'))
                network_result=wait_state(network,{'SUCCEEDED'})['result']
                self.assertGreater(network_result['ok'],0)
                self.assertEqual(0,network_result['failed'])
                self.assertGreaterEqual(network_result['avg_ms'],0)
                monitor_result=wait_state(monitor,{'SUCCEEDED'})['result']
                self.assertEqual(first,monitor_result['task_id'])
                self.assertEqual('PAUSED',monitor_result['state'])
                self.assertEqual('reporting',monitor_result['health'])
                # SUBACK alone is not authorization: the forbidden topic must never be delivered.
                nodes[0].client.subscribe('mesh/v1/nodes/micro-002/task_commands',1)
                with service.tasks.store.lock:
                    valid_command=service.tasks.store.db.execute("SELECT command_id FROM operations WHERE task_id='second'").fetchone()[0]
                nodes[0].client.publish('mesh/v1/nodes/micro-002/task_events',json.dumps(dict(v=1,type='task.event',
                    node_id='micro-002',task_id=second,msg_id=valid_command,boot_id=nodes[1].agent.boot,revision=1,seq=999,state='CANCELLED',progress=0)),qos=1)
                done=wait_state(second,{'SUCCEEDED','CANCELLED'})
                self.assertEqual('SUCCEEDED',done['state'])
                self.assertGreater(done['result']['samples'],0)
                third=api.create('micro-002',5,200,task_id='third')['task']['task_id']
                api.control(third,'start');wait_state(third,{'RUNNING'})
                self.assertGreaterEqual(nodes[1].seen.count('mesh/v1/nodes/micro-002/task_commands'),2)
                self.assertNotIn('mesh/v1/nodes/micro-002/task_commands',nodes[0].seen)
                api.control(first,'resume');wait_state(first,{'RUNNING'});api.control(first,'cancel');wait_state(first,{'CANCELLED'})
                history=[];cursor=0
                while True:
                    response=api.events(cursor,first);history+=response['items'];cursor=response['cursor']
                    if not response['more']:break
                states={e['state'] for e in history}
                self.assertTrue({'CREATED','RUNNING','PAUSED','CANCELLED'}<=states)
                deletion=api.delete(first)
                self.assertTrue(deletion['deleted'])
                with self.assertRaisesRegex(ValueError,'task_not_found'):api.get(first)
                self.assertNotEqual(first,api.list()['items'][0]['task_id'])
                service.close();service=None
                # Restart through explicit deployment paths/config, without deriving a repository from secrets.
                from changan_ugv.config import BrokerConfig,BrokerEndpoint,ServicePaths
                from changan_ugv.nodes.controller import BrokerTLSContext
                import ssl
                context=BrokerTLSContext(server_name='wrong-service.invalid')
                context.load_verify_locations(str(root/'secrets/ca.pem'))
                context.load_cert_chain(str(root/'secrets/controller-001/client.pem'),str(root/'secrets/controller-001/client.key'))
                with socket.create_connection(('127.0.0.1',port),timeout=2) as raw:
                    with self.assertRaises(ssl.SSLCertVerificationError):context.wrap_socket(raw,server_hostname='ugv-broker.lab')
                paths=ServicePaths.from_root(root)
                broker=BrokerConfig.from_secrets(root/'secrets',port)
                broker=BrokerConfig(BrokerEndpoint('localhost',port,'ugv-broker.lab'),broker.ca_file,broker.client_cert,broker.client_key)
                service=ServiceController(paths=paths,broker=broker,lock_file=paths.lock_file,
                    inventory=load_inventory(root),inventory_path=paths.inventory_file)

                wait_state(third,{'RUNNING','SUCCEEDED'})
                starts=[p for p in nodes[1].command_packets if p['task_id']==third and p['op']=='start']
                self.assertEqual(1,len(starts),'Restart must reconcile, not replay start')
                announced={s['service_id']:s for s in api.services()}
                for service_id in ('micro-001/patrol','micro-002/patrol','uav-001/anomaly-review'):
                    self.assertTrue(announced[service_id]['announced'])
                    self.assertEqual('esp32_test',announced[service_id]['execution_mode'])
                patrol=api.patrol_test('micro-001','A01',['P01','P02','P03'],1,2)['task']['task_id']
                api.control(patrol,'start');wait_state(patrol,{'RUNNING'})
                api.control(patrol,'pause');wait_state(patrol,{'PAUSED'})
                api.control(patrol,'resume');wait_state(patrol,{'RUNNING'})
                limit=time.monotonic()+6
                while time.monotonic()<limit:
                    incidents=api.incidents()['items']
                    if incidents:break
                    time.sleep(.1)
                self.assertEqual(patrol,incidents[0]['source_task_id'])
                self.assertEqual('P02',incidents[0]['point_id'])
                review=api.review_test('uav-001',incidents[0]['event_id'],'cleared',2)['task']['task_id']
                api.control(review,'start');wait_state(review,{'RUNNING'})
                watched=api.monitor('ugv-001',review,2,200,10)['task']['task_id']
                api.control(watched,'start')
                self.assertEqual('esp32_test',wait_state(patrol,{'SUCCEEDED'})['result']['mode'])
                reviewed=wait_state(review,{'SUCCEEDED'})['result']
                self.assertEqual(('esp32_test','cleared'),(reviewed['mode'],reviewed['verdict']))
                self.assertEqual('esp32_test',wait_state(watched,{'SUCCEEDED'})['result']['mode'])
            finally:
                if car:car.close()
                for node in nodes:node.close()
                if service:service.close()
                process.terminate()
                try:process.wait(5)
                except subprocess.TimeoutExpired:process.kill();process.wait(5)
                log.close()

if __name__=='__main__':unittest.main()
