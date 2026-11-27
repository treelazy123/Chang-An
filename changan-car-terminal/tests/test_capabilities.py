"""Capability test controls and full backend export; no device or Broker access."""
import json
from pathlib import Path
import queue
import tempfile
import tkinter as tk
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from car_terminal.gui import DebugWindow,run_operation


def result():
    return dict(batch_id='a'*32,summary=dict(total=2,confirmed=1,proved_within_800ms=1,
        states=dict(TIMEOUT=1,INTERRUPTED=0),avg_ms=20,p95_ms=20,max_ms=20,complete=True),
        items=[dict(node_id='micro-001',ordinal=0,cap_id='a'*16+'-00000001',agent_type='micro_uav',
                    basic_capabilities=['diagnostics'],task_status='IDLE',elapsed_ms=20,state='PASS',error=None),
               dict(node_id='micro-001',ordinal=1,cap_id=None,agent_type=None,basic_capabilities=[],task_status=None,
                    elapsed_ms=None,state='TIMEOUT',error='confirmation_missing')])


class Operations(unittest.TestCase):
    def test_validate_before_start_and_export_backend_complete_evidence(self):
        calls=[]
        client=SimpleNamespace(capability_test=lambda *args:(calls.append(args) or '{"raw":"后台原始公告"}\n'))
        values=dict(cap_nodes='micro-001,micro-001',cap_count='30',cap_period='1000',cap_batch='a'*32)
        with self.assertRaises(ValueError):run_operation(client,'cap_start',values)
        self.assertFalse(calls)
        values['cap_nodes']='ugv-001, micro-001'
        run_operation(client,'cap_start',values)
        self.assertEqual(['ugv-001','micro-001'],calls[-1][1]['nodes'])
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'evidence.jsonl';values['cap_export_path']=str(path)
            run_operation(client,'cap_export',values)
            self.assertEqual({'raw':'后台原始公告'},json.loads(path.read_text(encoding='utf-8')))
            self.assertEqual('export',calls[-1][0])


class Panel(unittest.TestCase):
    def setUp(self):
        self.root=tk.Tk();self.root.withdraw();self.jobs=[]
        self.worker=SimpleNamespace(results=queue.Queue(),submit=lambda *a:self.jobs.append(a))
        self.window=DebugWindow(self.root,worker=self.worker)
        self.window.connected=True;self.window._states()
        self.root.update_idletasks()

    def tearDown(self):self.window.close()

    def test_table_does_not_turn_timeout_into_zero_and_names_metric_upper_bound(self):
        self.window.cap_watch.set(True);self.window._apply('cap_get',result())
        self.assertFalse(self.window.cap_watch.get())
        rows=[self.window.cap_table.item(i,'values') for i in self.window.cap_table.get_children()]
        self.assertEqual('20.000',rows[0][6]);self.assertEqual('—',rows[1][6])
        self.assertIn('超时 1',self.window.cap_summary.get())

    def test_start_retains_batch_id_for_timeout_query_and_export_is_async(self):
        self.window.values['cap_nodes'].set('micro-001')
        self.window._start_capability_test()
        action,values=self.jobs[-1]
        self.assertEqual('cap_start',action);self.assertEqual(32,len(values['cap_batch']))
        self.window.busy=False
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'batch.csv'
            with patch('car_terminal.gui.filedialog.asksaveasfilename',return_value=str(path)):
                self.window._export_capability_test()
            self.assertEqual('cap_export',self.jobs[-1][0])
            self.assertEqual(str(path),self.jobs[-1][1]['cap_export_path'])

    def test_new_start_does_not_replace_known_running_batch(self):
        body=result();body['summary']['complete']=False
        self.window._apply('cap_get',body)
        self.window._start_capability_test()
        self.assertEqual('a'*32,self.window.values['cap_batch'].get())
        self.assertEqual([],self.jobs)
