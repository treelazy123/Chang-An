"""Headless/compatibility request tests with fake nodes, no live Broker or serial devices."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'))
from mqtt_controller import Registry
from node_inventory import defaults,write_inventory,write_acl
from ugv_requests import Requests
from ugv_rpc import Server,LocalController
from mesh_protocol import encode
class FakeController:
    def __init__(self):
        self.connected=threading.Event();self.connected.set();self.condition=threading.Condition()
        self.registry=Registry(nodes=['uav-001','micro-001']);self.calls=[]
    def refresh_inventory(self):pass
    def command(self,node,op,text=None,**kwargs):
        self.calls.append((node,op,text,kwargs))
        if op not in ('ping','status','echo'):raise ValueError('Unknown operation')
        return dict(v=1,type='ack',node_id=node,msg_id=kwargs['msg_id'],ok=True,payload=text)
class ServiceRequests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        write_inventory(self.root,defaults());self.c=FakeController();self.api=Requests(self.c,self.root,clock=lambda:1000)
    def packet(self,kind='command',identity='abc',**kwargs):
        return dict(v=1,type=kind,msg_id=identity,node_id='pc-root-001',deadline_unix=1020,**kwargs)
    def test_car_request_routes_and_target_ack_keeps_request_id(self):
        reply=self.api.handle(self.packet(target='micro-001',op='echo',payload='hello'),'pc-root-001')
        self.assertEqual('micro-001',reply[0]['node_id']);self.assertEqual('abc',reply[0]['msg_id'])
        self.assertEqual('hello',reply[0]['payload']);self.assertEqual(1,len(self.c.calls))
    def test_list_is_paginated_and_each_frame_is_within_c6_limit(self):
        for i in range(100):self.c.registry.nodes['node-'+str(i)]={}
        replies=self.api.handle(self.packet('list'),'pc-root-001')
        self.assertEqual(103,len(replies));self.assertFalse(replies[-1]['more'])
        for row in replies:self.assertLessEqual(len(encode(row)),1032)
    def test_duplicates_are_replayed_conflicts_and_expired_requests_rejected(self):
        request=self.packet(target='uav-001',op='ping')
        first=self.api.handle(request,'pc-root-001');second=self.api.handle(request,'pc-root-001')
        self.assertEqual(first,second);self.assertEqual(1,len(self.c.calls))
        conflict=self.api.handle(dict(request,op='status'),'pc-root-001')
        self.assertEqual('msg_id_conflict',conflict[0]['error'])
        expired=self.api.handle(dict(request,msg_id='new',deadline_unix=999),'pc-root-001')
        self.assertEqual('expired_or_invalid_deadline',expired[0]['error'])
    def test_malformed_command_cannot_kill_the_dispatch_worker(self):
        for target,op in [({},'ping'),('uav-001',{}),('uav-001','execute')]:
            response=self.api.handle(self.packet(target=target,op=op),'pc-root-001')
            self.assertEqual('invalid_command',response[0]['error'])
        self.assertFalse(self.c.calls)
        self.assertTrue(self.api.handle(self.packet(identity='valid',target='uav-001',op='ping'),'pc-root-001')[0]['ok'])
    def test_unauthorized_or_forged_source_does_not_dispatch(self):
        request=self.packet(target='uav-001',op='ping')
        for source in ('micro-001','stranger'):
            self.assertEqual('terminal_not_authorized',self.api.handle(request,source)[0]['error'])
        self.assertFalse(self.c.calls)
    def test_role_permissions_and_local_console_does_not_stop_backend(self):
        data=defaults();write_acl(self.root,data);acl=(self.root/'runtime/acl.conf').read_text()
        self.assertIn('topic write mesh/v1/terminals/pc-root-001/requests',acl)
        self.assertNotIn('topic write mesh/v1/terminals/micro-001/requests',acl)
        # Bind an ephemeral test port, not the actual service or Broker port.
        server=Server(0,self.api);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            local=LocalController.discover(server.server_address[1]);self.assertIsNotNone(local)
            # Local RPC creates deadlines from wall time; use actual time for this integration.
            import time
            self.api.clock=time.time
            self.assertEqual(2,len(local.snapshot()))
            self.assertTrue(local.command('uav-001','ping')['ok'])
            local.close();self.assertTrue(self.c.connected.is_set())
            again=LocalController.discover(server.server_address[1]);self.assertEqual(2,len(again.snapshot()))
        finally:server.shutdown();server.server_close();thread.join(2)
class SingleManager(unittest.TestCase):
    def test_controller_identity_is_exclusive_and_reusable_after_close(self):
        from controller_lease import Lease
        with tempfile.TemporaryDirectory() as directory:
            first=Lease(directory)
            try:
                with self.assertRaises(ValueError):Lease(directory)
            finally:first.close()
            second=Lease(directory);second.close()

if __name__=='__main__':unittest.main()
