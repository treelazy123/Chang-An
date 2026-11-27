import unittest
from car_terminal.mci import envelope,legacy_response,legacy_event

class MCIAdapterTests(unittest.TestCase):
    def packet(self,message_type,**fields):return dict(v=1,type=message_type,msg_id='request-1',deadline_unix=123,**fields)
    def test_creation_routes_executor_as_business_data_and_uses_camel_case(self):
        packet=self.packet('task.create',target='ugv-root',task_id='task-1',kind='network_diagnostics',config=dict(probe_node='micro-001',duration_s=30,period_ms=1000))
        wire=envelope(packet)
        self.assertEqual(('Mesh_Task','Cnr_CreateTask'),(wire['service'],wire['method']))
        self.assertEqual('ugv-root',wire['params']['executorNodeId'])
        self.assertNotIn('target',wire)
        self.assertEqual(30,wire['params']['config']['durationSeconds'])
        self.assertNotIn('msg_id',wire)
    def test_device_route_and_parent_policy_version(self):
        wire=envelope(self.packet('node.parent',target='micro-001',parent='uav-001',mode='fixed',expected_revision=3))
        self.assertEqual('micro-001',wire['target'])
        self.assertEqual('uav-001',wire['params']['parentNodeId'])
        self.assertEqual(3,wire['params']['expectedRevision'])
    def test_error_and_echo_result_preserve_legacy_view(self):
        p=self.packet('command',target='uav-001',op='echo',payload='hello')
        self.assertEqual('hello',legacy_response(p,dict(result=dict(text='hello')))['payload'])
        self.assertEqual('uav-001',legacy_response(p,dict(result=dict(text='hello')))['node_id'])
        self.assertIn('PERMISSION_DENIED',legacy_response(p,dict(error=dict(code='PERMISSION_DENIED',message='denied')))['error'])
    def test_task_and_node_notifications_normalize_without_modifying_wire(self):
        raw=dict(service='Mesh_Task',method='Ntf_TaskChanged',cursor=3,params=dict(taskId='task-1',stateSeq=2))
        event=legacy_event(raw)
        self.assertEqual(('task.event','task-1',3),(event['type'],event['task_id'],event['cursor']))
        self.assertNotIn('task_id',raw['params'])
        event=legacy_event(dict(method='Ntf_NodeSnapshot',params=dict(nodes=[],brokerConnected=True)))
        self.assertTrue(event['broker_connected'])
