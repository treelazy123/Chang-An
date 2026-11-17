import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from car_terminal.tasks import TaskClient, task_line
from car_terminal.client import request_line
from car_terminal.protocol import Decoder, encode
from car_terminal.serial_link import RootLink
from test_terminal import FakeSerial

class FakeTransport:
    def __init__(self):self.seen=[]
    def request(self,p):
        self.seen.append(p)
        return dict(v=1,type='task.reply',msg_id=p['msg_id'],ok=True,task=dict(task_id=p.get('task_id'),revision=3),items=[],cursor=0,more=False)

class TaskAPITests(unittest.TestCase):
    def test_workflow_cli_and_incident_discovery_are_explicit_test_mode(self):
        transport=FakeTransport()
        task_line(transport,'task patrol-test tiny-017 A01 P01,P02 2 1')
        packet=transport.seen[-1]
        self.assertEqual(('patrol','tiny-017','esp32_test'),(packet['kind'],packet['target'],packet['config']['execution_mode']))
        self.assertNotIn('period_ms',packet['config'])
        task_line(transport,'task review-test scout-017 event-1 cleared 3')
        self.assertEqual('cleared',transport.seen[-1]['config']['test_verdict'])
        task_line(transport,'task incidents')
        self.assertEqual(('task.events','incidents'),(transport.seen[-1]['type'],transport.seen[-1]['scope']))

    def test_delete_cli_reads_revision_or_uses_explicit_revision(self):
        transport=FakeTransport()
        task_line(transport,'task delete history')
        self.assertEqual(['task.get','task.control'],[p['type'] for p in transport.seen])
        self.assertEqual(('delete',3),(transport.seen[-1]['op'],transport.seen[-1]['expected_revision']))
        task_line(transport,'task delete other 4')
        self.assertEqual(3,len(transport.seen))
        self.assertEqual(4,transport.seen[-1]['expected_revision'])

    def test_delete_timeout_never_retries(self):
        class Broken:
            count=0
            def request(self,p):self.count+=1;raise TimeoutError('no reply')
        transport=Broken()
        with self.assertRaises(TimeoutError):TaskClient(transport).delete('history',1)
        self.assertEqual(1,transport.count)

    def test_new_service_cli_and_request_sizes(self):
        transport=FakeTransport()
        task_line(transport,'task network ugv-001 micro-001 20 500')
        self.assertEqual('network_diagnostics',transport.seen[-1]['kind'])
        task_line(transport,'task monitor ugv-001 watched 20 500 3')
        self.assertEqual(3,transport.seen[-1]['config']['stale_after_s'])
        for packet in transport.seen:
            self.assertLessEqual(len(json.dumps(dict(packet,node_id='x'*32),separators=(',',':')).encode()),512)

    def test_discovery_uses_existing_list_transport_and_rejects_legacy_reply(self):
        class Services(FakeTransport):
            def request(self,p):
                self.seen.append(p)
                return dict(type='nodes',nodes=[dict(service_id='ugv-001/network_diagnostics')])
        transport=Services()
        self.assertEqual('ugv-001/network_diagnostics',request_line(transport,'services')[0]['service_id'])
        self.assertEqual(('list','services'),(transport.seen[0]['type'],transport.seen[0]['scope']))
        class Old(Services):
            def request(self,p):return dict(type='nodes',nodes=[dict(node_id='micro-001')])
        with self.assertRaisesRegex(ValueError,'upgrade'):
            TaskClient(Old()).services()

    def test_create_keeps_task_identity_and_fits_gateway_limit(self):
        transport=FakeTransport();api=TaskClient(transport)
        api.create('micro-002',30,500,task_id='stable-task')
        p=transport.seen[0]
        self.assertEqual('stable-task',p['task_id']);self.assertEqual('diagnostics',p['kind'])
        self.assertLessEqual(len(json.dumps(dict(p,node_id='n'*32),separators=(',',':')).encode()),512)
        self.assertIn('deadline_unix',p)

    def test_control_reads_revision_then_sends_one_mutation(self):
        transport=FakeTransport();TaskClient(transport).control('task','pause')
        self.assertEqual(['task.get','task.control'],[p['type'] for p in transport.seen])
        self.assertEqual(3,transport.seen[-1]['expected_revision'])

    def test_cli_basic_commands_and_no_scene_commands(self):
        transport=FakeTransport()
        for line in ['task create micro-002 30 200','task list','task get t','task start t 1',
                     'task pause t','task resume t 1','task cancel t 1','task update t 1 60 500','task events 2 t']:
            self.assertTrue(request_line(transport,line)['ok'])
        for line in ['task survey area','task patrol area','task preview t']:
            with self.assertRaises(ValueError):task_line(transport,line)

    def test_timeout_does_not_resubmit_and_reports_queryable_task_id(self):
        class Broken:
            count=0
            def request(self,p):self.count+=1;raise TimeoutError('no reply')
        transport=Broken()
        with self.assertRaisesRegex(OSError,'task get stable'):
            TaskClient(transport).create('micro-001',task_id='stable')
        self.assertEqual(1,transport.count)

    def test_errors_are_not_reported_as_task_success(self):
        class Rejected:
            def request(self,p):return dict(type='error',error='revision_conflict')
        with self.assertRaisesRegex(ValueError,'revision_conflict'):TaskClient(Rejected()).get('task')

    def test_task_reply_and_live_event_are_separate_on_fragmented_serial(self):
        class Serial(FakeSerial):
            def write(self,data):
                for p in self.decoder.feed(data):
                    for message in [dict(v=1,type='task.event',task_id='t',state='RUNNING',cursor=1),
                                    dict(v=1,type='task.reply',msg_id=p['msg_id'],ok=True,task=dict(task_id='t'))]:
                        wire=encode(message)
                        for i in range(0,len(wire),5):self.input.put(wire[i:i+5])
                return len(data)
        received=[];link=RootLink(Serial(),on_message=received.append).start()
        try:
            response=link.request(dict(v=1,type='task.get',msg_id='abc',task_id='t'),timeout=2)
            self.assertEqual('task.reply',response['type']);self.assertTrue(any(m['type']=='task.event' for m in received))
        finally:link.close()

if __name__=='__main__':unittest.main()
