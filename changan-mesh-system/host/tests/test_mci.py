"""MCI contracts, independent permissions and real loopback adapters; no devices."""
import asyncio
import copy
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from aiohttp.test_utils import TestClient,TestServer
from jsonschema import Draft202012Validator, ValidationError
from changan_ugv.mci import MCI, definitions, validate_catalog
from changan_ugv.api.server import application
from test_root_http import Harness

def call(method,params=None,service='Mesh_Task',**extra):
    return dict(dict(service=service,method=method,params=params or {},requestId='mci-test',deadlineUnix=int(time.time())+30),**extra)

class MCITests(unittest.TestCase):
    def test_nullable_object_and_array_descriptors_require_explicit_structure(self):
        for schema in [dict(type=['object','null']),dict(type='array'),None]:
            rows=definitions()
            if schema is None:rows['Mesh_Task','Get_Task'][0]['inputSchema']=None
            else:rows['Mesh_Task','Get_Task'][0]['inputSchema']['properties']['example']=dict(schema,description='示例&用于验证发布约束。')
            with self.subTest(schema=schema),self.assertRaises(ValueError):validate_catalog(rows)
    def test_notification_replay_cursor_is_outside_business_payload(self):
        result=MCI(None).notification('Mesh_Task','Ntf_TaskChanged',dict(task_id='task-1',state='CREATED',cursor=3))
        self.assertEqual(3,result['cursor'])
        self.assertNotIn('cursor',result['params'])
    def test_independent_terminal_sends_real_mci_and_captures_raw_json(self):
        import sys
        sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'changan-car-terminal'))
        from car_terminal.transport.http import HTTPClient
        async def exercise():
            with tempfile.TemporaryDirectory() as folder:
                h=Harness(Path(folder))
                try:
                    async with TestClient(TestServer(application(h))) as server:
                        terminal=await asyncio.to_thread(HTTPClient,str(server.make_url('/')).rstrip('/'),events=False)
                        try:
                            captured=[];terminal.on_wire=captured.append
                            packet=dict(v=1,type='task.create',msg_id='terminal-create',deadline_unix=int(time.time())+30,
                                target='ugv-001',task_id='terminal-task',kind='diagnostics',config=dict(duration_s=3,period_ms=500))
                            result=await asyncio.to_thread(terminal.request,packet)
                            self.assertEqual('CREATED',result['task']['state'])
                            self.assertEqual('Mesh_Task',captured[0]['request']['service'])
                            self.assertEqual(3,captured[0]['request']['params']['config']['durationSeconds'])
                            self.assertEqual('terminal-task',captured[0]['response']['result']['task']['taskId'])
                            self.assertEqual('/api/v1/mci/call',captured[0]['path'])
                            self.assertEqual(result,await asyncio.to_thread(terminal.request,packet))
                            discovery=await asyncio.to_thread(terminal.discover)
                            self.assertEqual('1.0.0',discovery['specVersion'])
                        finally:await asyncio.to_thread(terminal.close)
                finally:h.close()
        asyncio.run(exercise())
    def test_catalog_filter_sort_and_isolation(self):
        m=MCI(None);all_rows=m.discover({})
        self.assertEqual(['specVersion','services'],list(all_rows))
        self.assertEqual(4,len(all_rows['services']))
        rows=m.discover(dict(method='Cnr_CreateTask'))['services']
        self.assertEqual('Mesh_Task',rows[0]['service'])
        self.assertEqual([],m.discover(dict(service='Other_Service'))['services'])
        for bad in ({'service':''},{'service':'mesh_task'},{'unknown':1},{'method':'*'},[]):
            self.assertEqual('INVALID_ARGUMENT',m.discover(bad)['error']['code'])
        rows[0]['methods'][0]['method']='Changed'
        self.assertEqual(23,len(m.rows))
        self.assertEqual('Cnr_CreateTask',m.discover(dict(method='Cnr_CreateTask'))['services'][0]['methods'][0]['method'])
    def test_kind_and_config_are_bound_and_validate_recursively(self):
        schema=definitions()['Mesh_Task','Cnr_CreateTask'][0]['inputSchema']
        valid=dict(executorNodeId='ugv-root',taskId='task',kind='network_diagnostics',config=dict(probeNodeId='micro-001'))
        Draft202012Validator(schema).validate(valid)
        Draft202012Validator(schema).validate(dict(valid,config=dict(probeNodeId='micro-001',durationSeconds=120)))
        for bad in (dict(valid,kind='task_monitor'),dict(valid,config=dict(watchTaskId='task')),
                    dict(valid,config=dict(probe_node='micro-001')),dict(valid,kind='camp_survey'),
                    dict(valid,config=dict(probeNodeId='micro-001',periodMs=100)),dict(valid,token='x')):
            with self.assertRaises(ValidationError):Draft202012Validator(schema).validate(bad)
    def test_discovery_and_invocation_permissions_are_independent(self):
        m=MCI(None,authorize=lambda action,key:action!='invoke')
        self.assertTrue(m.discover({})['services'])
        self.assertEqual('PERMISSION_DENIED',m.call(call('Get_Task',dict(taskId='task')))['error']['code'])
        m=MCI(None,authorize=lambda action,key:action!='discover')
        self.assertEqual('PERMISSION_DENIED',m.discover({})['error']['code'])
    def test_schema_invalid_catalog_and_one_way_calls(self):
        m=MCI(None)
        m.rows['Mesh_Task','Cnr_CreateTask'][0]['inputSchema']['properties']['bad_key']={'type':'string'}
        self.assertEqual('CATALOG_INVALID',m.discover({})['error']['code'])
        m=MCI(None)
        self.assertEqual('INVALID_ARGUMENT',m.call(call('Ntf_TaskChanged'))['error']['code'])
    def test_invalid_publication_retains_previous_catalog(self):
        m=MCI(None);before=m.discover({});rows=definitions()
        rows['Mesh_Task','Get_Task'][0]['inputSchema']['properties']['taskId']['$ref']='https://example.invalid/schema'
        with self.assertRaises(ValueError):m.publish(rows)
        self.assertEqual(before,m.discover({}))
    def test_node_status_catalog_and_instance_views(self):
        status=dict(role='micro_uav',ap_enabled=False,parent_connected=True,sta_ip='192.168.8.2',
                    parent_policy=dict(mode='auto',revision=0,parent=None,stage='active'))
        seen=[]
        def submit(p):
            seen.append(p)
            if p['type']=='command':return [dict(type='ack',ok=True,payload=status)]
            return [dict(type='nodes',nodes=[dict(node_id='micro-001',ready=True,status=status)])]
        m=MCI(SimpleNamespace(submit_local=submit))
        result=m.call(call('Get_NodeList',service='Mesh_Node'))['result']
        self.assertEqual('192.168.8.2',result['nodes'][0]['status']['staIp'])
        self.assertEqual('auto',result['nodes'][0]['status']['parentPolicy']['mode'])
        result=m.call(call('Get_Status',service='Mesh_Node',target='micro-001'))['result']
        self.assertFalse(result['apEnabled'])
        self.assertEqual('micro-001',seen[-1]['target'])
        self.assertEqual('status',seen[-1]['op'])
    def test_parent_command_mapping_and_receipt_stage(self):
        seen=[]
        def submit(p):
            seen.append(p);return [dict(type='node.parent.reply',target=p['target'],mode=p['mode'],parent=p['parent'],revision=3,state='accepted')]
        m=MCI(SimpleNamespace(submit_local=submit))
        result=m.call(call('Cnr_SetPolicy',dict(mode='fixed',parentNodeId='uav-001',expectedRevision=2),service='Mesh_Parent',target='micro-001'))
        self.assertEqual('accepted',result['result']['state'])
        self.assertEqual('uav-001',seen[0]['parent'])
        self.assertEqual('micro-001',seen[0]['target'])
        self.assertNotIn('target',result['result'])
    def test_output_violations_do_not_report_success(self):
        m=MCI(SimpleNamespace(submit_local=lambda p:[dict(ok=True,payload=13)]))
        self.assertEqual('OUTPUT_INVALID',m.call(call('Cnr_Echo',dict(text='hello'),service='Mesh_Node',target='ugv-001'))['error']['code'])
    def test_network_result_before_first_sample_can_report_unknown_readiness(self):
        service=SimpleNamespace(submit_local=lambda p:[dict(type='task.reply',task=dict(task_id='network',kind='network_diagnostics',
            state='RUNNING',revision=1,config=dict(probe_node='micro-001',duration_s=30,period_ms=1000),
            result=dict(node_id='micro-001',samples=0,ok=0,failed=0,ready=None,last_ms=None,avg_ms=None,max_ms=None,error=None)))])
        result=MCI(service).call(call('Get_Task',dict(taskId='network')))
        self.assertIsNone(result['result']['task']['result']['ready'])
    def test_admission_instance_catalog_and_echo_contracts(self):
        def submit(p):
            if p['type']=='node.admission':return [dict(ok=True,trust_status='revoked',admission_revision=2,broker_acl_applied=False,broker_acl_reload_required=True)]
            if p['type']=='command':return [dict(ok=True,payload=p['payload'])]
            return [dict(nodes=[dict(service_id='uav-001/anomaly-review',node_id='uav-001',execution_mode='esp32_test',availability='busy')])]
        service=SimpleNamespace(submit_local=submit,catalog=SimpleNamespace(records=lambda:[dict(node_id='uav-001',root_id='ugv-root',registered=True,
            registration=dict(node_id='uav-001',role='uav',ap_subnet=8,enabled=True),last_observation=None,observed_at=None)]))
        m=MCI(service)
        receipt=m.call(call('Cnr_SetTrustStatus',dict(trustStatus='revoked',expectedRevision=1),service='Mesh_Admission',target='uav-001'))['result']
        self.assertFalse(receipt['brokerAclApplied'])
        self.assertTrue(receipt['brokerAclReloadRequired'])
        self.assertEqual('hello',m.call(call('Cnr_Echo',dict(text='hello'),service='Mesh_Node',target='uav-001'))['result']['text'])
        self.assertEqual('busy',m.call(call('Get_ServiceInstances',service='Mesh_Node'))['result']['instances'][0]['availability'])
        registration=m.call(call('Get_RegisteredNodes',service='Mesh_Node'))['result']['nodes'][0]
        self.assertEqual(8,registration['registration']['apSubnet'])
        self.assertIsNone(registration['lastObservation'])
    def test_actual_http_task_persistence_idempotence_and_ws(self):
        async def exercise():
            with tempfile.TemporaryDirectory() as folder:
                h=Harness(Path(folder))
                try:
                    async with TestClient(TestServer(application(h))) as client:
                        discovered=await (await client.post('/api/v1/mci/listMethod',json={})).json()
                        self.assertEqual('1.0.0',discovered['specVersion'])
                        packet=call('Cnr_CreateTask',dict(executorNodeId='ugv-001',taskId='mci-task',kind='diagnostics',config=dict(durationSeconds=3,periodMs=500)))
                        async def invoke(p):return await (await client.post('/api/v1/mci/call',json=p)).json()
                        first=await invoke(packet);self.assertEqual('CREATED',first['result']['task']['state'])
                        self.assertEqual(first,await invoke(packet))
                        changed=copy.deepcopy(packet);changed['params']['config']['durationSeconds']=4
                        self.assertEqual('BUSINESS_ERROR',(await invoke(changed))['error']['code'])
                        query=await invoke(call('Get_Task',dict(taskId='mci-task'),requestId='query'))
                        self.assertEqual('ugv-001',query['result']['task']['target'])
                        self.assertEqual(3,query['result']['task']['config']['durationSeconds'])
                        update=await invoke(call('Cnr_UpdateTask',dict(taskId='mci-task',expectedRevision=1,
                            config=dict(watchTaskId='other')),requestId='bad-update'))
                        self.assertEqual('INVALID_ARGUMENT',update['error']['code'])
                        start=await invoke(call('Cnr_StartTask',dict(taskId='mci-task',expectedRevision=1),requestId='start'))
                        self.assertEqual('QUEUED',start['result']['task']['state'])
                        self.assertEqual('UGV_RECEIVED',start['result']['stage'])
                        ws=await client.ws_connect('/api/v1/events?format=mci')
                        event=await ws.receive_json(timeout=3)
                        self.assertEqual('Ntf_TaskChanged',event['method'])
                        self.assertEqual('mci-task',event['params']['taskId'])
                        await ws.close()
                        with h.tasks.store.lock,h.tasks.store.db:
                            h.tasks.store.db.execute('INSERT INTO incidents(event_id,owner,source_task_id,node_id,area_id,point_id,created) VALUES(?,?,?,?,?,?,?)',
                                ('test-event','http-local','mci-task','micro-001','A01','P01',int(time.time())))
                        ws=await client.ws_connect('/api/v1/events?format=mci&cursor=999')
                        event=await ws.receive_json(timeout=3)
                        self.assertEqual('Et_TestIncident',event['method'])
                        self.assertEqual('test-event',event['params']['eventId'])
                        self.assertGreater(event['incidentCursor'],0)
                        await ws.close()
                        bad=await client.post('/api/v1/mci/listMethod',data='{"service":"Mesh_Task","service":"Mesh_Node"}',headers={'Content-Type':'application/json'})
                        self.assertEqual(400,bad.status)
                finally:h.close()
        asyncio.run(exercise())

if __name__=='__main__':unittest.main()
