"""Actual isolated mTLS Broker -> Service -> independent HTTP terminal receipt test.

The publisher is an explicit host protocol substitute, not evidence of C6 radio timing.
"""
import contextlib
import io
import json
import os
from pathlib import Path
import socket
import ssl
import subprocess
import tempfile
import threading
import time
import unittest
import uuid
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from provision_mqtt import provision
from test_task_broker import BROKER,CAR
from changan_ugv.api.server import LocalAPI
from changan_ugv.deployment import render_broker_config
from changan_ugv.nodes.controller import BrokerTLSContext
from changan_ugv.nodes.inventory import load_inventory,write_inventory,write_acl
from changan_ugv.service.server import ServiceController


class Publisher:
    def __init__(self,root,port):
        import paho.mqtt.client as mqtt
        self.node='ugv-001';self.boot=uuid.uuid4().hex[:16];self.seq=0;self.pending={}
        self.client=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,client_id=self.node,clean_session=True)
        context=BrokerTLSContext(ssl.PROTOCOL_TLS_CLIENT)
        context.load_verify_locations(str(root/'secrets/ca.pem'))
        context.load_cert_chain(str(root/'secrets'/self.node/'client.pem'),str(root/'secrets'/self.node/'client.key'))
        self.client.tls_set_context(context)
        self.client.on_connect=lambda client,*args:client.subscribe(f'mesh/v1/nodes/{self.node}/commands',1)
        self.client.on_subscribe=self.subscribed;self.client.on_message=self.receive
        self.client.connect('127.0.0.1',port,15);self.client.loop_start()

    def send(self,topic,body,retain=False):
        self.client.publish(f'mesh/v1/nodes/{self.node}/{topic}',json.dumps(dict(v=1,node_id=self.node,**body)),qos=1,retain=retain)

    def subscribed(self,*args):
        self.send('presence',dict(type='presence',boot_id=self.boot,online=True),True)
        self.send('telemetry',dict(type='telemetry',boot_id=self.boot,payload={}))
        self.announce()

    def announce(self,request=None,*,state='IDLE'):
        self.seq+=1;sent=time.monotonic_ns()//1000;cap_id=f'{self.boot}-{self.seq:08x}'
        self.pending[cap_id]=(self.seq,sent)
        if request:
            body=dict(type='capabilities',boot_id=self.boot,operations=['ping','status','echo'],task_types=['diagnostics'],
                task_role='ugv',task_status='IDLE',cap_measure_v=1,cap_seq=self.seq,cap_id=cap_id,sent_us=sent,
                probe_id=request['probe_id'],batch_id=request['batch_id'])
            self.send('capabilities',body)
        else:
            params=dict(operations=['ping','status','echo'],taskRole='ugv',taskTypes=['diagnostics'],
                taskOperations=['start','pause','resume','cancel','query'],taskStatus=state,
                capMeasureV=1,capSeq=self.seq,capId=cap_id,sentUs=sent)
            if state!='IDLE':
                params['taskId']='mci-diag'
            wire=dict(v=1,service='Mesh_Node',method='Ntf_Capabilities',nodeId=self.node,bootId=self.boot,params=params)
            self.client.publish(f'mesh/v1/nodes/{self.node}/capabilities',json.dumps(wire),qos=1,retain=True)
        return cap_id

    def receive(self,client,userdata,message):
        body=json.loads(message.payload)
        if body['type']=='cap.request':self.announce(body)
        elif body['type']=='cap.receipt' and body['cap_id'] in self.pending:
            seq,sent=self.pending.pop(body['cap_id']);confirmed=time.monotonic_ns()//1000
            self.send('telemetry',dict(type='cap.result',boot_id=self.boot,cap_id=body['cap_id'],cap_seq=seq,
                receipt_token=body['receipt_token'],elapsed_us=confirmed-sent,confirmed_us=confirmed))

    def close(self):self.client.disconnect();self.client.loop_stop()


@unittest.skipUnless(Path(BROKER).is_file() and CAR.is_dir(),'Requires isolated Mosquitto and independent terminal')
class CapabilityBroker(unittest.TestCase):
    def test_actual_mqtt_receipt_http_batch_and_independent_export(self):
        from car_terminal.transport.http import HTTPClient
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with contextlib.redirect_stdout(io.StringIO()):provision(root)
            inventory=load_inventory(root);write_inventory(root,inventory);write_acl(root,inventory)
            with socket.socket() as listener:listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
            config=render_broker_config(ca_file=root/'secrets/ca.pem',server_cert=root/'secrets/ugv-broker.lab/client.pem',
                server_key=root/'secrets/ugv-broker.lab/client.key',acl_file=root/'runtime/ugv-root/acl.conf',listeners=[('127.0.0.1',port)])
            conf=root/'broker.conf';conf.write_text(config,encoding='utf-8')
            service=api=node=terminal=None
            with (root/'broker.log').open('w') as log:
                process=subprocess.Popen([BROKER,'-c',str(conf)],stdout=log,stderr=log,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
                try:
                    deadline=time.monotonic()+5
                    while True:
                        try:
                            with socket.create_connection(('127.0.0.1',port),timeout=.1):break
                        except OSError:
                            if process.poll() is not None or time.monotonic()>deadline:raise AssertionError('Temporary Broker startup failed')
                            time.sleep(.05)
                    service=ServiceController(root/'secrets',port,inventory,root/'config/nodes.json',root=root,ugv_id='ugv-root')
                    node=Publisher(root,port);deadline=time.monotonic()+5
                    while not service.registry.ready('ugv-001'):
                        if time.monotonic()>deadline:self.fail('Publisher did not become ready')
                        time.sleep(.05)
                    self.assertEqual(1024,service.registry.command_limit(node.node))
                    updated=node.announce(state='RUNNING')
                    deadline=time.monotonic()+5
                    with service.condition:
                        while service.registry.nodes[node.node]['capabilities']['task_status']!='RUNNING':
                            if time.monotonic()>deadline:self.fail('MCI state announcement not applied')
                            service.condition.wait(.05)
                        self.assertEqual('mci-diag',service.registry.nodes[node.node]['capabilities']['task_id'])
                    api=LocalAPI(service,0);api.start();terminal=HTTPClient(f'http://127.0.0.1:{api.port}')
                    batch=uuid.uuid4().hex
                    started=terminal.capability_test('start',dict(batch_id=batch,nodes=['ugv-001'],count=2,period_ms=200))
                    self.assertEqual(2,started['summary']['total']);deadline=time.monotonic()+8
                    while True:
                        result=terminal.capability_test('get',dict(batch_id=batch))
                        if result['summary']['complete']:break
                        if time.monotonic()>deadline:self.fail('Receipt batch did not finish')
                        time.sleep(.05)
                    self.assertEqual(2,result['summary']['confirmed'])
                    self.assertTrue(all(r['state'] in ('PASS','UPPER_BOUND_EXCEEDED') for r in result['items']))
                    exported=terminal.capability_test('export',dict(batch_id=batch,format='jsonl'))
                    evidence=[json.loads(line) for line in exported.splitlines()]
                    self.assertEqual(3,len(evidence));self.assertIn('cap_id',evidence[1]['announcement'])
                    self.assertIn('receipt_token',evidence[1]['result'])
                    self.assertEqual(1024,service.registry.command_limit(node.node))
                    with service.tasks.store.lock:
                        saved=service.tasks.store.db.execute(
                            'SELECT raw,elapsed_us FROM cap_announcements WHERE cap_id=?',(updated,)).fetchone()
                    self.assertEqual('RUNNING',json.loads(saved['raw'])['params']['taskStatus'])
                    self.assertIsNotNone(saved['elapsed_us'])
                    before=len(node.pending);terminal.close();terminal=None
                    self.assertEqual(2,service.capability_measurements.get(batch)['summary']['confirmed'])
                finally:
                    if terminal:terminal.close()
                    if api:api.close()
                    if node:node.close()
                    if service:service.close()
                    process.terminate()
                    try:process.wait(5)
                    except subprocess.TimeoutExpired:process.kill();process.wait(5)
