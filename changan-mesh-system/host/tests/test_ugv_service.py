"""HTTP request routing, ACL separation and controller exclusivity."""
from pathlib import Path
import tempfile
import threading
import unittest
from types import SimpleNamespace
from changan_ugv.nodes.controller import Registry
from changan_ugv.nodes.inventory import defaults,write_inventory,render_acl
from changan_ugv.service.requests import Requests
class ServiceRequests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);write_inventory(self.root,defaults())
        self.calls=[];self.connected=threading.Event();self.connected.set()
        def command(node,op,text,**kwargs):
            self.calls.append((node,op));return dict(v=1,type='ack',node_id=node,msg_id=kwargs['msg_id'],ok=True,payload=text)
        self.c=SimpleNamespace(connected=self.connected,condition=threading.Condition(),registry=Registry(nodes=['uav-001']),
            refresh_inventory=lambda:None,command=command)
        self.api=Requests(self.c,self.root,clock=lambda:1000)
    def packet(self,**fields):return dict(v=1,type='command',msg_id='request',deadline_unix=1020,target='uav-001',op='ping',**fields)
    def test_request_id_duplicates_conflicts_and_deadline(self):
        first=self.api.handle(self.packet());self.assertEqual(first,self.api.handle(self.packet()))
        self.assertEqual(1,len(self.calls))
        changed=self.packet();changed['op']='status'
        self.assertEqual('msg_id_conflict',self.api.handle(changed)[0]['error'])
        expired=self.packet();expired.update(msg_id='expired',deadline_unix=1)
        self.assertEqual('expired_or_invalid_deadline',self.api.handle(expired)[0]['error'])
    def test_malformed_command_is_rejected_and_body_cannot_choose_owner(self):
        packet=self.packet();packet['target']={}
        self.assertEqual('invalid_command',self.api.handle(packet)[0]['error'])
        self.assertTrue(self.api.handle(self.packet(node_id='forged-owner'))[0]['ok'])
        self.assertEqual('http_transport_required',self.api.handle(self.packet(),local=False)[0]['error'])
    def test_no_terminal_topics_and_root_is_not_a_mqtt_client(self):
        acl=render_acl(defaults())
        self.assertNotIn('terminals/',acl);self.assertNotIn('user ugv-root\n',acl)
        self.assertIn('topic read mesh/v1/nodes/ugv-001/task_commands',acl)
class SingleManager(unittest.TestCase):
    def test_controller_identity_is_exclusive_and_reusable(self):
        from changan_ugv.nodes.lease import Lease
        with tempfile.TemporaryDirectory() as directory:
            first=Lease(directory)
            try:
                with self.assertRaises(ValueError):Lease(directory)
            finally:first.close()
            Lease(directory).close()
