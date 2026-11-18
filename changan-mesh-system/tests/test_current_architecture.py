"""Keep the single current topology and independent HTTP terminal as source contracts."""
from pathlib import Path
import json
import subprocess
import sys
import unittest
from changan_ugv.config import ServiceConfig
from changan_ugv.nodes.inventory import ROLES,defaults,load_inventory,validate,clients

ROOT=Path(__file__).resolve().parents[1]

class CurrentArchitecture(unittest.TestCase):
    def test_default_and_explicit_configs_use_one_inventory_and_root(self):
        data=load_inventory(ROOT)
        self.assertEqual(2,data['schema'])
        self.assertEqual({'ugv_root','ugv','uav','micro_uav'},set(ROLES))
        self.assertEqual('ugv-root',next(e['node_id'] for e in data['nodes'] if e['role']=='ugv_root'))
        self.assertNotIn('ugv-root',clients(data))
        for name in ('ugv-root.dev.toml','ugv.example.toml'):
            cfg=ServiceConfig.from_file(ROOT/'config'/name)
            self.assertEqual('ugv-root',cfg.ugv_id)
            self.assertEqual(ROOT/'config/nodes.json',cfg.paths.inventory_file)
            self.assertEqual(ROOT/'runtime/ugv-root/tasks.sqlite3',cfg.paths.task_database)
        with self.assertRaises(ValueError):validate(dict(defaults(),schema=1))

    def test_node_examples_are_json_and_fit_physical_command_budget(self):
        from changan_ugv.protocol.messages import encode
        for packet in json.loads((ROOT/'protocols/v1/examples.json').read_text())['examples']:
            wire=encode(packet)
            self.assertEqual(packet,json.loads(wire))
            self.assertLessEqual(len(wire),512)

    def test_terminal_command_line_has_no_device_transport_options(self):
        car=ROOT.parent/'changan-car-terminal'
        if not car.is_dir():self.skipTest('Independent terminal not available')
        result=subprocess.run([sys.executable,'-m','car_terminal','--help'],cwd=car,capture_output=True,text=True)
        self.assertEqual(0,result.returncode,result.stderr)
        self.assertIn('--base-url',result.stdout)
        for option in ('--port','--cert-dir','--broker-port','--node-id'):
            self.assertNotIn(option,result.stdout)
