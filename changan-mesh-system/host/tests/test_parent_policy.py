"""Parent-selection intent, real HTTP contract and reconciliation; no IDF or COM."""
import asyncio
import json
from pathlib import Path
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from aiohttp.test_utils import TestClient,TestServer
from changan_ugv.nodes.inventory import defaults
from changan_ugv.nodes.parent_policy import ParentPolicies
from changan_ugv.tasks.store import Store
from changan_ugv.service.requests import Requests
from changan_ugv.api.server import application

class ParentPolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=Store(Path(self.temp.name)/'tasks.sqlite3');self.addCleanup(self.store.close)
        self.inventory=defaults();self.sent=[]
        self.rows=[dict(node_id='micro-001',ready=True,operations=['parent'],status={}),
            dict(node_id='uav-001',ready=True,status=dict(level=3,ap_enabled=True,
                 ap_mac='aa:bb:cc:00:00:01',ap_ssid='changan_000001',parent_auth=dict(relay_authorized=True)))]
        self.controller=SimpleNamespace(condition=threading.Condition(),
            registry=SimpleNamespace(snapshot=lambda:self.rows),command=self.send)
        self.manager=ParentPolicies(self.store,self.controller,lambda:self.inventory,'ugv-root')
    def send(self,*args,**kwargs):
        self.sent.append((args,kwargs));return dict(ok=True)
    def request(self,**fields):
        return dict(v=1,type='node.parent',node_id='http-local',msg_id='bind-one',target='micro-001',
                    mode='fixed',parent='uav-001',expected_revision=0,deadline_unix=int(time.time())+30,**fields)
    def test_ack_is_only_accepted_and_matching_fresh_parent_proves_application(self):
        request=self.request();result=self.manager.change(request)
        self.assertEqual('accepted',result['state'])
        self.assertEqual('parent',self.sent[0][0][1])
        config=self.sent[0][0][2]
        self.assertEqual('aa:bb:cc:00:00:01',config['bssid'])
        status=self.rows[0]['status'];status.update(parent_connected=True,parent_bssid='aa:bb:cc:00:00:02',
            parent_policy=dict(revision=result['revision'],mode='fixed',stage='active'))
        self.assertEqual('waiting',self.manager.get('micro-001')['state'])
        status['parent_bssid']=config['bssid'];status['parent_policy']['stage']='pending'
        self.assertEqual('waiting',self.manager.get('micro-001')['state'])
        status['parent_policy']['stage']='active'
        self.assertEqual('applied',self.manager.get('micro-001')['state'])
        self.rows[0]['ready']=False
        self.assertEqual('accepted',self.manager.get('micro-001')['state'])
    def test_duplicate_conflict_revision_and_service_restart_never_repeat_dispatch(self):
        request=self.request();self.manager.change(request);self.manager.change(request)
        self.assertEqual(1,len(self.sent))
        with self.assertRaisesRegex(ValueError,'msg_id_conflict'):self.manager.change(dict(request,mode='prefer'))
        with self.assertRaisesRegex(ValueError,'revision_conflict'):self.manager.change(dict(request,msg_id='other'))
        restarted=ParentPolicies(self.store,self.controller,lambda:self.inventory,'ugv-root')
        restarted.change(request);self.assertEqual(1,len(self.sent))
    def test_parent_and_child_authorization_layer_radio_freshness(self):
        cases=[('child-role',lambda:self.inventory['nodes'][3].update(role='uav')),
               ('old-child',lambda:self.rows[0].update(operations=['ping','status'])),
               ('child-offline',lambda:self.rows[0].update(ready=False)),
               ('revoke',lambda:self.inventory['nodes'][2].update(trust_status='revoked')),
               ('wrong-root',lambda:self.inventory['nodes'][2].update(root_id='other')),
               ('offline',lambda:self.rows[1].update(ready=False)),
               ('no-relay-grant',lambda:self.rows[1]['status'].update(parent_auth=dict(relay_authorized=False))),
               ('old-parent-firmware',lambda:self.rows[1]['status'].pop('parent_auth')),
               ('wrong-level',lambda:self.rows[1]['status'].update(level=2)),
               ('no-ssid',lambda:self.rows[1]['status'].pop('ap_ssid'))]
        import copy
        for name,change in cases:
            with self.subTest(name=name):
                original_inventory,original_rows=copy.deepcopy(self.inventory),copy.deepcopy(self.rows)
                change()
                with self.assertRaises(ValueError):self.manager.change(self.request())
                self.assertEqual([],self.sent)
                self.inventory,self.rows=original_inventory,original_rows
    def test_timeout_retains_uncertainty_and_preferred_fallback_is_distinct(self):
        def timeout(*args,**kwargs):self.sent.append(args);raise TimeoutError('no ack')
        self.controller.command=timeout
        request=dict(self.request(),mode='prefer')
        result=self.manager.change(request);self.assertEqual('uncertain',result['state'])
        self.manager.change(request);self.assertEqual(1,len(self.sent))
        self.rows[0]['status'].update(parent_connected=True,parent_bssid='aa:bb:cc:00:00:02',
            parent_policy=dict(mode='prefer',revision=result['revision'],stage='fallback'))
        self.assertEqual('fallback',self.manager.get('micro-001')['state'])
        self.controller.command=self.send
        reset=dict(request,msg_id='reset',mode='auto',parent=None,expected_revision=result['revision'])
        self.assertEqual('auto',self.manager.change(reset)['mode'])
    def test_actual_loopback_http_uses_versioned_parent_contract(self):
        async def exercise():
            service=self.controller
            service.parents=self.manager
            requests=Requests(service,inventory_loader=lambda:self.inventory)
            service.submit_local=requests.handle
            async with TestClient(TestServer(application(service))) as client:
                response=await client.post('/api/v1/requests',json=self.request())
                body=await response.json()
                self.assertTrue(body['ok']);self.assertEqual('accepted',body['state'])
                query=dict(self.request(),type='node.parent.get',msg_id='read-back')
                body=await (await client.post('/api/v1/requests',json=query)).json()
                self.assertEqual(1,body['revision']);self.assertEqual(1,len(self.sent))
        asyncio.run(exercise())

if __name__=='__main__':unittest.main()
