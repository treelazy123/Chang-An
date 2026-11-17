"""Desktop regression tests with fake transports; no COM ports or brokers."""
import json
from pathlib import Path
import sys
import tempfile
import threading
import tkinter as tk
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from car_terminal.gui import DebugWindow, SessionWorker, run_operation


class FakeTransport:
    def __init__(self):
        self.seen = []
        self.closed = False

    def request(self, packet):
        self.seen.append(packet)
        kind = packet['type']
        if kind == 'list':
            return dict(type='nodes', nodes=[dict(node_id='micro-002', ready=True,
                        status=dict(role='micro_uav'), operations=['ping', 'status', 'echo'])])
        if kind == 'command':
            return dict(type='ack', node_id=packet['target'], ok=True)
        if kind in ('task.list', 'task.events'):
            cursor = packet['cursor']
            task = dict(task_id='test-task', target='micro-002', state='CREATED',
                        revision=3, progress=0, state_seq=cursor + 1)
            return dict(type='task.reply', ok=True, items=[task], cursor=cursor + 1, more=cursor < 1)
        return dict(type='task.reply', ok=True, task=dict(task_id='test-task',
                    target='micro-002', state='CREATED', revision=3, state_seq=1, progress=0))

    def close(self):
        self.closed = True


class OperationTests(unittest.TestCase):
    def test_workflow_creation_and_update_use_selected_executor_and_test_config(self):
        client=FakeTransport()
        values=dict(task_kind='区域巡检（ESP32测试）',executor='tiny-017',area_id='A01',points='P01,P02',point_seconds='2',anomaly_point='1')
        run_operation(client,'create',values)
        self.assertEqual(('tiny-017','patrol'),(client.seen[-1]['target'],client.seen[-1]['kind']))
        values.update(task_id='task',revision=3,points='P03')
        run_operation(client,'update',values)
        self.assertEqual('task.update',client.seen[-1]['type'])
        self.assertEqual(['P03'],client.seen[-1]['config']['point_ids'])
        values.update(task_kind='异常复核（ESP32测试）',executor='scout-017',event_id='event-1',test_verdict='cleared',duration='3')
        run_operation(client,'create',values)
        self.assertEqual(('anomaly_review','esp32_test'),(client.seen[-1]['kind'],client.seen[-1]['config']['execution_mode']))

    def test_delete_requires_known_terminal_state_and_displayed_revision(self):
        client=FakeTransport()
        with self.assertRaisesRegex(ValueError,'已结束'):
            run_operation(client,'delete',dict(task_id='history',revision=3,task_state='RUNNING'))
        self.assertEqual([],client.seen)
        run_operation(client,'delete',dict(task_id='history',revision=3,task_state='CANCELLED'))
        self.assertEqual(('task.control','delete',3),(client.seen[0]['type'],client.seen[0]['op'],client.seen[0]['expected_revision']))

    def test_service_tasks_separate_executor_from_subject(self):
        client = FakeTransport()
        values=dict(target='micro-002',executor='ugv-001',task_kind='网络诊断',duration='30',period='500')
        run_operation(client,'create',values)
        self.assertEqual('ugv-001',client.seen[-1]['target'])
        self.assertEqual('micro-002',client.seen[-1]['config']['probe_node'])
        values.update(task_kind='任务运行监视',watch_task_id='watched',stale_after='3')
        run_operation(client,'create',values)
        self.assertEqual('task_monitor',client.seen[-1]['kind'])
        self.assertEqual('watched',client.seen[-1]['config']['watch_task_id'])
        # The node debug buttons still address the selected remote node.
        run_operation(client,'ping',values)
        self.assertEqual('micro-002',client.seen[-1]['target'])

    def test_task_list_collects_all_pages(self):
        client = FakeTransport()
        result = run_operation(client, 'tasks', {})
        self.assertEqual([0, 1], [packet['cursor'] for packet in client.seen])
        self.assertEqual(2, len(result['items']))
        self.assertFalse(result['more'])

    def test_event_batches_preserve_resume_cursor(self):
        client = FakeTransport()
        result = run_operation(client, 'events', {'cursor': 7})
        self.assertEqual(7, client.seen[0]['cursor'])
        self.assertEqual(8, result['cursor'])

    def test_nonadvancing_pagination_is_rejected(self):
        class Broken(FakeTransport):
            def request(self, packet):
                return dict(type='task.reply', ok=True, items=[], cursor=0, more=True)
        with self.assertRaisesRegex(ValueError, '游标'):
            run_operation(Broken(), 'tasks', {})

    def test_control_uses_displayed_revision_without_overwriting_conflicts(self):
        class Conflict(FakeTransport):
            def request(self, packet):
                self.seen.append(packet)
                return dict(type='error', error='revision_conflict')
        client = Conflict()
        with self.assertRaisesRegex(ValueError, 'revision_conflict'):
            run_operation(client, 'start', dict(task_id='test-task', revision=3))
        self.assertEqual(1, len(client.seen))
        self.assertEqual(3, client.seen[0]['expected_revision'])

    def test_unknown_task_revision_requires_query(self):
        client = FakeTransport()
        with self.assertRaisesRegex(ValueError, '查询'):
            run_operation(client, 'pause', dict(task_id='test-task'))
        self.assertEqual([], client.seen)

    def test_create_timeout_keeps_task_id_and_never_retries(self):
        class Broken(FakeTransport):
            def request(self, packet):
                self.seen.append(packet)
                raise TimeoutError('no reply')
        client = Broken()
        with self.assertRaisesRegex(OSError, 'task get') as captured:
            run_operation(client, 'create', dict(target='micro-002', duration='30', period='1000'))
        self.assertEqual(1, len(client.seen))
        self.assertIn(client.seen[0]['task_id'], str(captured.exception))

    def test_invalid_diagnostics_config_does_not_send(self):
        client = FakeTransport()
        with self.assertRaises(ValueError):
            run_operation(client, 'create', dict(target='micro-002', duration='0', period='1'))
        self.assertEqual([], client.seen)

    def test_worker_keeps_blocking_io_off_caller_and_closes_in_order(self):
        entered, release = threading.Event(), threading.Event()
        class Blocking(FakeTransport):
            def request(self, packet):
                entered.set()
                release.wait(2)
                self.assert_open = not self.closed
                return super().request(packet)
        client = Blocking()
        worker = SessionWorker(factory=lambda _: client)
        try:
            worker.submit('connect')
            self.assertTrue(worker.results.get(timeout=2)[1])
            worker.submit('nodes')
            self.assertTrue(entered.wait(2))
            worker.submit('disconnect')
            self.assertFalse(client.closed)
            release.set()
            self.assertTrue(worker.results.get(timeout=2)[1])
            self.assertTrue(worker.results.get(timeout=2)[1])
            self.assertTrue(client.assert_open)
            self.assertTrue(client.closed)
        finally:
            release.set()
            worker.submit('stop')
            worker.thread.join(3)
        self.assertFalse(worker.thread.is_alive())


class WindowTests(unittest.TestCase):
    def test_role_services_and_incident_selection_do_not_assume_fixed_node_ids(self):
        rows=[dict(service_id=node+'/'+suffix,node_id=node,agent_type=role,service_type=kind,
                   execution_mode='esp32_test',availability='available',task_status='IDLE')
              for node,suffix,kind,role in [('tiny-017','patrol','patrol','micro_uav'),('scout-017','anomaly-review','anomaly_review','uav')]]
        self.window._apply('services',rows)
        self.window.services.selection_set(self.window.services.get_children()[0]);self.window._select_service()
        self.assertEqual(('tiny-017','区域巡检（ESP32测试）'),(self.window.values['executor'].get(),self.window.values['task_kind'].get()))
        self.window._apply('incidents',dict(items=[dict(event_id='test-event',source_task_id='patrol-task',node_id='tiny-017',area_id='A01',point_id='P02')]))
        self.window.incidents.selection_set(self.window.incidents.get_children()[0]);self.window._select_incident()
        self.assertEqual(('test-event','scout-017','异常复核（ESP32测试）'),(self.window.values['event_id'].get(),self.window.values['executor'].get(),self.window.values['task_kind'].get()))
        self.window._apply('get',dict(task=dict(task_id='loaded',target='tiny-017',kind='patrol',revision=2,config=dict(area_id='A02',point_ids=['P08'],point_duration_s=2,anomaly_point=1))))
        self.assertEqual('P08',self.window.values['points'].get())

    def test_workflow_forms_fit_minimum_window(self):
        self.root.deiconify();self.root.geometry('980x720')
        page=self.window.task_page;page.master.select(page)
        for kind in ('区域巡检（ESP32测试）','异常复核（ESP32测试）','网络诊断'):
            self.window.values['task_kind'].set(kind);self.root.update()
            for form in (self.window.patrol_form,self.window.review_form):
                if form.winfo_ismapped():
                    for widget in form.winfo_children():
                        self.assertLessEqual(widget.winfo_x()+widget.winfo_width(),form.winfo_width())
            self.assertGreater(self.window.tasks.winfo_width(),500)

    def test_deleted_history_is_removed_and_late_events_cannot_restore_it(self):
        self.window._upsert_task(dict(task_id='history',state='CANCELLED',revision=1,state_seq=2))
        self.window.values['task_id'].set('history')
        self.window._apply('delete',dict(deleted=True,task_id='history',state_seq=3))
        self.assertNotIn('history',self.window.task_rows)
        self.assertFalse(self.window.tasks.exists('history'))
        self.assertEqual('',self.window.values['task_id'].get())
        self.window._upsert_task(dict(task_id='history',state='CANCELLED',state_seq=2))
        self.assertFalse(self.window.tasks.exists('history'))
        self.window._upsert_task(dict(task_id='other',state='SUCCEEDED',state_seq=2))
        self.window._apply('events',dict(cursor=10,items=[dict(task_id='other',state='DELETED',state_seq=3)]))
        self.assertFalse(self.window.tasks.exists('other'))
        self.assertEqual(10,self.window.cursor)

    def test_service_task_controls_fit_minimum_window(self):
        self.root.deiconify()
        self.root.geometry('980x720')
        page=self.window.task_page
        page.master.select(page)
        self.root.update()
        create=self.window.task_common
        for widget in create.winfo_children():
            self.assertLessEqual(widget.winfo_x()+widget.winfo_width(),create.winfo_width())
        self.assertGreater(self.window.tasks.winfo_width(),500)

    def test_service_selection_and_live_results(self):
        self.window._apply('services',[dict(service_id='ugv-001/task_monitor',agent_type='ugv',
            service_type='task_monitor',availability='available',task_status='IDLE')])
        self.window.services.selection_set(self.window.services.get_children()[0])
        self.window._select_service()
        self.assertEqual('任务运行监视',self.window.values['task_kind'].get())
        self.window.values['task_id'].set('monitor')
        self.window._upsert_task(dict(task_id='monitor',kind='task_monitor',state_seq=1,
            result=dict(task_id='remote',state='RUNNING',progress=35,age_s=11,health='feedback_stale')))
        self.assertIn('反馈超时',self.window.metrics.get())
        self.window._upsert_task(dict(task_id='monitor',state_seq=2,
            result=dict(task_id='remote',state='FAILED',health='finished',error='node_error')))
        self.assertIn('node_error',self.window.metrics.get())

    def setUp(self):
        self.client = FakeTransport()
        self.opens = []
        self.worker = SessionWorker(factory=self._factory)
        self.root = tk.Tk()
        self.root.withdraw()
        self.window = DebugWindow(self.root, worker=self.worker)
        self.root.update_idletasks()

    def _factory(self, settings):
        self.opens.append(settings)
        return self.client

    def tearDown(self):
        self.window.close()
        self.worker.thread.join(3)

    def test_open_window_does_not_connect_or_watch(self):
        self.root.update()
        self.assertEqual([], self.opens)
        self.assertFalse(self.window.connected)
        self.assertFalse(self.window.watch.get())
        self.assertEqual('disabled', str(self.window.operation_buttons[0]['state']))

    def test_node_selection_and_task_results_are_visible(self):
        self.window._apply('nodes', run_operation(self.client, 'nodes', {}))
        self.assertEqual('micro-002', self.window.values['target'].get())
        self.assertEqual(1, len(self.window.nodes.get_children()))
        self.window._apply('get', run_operation(self.client, 'get', dict(task_id='test-task')))
        self.assertEqual('test-task', self.window.values['task_id'].get())
        self.assertEqual('版本：3', self.window.revision.get())
        self.window._upsert_task(dict(task_id='test-task', state='RUNNING', state_seq=2, progress=35))
        self.window._upsert_task(dict(task_id='test-task', state='CREATED', state_seq=1, progress=0))
        self.assertEqual('RUNNING', self.window.task_rows['test-task']['state'])
        self.assertEqual('micro-002', self.window.task_rows['test-task']['target'])

    def test_results_export_contains_success_error_timing_and_unicode(self):
        self.window.record('status', True, dict(node='micro-002', result='正常'), .123)
        self.window.record('pause', False, 'revision_conflict', .01)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'debug.jsonl'
            with patch('car_terminal.gui.filedialog.asksaveasfilename', return_value=str(path)):
                self.window.export()
            rows = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]
        self.assertEqual([True, False], [row['ok'] for row in rows])
        self.assertEqual(123, rows[0]['elapsed_ms'])
        self.assertEqual('正常', rows[0]['result']['result'])
        self.assertIn('revision_conflict', self.window.output.get('1.0', 'end'))
        self.window.clear()
        self.assertEqual([], list(self.window.records))

    def test_malformed_response_is_logged_and_ui_remains_available(self):
        self.window.connected = True
        self.window.busy = True
        self.worker.results.put(('nodes', True, [dict(unexpected=True)], .02))
        self.window._drain()
        self.assertFalse(self.window.busy)
        self.assertFalse(self.window.records[-1]['ok'])
        self.assertIn('响应格式错误', self.window.records[-1]['result'])


if __name__ == '__main__':
    unittest.main()
