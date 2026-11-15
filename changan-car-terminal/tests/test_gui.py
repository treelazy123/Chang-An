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
