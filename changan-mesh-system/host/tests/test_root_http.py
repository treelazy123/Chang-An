"""New root topology and actual loopback HTTP/WS, with no production endpoints."""
import asyncio
import contextlib
import hashlib
import io
import json
from pathlib import Path
import queue
import tempfile
import threading
import time
import unittest
import uuid
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from types import SimpleNamespace
from aiohttp import ClientSession,WSMsgType
from aiohttp.test_utils import TestClient,TestServer
from changan_ugv.nodes.catalog import NodeCatalog
from changan_ugv.api.server import application
from changan_ugv.agents.ugv import HostDiagnostics
from changan_ugv.nodes.inventory import defaults,validate,clients,write_acl
from changan_ugv.service.requests import Requests
from changan_ugv.service.server import ServiceController
from changan_ugv.tasks.runtime import Runtime
from changan_ugv.tasks.ports import NodeSnapshot,SendReceipt


def packet(message_type='list',**fields):
    return dict(v=1,type=message_type,msg_id=uuid.uuid4().hex,deadline_unix=int(time.time())+30,**fields)


class Channel:
    def __init__(self):self.sent=[];self.online=True
    def is_connected(self):return self.online
    def ready_count(self):return 1
    def snapshot(self,node):return NodeSnapshot(True,'radio-boot',('diagnostics',))
    def send(self,node,body):self.sent.append((node,body));return SendReceipt(True)
    def notify(self,owner,body):raise AssertionError('HTTP events must not be published as MQTT terminal events')


class Harness:
    request_loop=ServiceController.request_loop
    submit_local=ServiceController.submit_local
    def __init__(self,folder,inventory=None):
        self.inventory=inventory or defaults()
        self.stopped=threading.Event();self.connected=threading.Event();self.connected.set()
        self.inbox=queue.Queue(16);self.task_inbox=queue.Queue(16)
        self.channel=Channel()
        self.registry=SimpleNamespace(snapshot=lambda:[dict(node_id='ugv-001',ready=True,operations=['ping'])])
        self.condition=threading.Condition()
        self.tasks=Runtime(self.channel,database=folder/'tasks.db',inventory_loader=lambda:self.inventory,
            executor_factory=lambda emit,snapshot:HostDiagnostics(folder/'agent.json','ugv-root',emit,snapshot),
            ugv_id='ugv-root',operators=('http-local',))
        self.catalog=NodeCatalog(self.tasks.store)
        self.requests=Requests(self,root=folder,inventory_loader=lambda:self.inventory)
        self.workers=[threading.Thread(target=self.request_loop,args=(inbox,),daemon=True)
                      for inbox in (self.inbox,self.task_inbox)]
        for worker in self.workers:worker.start()
    def refresh_inventory(self):pass
    def close(self):
        self.stopped.set()
        for worker in self.workers:worker.join(2)
        self.tasks.close()


class Topology(unittest.TestCase):
    def test_all_new_role_dry_runs_are_isolated_without_enrollment(self):
        import subprocess
        root=Path(__file__).resolve().parents[2]
        for role,node in [('ugv_root','ugv-root'),('ugv','ugv-001'),('uav','uav-001'),('micro_uav','micro-001')]:
            result=subprocess.run([sys.executable,str(root/'tools/lab.py'),'--role',role,
                '--node-id',node,'--transport','mqtt_serial','--inventory',str(root/'config/nodes.json'),
                '--dry-run'],capture_output=True,text=True)
            self.assertEqual(0,result.returncode,result.stderr)
            self.assertIn('UGV ID: ugv-root',result.stdout)
            self.assertIn(role+'-chain',result.stdout)

    def test_migration_clients_root_scope_acl_and_revocation(self):
        original=defaults();new=defaults()
        self.assertEqual('ugv_root',original['nodes'][0]['role'])
        self.assertEqual('ugv_root',new['nodes'][0]['role'])
        self.assertIn('ugv-001',clients(new));self.assertNotIn('http-local',clients(new))
        with tempfile.TemporaryDirectory() as folder:
            write_acl(folder,new);acl=(Path(folder)/'runtime/ugv-root/acl.conf').read_text()
            self.assertIn('user ugv-001\n',acl)
            self.assertIn('topic read mesh/v1/nodes/ugv-001/task_commands',acl)
            self.assertNotIn('user ugv-root\n',acl)
        new['nodes'][1]['trust_status']='revoked'
        self.assertNotIn('ugv-001',clients(new))
        new['nodes'][1]['root_id']='missing'
        with self.assertRaises(ValueError):validate(new)

    def test_root_configuration_does_not_touch_enrolled_credentials(self):
        from provision_mqtt import provision
        from identity_env import ensure_identity
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            with contextlib.redirect_stdout(io.StringIO()):provision(root)
            before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'secrets').rglob('*') if p.is_file()}
            inventory=root/'new.json';inventory.write_text(json.dumps(defaults()))
            record=ensure_identity(root,'ugv_root','ugv-root','ugv-root',inventory_path=inventory)
            self.assertEqual('ugv-root',record['node_id'])
            self.assertFalse(record['created'])
            self.assertEqual(before,{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'secrets').rglob('*') if p.is_file()})

    def test_renamed_root_radio_report_and_alias_restriction(self):
        from changan_ugv.nodes.network import NetworkStatusFile,read_network_status
        data=defaults()
        self.assertTrue(all(e['root_id']=='ugv-root' for e in data['nodes']))
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            writer=NetworkStatusFile(root/'runtime/ugv-network.json','ugv-root',clock=lambda:100)
            writer(dict(v=1,type='network',node_id='ugv-root',payload=dict(role='ugv_root',level=1)),42)
            self.assertTrue(read_network_status('ugv-root',root,clock=lambda:101)['fresh'])
            self.assertIsNone(read_network_status('http-local',root,clock=lambda:101))
        data['nodes'][1]['credential_id']='http-local'
        with self.assertRaisesRegex(ValueError,'aliases'):validate(data)


class HTTPContract(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory();self.folder=Path(self.temp.name)
        self.service=Harness(self.folder)
        self.client=TestClient(TestServer(application(self.service)))
        await self.client.start_server()

    async def asyncTearDown(self):
        await self.client.close()
        await asyncio.to_thread(self.service.close)
        self.temp.cleanup()

    async def post(self,body):
        reply=await self.client.post('/api/v1/requests',json=body)
        self.assertEqual(200,reply.status)
        return await reply.json()

    async def test_local_identity_duplicate_conflict_revision_and_persistence(self):
        create=packet('task.create',node_id='local-console',task_id='local-job',target='ugv-001',kind='diagnostics',config={})
        first=await self.post(create)
        self.assertEqual('CREATED',first['task']['state'])
        self.assertEqual(first,await self.post(create))
        self.assertEqual('msg_id_conflict',(await self.post(dict(create,config={'duration_s':2})))['error'])
        self.assertEqual('revision_conflict',(await self.post(packet('task.control',task_id='local-job',op='start',expected_revision=8)))['error'])
        start=await self.post(packet('task.control',task_id='local-job',op='start',expected_revision=1))
        self.assertEqual('UGV_RECEIVED',start['stage'])
        self.service.tasks.tick()
        self.assertEqual('ugv-001',self.service.channel.sent[0][0])
        self.assertEqual('http-local',self.service.tasks.store._row('local-job')['owner'])
        self.service.close();self.service=Harness(self.folder)
        self.assertEqual('RECONCILING',self.service.tasks.store._row('local-job')['state'])

    async def test_websocket_replays_cursor_and_survives_broker_outage(self):
        await self.post(packet('task.create',task_id='events-job',target='ugv-001',kind='diagnostics',config={}))
        async with self.client.ws_connect('/api/v1/events?cursor=0') as ws:
            event=await ws.receive_json(timeout=3)
            self.assertEqual('task.event',event['type']);cursor=event['cursor']
        self.service.connected.clear();self.service.channel.online=False
        await self.post(packet('task.control',task_id='events-job',op='cancel',expected_revision=1))
        async with self.client.ws_connect(f'/api/v1/events?cursor={cursor}') as ws:
            event=await ws.receive_json(timeout=3)
            self.assertGreater(event['cursor'],cursor);self.assertEqual('CANCELLED',event['state'])

    async def test_validation_loopback_origin_and_node_trust(self):
        reply=await self.client.post('/api/v1/requests',data='{"v":1,"v":1}')
        self.assertEqual(400,reply.status)
        reply=await self.client.post('/api/v1/requests',json=packet(),headers={'Origin':'https://untrusted.example'})
        self.assertEqual(403,reply.status)
        reply=await self.client.get('/api/v1/events?cursor=-1')
        self.assertEqual(400,reply.status)
        self.assertEqual('invalid_request',(await self.post(packet([])))['error'])
        self.assertEqual('expired_or_invalid_deadline',(await self.post(dict(packet(),deadline_unix=1)))['error'])
        self.service.inventory['nodes'][1]['trust_status']='revoked'
        rows=(await self.post(packet()))['nodes']
        row=next(r for r in rows if r['node_id']=='ugv-001')
        self.assertEqual('revoked',row['trust_status'])
        response=await self.post(packet('task.create',task_id='denied',target='ugv-001',kind='diagnostics',config={}))
        self.assertEqual('target_not_authorized',response['error'])
        self.service.catalog.update(self.service.inventory['nodes'],[])
        self.assertEqual(len(self.service.inventory['nodes']),len(self.service.catalog.records()))

    async def test_independent_terminal_http_and_actual_ws(self):
        import sys
        car=Path(__file__).resolve().parents[3]/'changan-car-terminal'
        if not car.is_dir():self.skipTest('Independent terminal not available')
        sys.path.insert(0,str(car))
        from car_terminal.transport.http import HTTPClient
        client=await asyncio.to_thread(HTTPClient,str(self.client.make_url('')).rstrip('/'))
        captured=queue.Queue();client.on_event=captured.put
        try:
            created=await asyncio.to_thread(client.request,packet('task.create',task_id='terminal-job',target='ugv-001',kind='diagnostics',config={}))
            self.assertEqual('CREATED',created['task']['state'])
            deadline=time.monotonic()+4
            while time.monotonic()<deadline:
                try:event=captured.get_nowait()
                except queue.Empty:await asyncio.sleep(.05);continue
                if event.get('type')=='task.event':break
            else:self.fail('Independent terminal received no WS task event')
            self.assertEqual('terminal-job',event['task_id'])
            self.assertEqual('nodes',(await asyncio.to_thread(client.request,packet()))['type'])
        finally:await asyncio.to_thread(client.close)
