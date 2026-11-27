"""Durable application receipts, correlation, deadline failures and actual HTTP contract."""
import csv
import io
import json
from pathlib import Path
import tempfile
import unittest
import uuid
from types import SimpleNamespace
from aiohttp.test_utils import TestClient,TestServer
from changan_ugv.nodes.capability_measurements import CapabilityMeasurements
from changan_ugv.tasks.store import Store
from changan_ugv.api.server import application


class Measurements(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'tasks.db';self.store=Store(self.path);self.addCleanup(lambda:self.store.close())
        self.now=100.;self.sent=[]
        self.info={'micro-001':dict(ready=True,supported=True,boot_id='a'*16,role='micro_uav'),
                   'uav-001':dict(ready=True,supported=True,boot_id='b'*16,role='uav')}
        self.manager=CapabilityMeasurements(self.store,self.info.get,self.send,clock=lambda:self.now)
        self.batch=uuid.uuid4().hex

    def send(self,node,body):self.sent.append((node,body));return True

    def start(self,count=1):
        return self.manager.start(dict(batch_id=self.batch,nodes=list(self.info),count=count,period_ms=200))

    def announce(self,node,seq=1,probe=None,**overrides):
        boot=self.info[node]['boot_id']
        body=dict(v=1,type='capabilities',node_id=node,boot_id=boot,cap_measure_v=1,
                  cap_seq=seq,cap_id=f'{boot}-{seq:08x}',sent_us=1000000,task_role=self.info[node]['role'],
                  task_types=['diagnostics'],operations=['ping','status'],task_status='IDLE')
        if probe:body.update(probe_id=probe['probe_id'],batch_id=probe['batch_id'])
        body.update(overrides);return body

    def complete(self,node,cap,elapsed=800000):
        receipt=self.sent[-1][1]
        result=dict(v=1,type='cap.result',node_id=node,boot_id=cap['boot_id'],cap_id=cap['cap_id'],cap_seq=cap['cap_seq'],
                    receipt_token=receipt['receipt_token'],elapsed_us=elapsed,confirmed_us=cap['sent_us']+elapsed)
        self.manager.result(node,result);return result

    def test_commit_before_receipt_and_threshold_uses_unrounded_microseconds(self):
        self.start();self.manager.tick()
        requests={n:p for n,p in self.sent};self.sent.clear()
        for node,elapsed in [('micro-001',800000),('uav-001',800001)]:
            cap=self.announce(node,probe=requests[node]);self.manager.announcement(node,cap,False,self.now)
            with self.store.lock:
                self.assertIsNotNone(self.store.db.execute('SELECT raw FROM cap_announcements WHERE node_id=?',(node,)).fetchone())
            self.complete(node,cap,elapsed)
        body=self.manager.get(self.batch);summary=body['summary']
        self.assertTrue(summary['complete']);self.assertEqual(1,summary['proved_within_800ms'])
        self.assertEqual(1,summary['states']['UPPER_BOUND_EXCEEDED'])
        self.assertEqual(800.001,summary['max_ms'])
        self.assertEqual('capability_receipt_rtt_upper_bound',body['metric'])
        self.assertTrue(all(r['agent_type'] and r['task_status'] and r['basic_capabilities'] for r in body['items']))

    def test_retained_wrong_source_wrong_probe_and_wrong_token_never_prove_success(self):
        self.start();self.manager.tick();node,request=self.sent[0];cap=self.announce(node,probe=request)
        count=len(self.sent)
        self.manager.announcement(node,cap,True,self.now)
        self.manager.announcement('foreign',cap,False,self.now)
        self.manager.announcement(node,dict(cap,probe_id='unknown'),False,self.now)
        self.assertEqual(count,len(self.sent))
        self.manager.announcement(node,cap,False,self.now)
        receipt=self.sent[-1][1]
        bad=dict(v=1,type='cap.result',node_id=node,boot_id=cap['boot_id'],cap_id=cap['cap_id'],cap_seq=1,
                 receipt_token='wrong',elapsed_us=5,confirmed_us=1000005)
        self.manager.result(node,bad)
        self.assertEqual(0,self.manager.get(self.batch)['summary']['confirmed'])
        self.manager.result(node,dict(bad,receipt_token=receipt['receipt_token'],confirmed_us=7))
        self.assertEqual(0,self.manager.get(self.batch)['summary']['confirmed'])
        self.manager.announcement(node,cap,False,self.now)
        self.assertEqual(receipt,self.sent[-1][1])
        self.assertEqual(1,self.store.db.execute('SELECT duplicates FROM cap_announcements').fetchone()[0])
        self.complete(node,cap,100)
        self.assertEqual(1,self.manager.get(self.batch)['summary']['confirmed'])

    def test_timeout_missing_announcement_and_restart_keep_all_planned_samples(self):
        self.start(count=2);self.manager.tick();self.now+=6;self.manager.tick()
        body=self.manager.get(self.batch)
        self.assertEqual(4,body['summary']['total']);self.assertEqual(2,body['summary']['states']['TIMEOUT'])
        self.assertIsNone(body['summary']['avg_ms'])
        CapabilityMeasurements(self.store,self.info.get,self.send,clock=lambda:self.now)
        self.assertEqual(2,self.manager.get(self.batch)['summary']['states']['INTERRUPTED'])
        before=len(self.sent);self.manager.tick();self.assertEqual(before,len(self.sent))

    def test_replay_conflict_permissions_and_reboot_do_not_publish(self):
        self.start();self.assertEqual(self.start()['batch_id'],self.batch)
        with self.assertRaisesRegex(ValueError,'conflict'):self.start(count=2)
        self.info['micro-001']['boot_id']='c'*16
        self.info.pop('uav-001')
        self.manager.tick();self.assertEqual([],self.sent)
        self.assertEqual(2,self.manager.get(self.batch)['summary']['states']['NOT_READY'])

    def test_node_timeout_and_exports_preserve_raw_evidence(self):
        self.start();self.manager.tick();node,request=self.sent[0];cap=self.announce(node,probe=request)
        self.manager.announcement(node,cap,False,self.now)
        self.manager.result(node,dict(v=1,type='cap.result',node_id=node,boot_id=cap['boot_id'],cap_id=cap['cap_id'],cap_seq=1,error='receipt_timeout'))
        body=self.manager.get(self.batch);self.assertEqual(1,body['summary']['states']['TIMEOUT'])
        records=[json.loads(line) for line in self.manager.export(self.batch,'jsonl').splitlines()]
        self.assertEqual(3,len(records));self.assertEqual('summary',records[0]['kind'])
        self.assertTrue(any(r.get('announcement')==cap for r in records[1:]))
        rows=list(csv.DictReader(io.StringIO(self.manager.export(self.batch,'csv'))))
        self.assertEqual(2,len(rows));self.assertEqual('800',rows[0]['threshold_ms'])

    def test_readiness_feature_and_input_limits_are_required(self):
        self.info['micro-001']['supported']=False
        with self.assertRaisesRegex(ValueError,'firmware'):self.start()
        with self.assertRaises(ValueError):self.start(count=101)
        with self.assertRaises(ValueError):self.manager.start(dict(batch_id='x',nodes=['micro-001']))

    def test_invalid_result_ids_and_stale_boot_never_modify_samples(self):
        self.start();self.manager.tick();node,request=self.sent[0];cap=self.announce(node,probe=request)
        self.manager.announcement(node,cap,False,self.now)
        for bad in ([],{},None,123):
            self.manager.result(node,dict(v=1,type='cap.result',node_id=node,cap_id=bad))
        self.manager.result(node,dict(v=1,type='cap.result',node_id=node,cap_id=cap['cap_id'],boot_id='other',cap_seq=1,error='receipt_timeout'))
        self.assertEqual(0,self.manager.get(self.batch)['summary']['confirmed'])

    def test_required_agent_capability_and_task_fields_must_be_present(self):
        self.start();self.manager.tick();node,request=self.sent[0];cap=self.announce(node,probe=request)
        before=len(self.sent)
        for field in ('task_role','task_types','task_status'):
            invalid=dict(cap);invalid.pop(field)
            self.manager.announcement(node,invalid,False,self.now)
        self.assertEqual(before,len(self.sent))
        self.assertEqual(0,self.manager.get(self.batch)['summary']['confirmed'])

    def test_largest_protocol_messages_fit_existing_node_frame_limits(self):
        from changan_ugv.protocol.messages import encode
        node='n'*32;boot='a'*16;cap_id=boot+'-ffffffff'
        cap=dict(v=1,type='capabilities',node_id=node,boot_id=boot,cap_id=cap_id,cap_seq=0xffffffff,sent_us=2**53-1,
            cap_measure_v=1,probe_id='b'*32,batch_id='c'*32,task_role='micro_uav',task_types=['diagnostics','patrol'],
            task_operations=['start','pause','resume','cancel','query'],operations=['ping','status','echo','parent'],
            task_status='RUNNING',task_id='t'*32,execution_mode='esp32_test')
        self.assertLessEqual(len(encode(cap)),1024)
        for body in [dict(type='cap.request',target=node,boot_id=boot,batch_id='b'*32,probe_id='c'*32,deadline_unix=2147483647),
                     dict(type='cap.receipt',target=node,boot_id=boot,cap_id=cap_id,cap_seq=0xffffffff,receipt_token='d'*32),
                     dict(type='cap.result',node_id=node,boot_id=boot,cap_id=cap_id,cap_seq=0xffffffff,receipt_token='d'*32,
                          confirmed_us=2**53-1,elapsed_us=2000000)]:
            self.assertLessEqual(len(encode(dict(v=1,**body))),512)


class HTTPMeasurements(unittest.IsolatedAsyncioTestCase):
    async def test_versioned_api_persistence_and_export(self):
        with tempfile.TemporaryDirectory() as directory:
            store=Store(Path(directory)/'tasks.db')
            try:
                manager=CapabilityMeasurements(store,lambda n:dict(ready=True,supported=True,boot_id='a'*16,role='ugv'),lambda *a:True)
                service=SimpleNamespace(capability_measurements=manager)
                async with TestClient(TestServer(application(service))) as client:
                    batch=uuid.uuid4().hex
                    response=await client.post('/api/v1/capability-tests',json=dict(batch_id=batch,nodes=['ugv-001'],count=1))
                    self.assertEqual(200,response.status);self.assertEqual(1,(await response.json())['summary']['total'])
                    response=await client.get('/api/v1/capability-tests/'+batch)
                    self.assertEqual(batch,(await response.json())['batch_id'])
                    response=await client.get('/api/v1/capability-tests/'+batch+'/export?format=jsonl')
                    self.assertEqual(2,len((await response.text()).splitlines()))
                    response=await client.get('/api/v1/capability-tests')
                    self.assertEqual(batch,(await response.json())['items'][0]['batch_id'])
                    response=await client.post('/api/v1/capability-tests',json={},headers={'Origin':'https://untrusted.example'})
                    self.assertEqual(403,response.status)
            finally:store.close()
