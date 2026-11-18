"""New HTTP terminal -> root backend -> real isolated mTLS Broker -> UGV executor."""
import contextlib
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
import unittest
from changan_ugv.api.server import LocalAPI
from changan_ugv.deployment import render_broker_config
from changan_ugv.nodes.inventory import load_inventory,write_inventory,write_acl
from changan_ugv.service.server import ServiceController
from provision_mqtt import provision
from test_task_broker import BROKER,CAR,Node


@unittest.skipUnless(Path(BROKER).is_file() and CAR.is_dir(),'Requires isolated Mosquitto and independent car repository')
class RootBroker(unittest.TestCase):
    def test_second_layer_ugv_execution_revoke_and_terminal_disconnect(self):
        from car_terminal.transport.http import HTTPClient
        from car_terminal.tasks import TaskClient
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with contextlib.redirect_stdout(io.StringIO()):provision(root)
            inventory=load_inventory(root)
            write_inventory(root,inventory);write_acl(root,inventory)
            with socket.socket() as listener:
                listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
            config=render_broker_config(ca_file=root/'secrets/ca.pem',
                server_cert=root/'secrets/ugv-broker.lab/client.pem',server_key=root/'secrets/ugv-broker.lab/client.key',
                acl_file=root/'runtime/ugv-root/acl.conf',listeners=[('127.0.0.1',port)])
            conf=root/'isolated.conf';conf.write_text(config,encoding='utf-8')
            log=(root/'broker.log').open('w')
            process=subprocess.Popen([BROKER,'-c',str(conf)],stdout=log,stderr=log,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            service=api=node=terminal=None
            try:
                deadline=time.monotonic()+5
                while True:
                    try:
                        with socket.create_connection(('127.0.0.1',port),timeout=.1):break
                    except OSError:
                        if process.poll() is not None or time.monotonic()>deadline:
                            raise AssertionError('Isolated broker did not start')
                        time.sleep(.05)
                service=ServiceController(root/'secrets',port,inventory,root/'config/nodes.json',root=root,ugv_id='ugv-root')
                node=Node(root,'ugv-001',port)
                deadline=time.monotonic()+5
                while not service.registry.ready('ugv-001'):
                    if time.monotonic()>deadline:self.fail('Second-layer UGV not ready')
                    time.sleep(.05)
                api=LocalAPI(service,0);api.start()
                url=f'http://127.0.0.1:{api.port}'
                terminal=HTTPClient(url);tasks=TaskClient(terminal)
                created=tasks.create('ugv-001',1,200,task_id='root-e2e')
                self.assertEqual('CREATED',created['task']['state'])
                tasks.control('root-e2e','start',1)
                terminal.close();terminal=None
                # UI exit does not close the manager or stop node execution.
                time.sleep(1.5)
                terminal=HTTPClient(url);tasks=TaskClient(terminal)
                deadline=time.monotonic()+8
                while tasks.get('root-e2e')['task']['state']!='SUCCEEDED':
                    if time.monotonic()>deadline:self.fail('UGV diagnostic did not finish')
                    time.sleep(.1)
                from car_terminal.client import request_line
                import urllib.request
                body=dict(msg_id='revoke-http',deadline_unix=int(time.time())+20,
                          trust_status='revoked',expected_revision=0)
                request=urllib.request.Request(url+'/api/v1/nodes/ugv-001/admission',
                    data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
                with urllib.request.urlopen(request,timeout=5) as reply:receipt=json.load(reply)
                self.assertFalse(receipt['broker_acl_applied'])
                self.assertNotIn('ugv-001',service.registry.nodes)
                with self.assertRaisesRegex(ValueError,'target_not_authorized'):
                    tasks.create('ugv-001',1,200,task_id='must-deny')
                with self.assertRaisesRegex(ValueError,'admission_revision_conflict'):
                    request_line(terminal,'node admit ugv-001 0')
                receipt=request_line(terminal,'node admit ugv-001 1')
                self.assertEqual(2,receipt['admission_revision'])
                self.assertIn('ugv-001',service.registry.nodes)
            finally:
                if terminal:terminal.close()
                if api:api.close()
                if node:node.close()
                if service:service.close()
                process.terminate()
                try:process.wait(5)
                except subprocess.TimeoutExpired:process.kill();process.wait(5)
                log.close()
