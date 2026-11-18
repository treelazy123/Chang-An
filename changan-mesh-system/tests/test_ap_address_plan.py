"""Inventory-wide AP reservations; no SDK, serial ports or live services."""
import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from node_inventory import defaults,validate,assign_ap_subnets,next_ap_subnet,load_inventory,write_inventory
import lab


class AddressPlan(unittest.TestCase):
    def test_two_uavs_get_distinct_persistent_subnets_without_renumbering_existing_nodes(self):
        data=defaults();before=copy.deepcopy(data)
        data['nodes'].append(dict(node_id='uav-002',role='uav',root_id='ugv-root'))
        assign_ap_subnets(data)
        first={e['node_id']:e['ap_subnet'] for e in data['nodes']}
        self.assertEqual(8,first['uav-001']);self.assertEqual(10,first['uav-002'])
        self.assertEqual(before['nodes'],data['nodes'][:-1])
        data['nodes'].reverse()
        data['nodes'].append(dict(node_id='uav-003',role='uav',root_id='ugv-root'))
        assign_ap_subnets(data)
        for entry in data['nodes']:
            if entry['node_id'] in first:self.assertEqual(first[entry['node_id']],entry['ap_subnet'])
        with tempfile.TemporaryDirectory() as directory:
            write_inventory(directory,data)
            self.assertEqual(data,load_inventory(directory))

    def test_disabled_and_revoked_devices_keep_their_reservations(self):
        data=defaults()
        data['nodes'][2].update(enabled=False)
        data['nodes'][3].update(trust_status='revoked')
        self.assertEqual(10,next_ap_subnet(data))
        data['nodes'].append(dict(node_id='new-uav',role='uav',root_id='ugv-root'))
        assign_ap_subnets(data)
        self.assertEqual([5,6,8,None,10],[e['ap_subnet'] for e in data['nodes']])

    def test_invalid_or_duplicate_subnets_are_rejected_even_for_disabled_devices(self):
        for bad in (True,False,0,3,255,'8',8.0,None):
            with self.subTest(value=bad):
                data=defaults();data['nodes'][2]['ap_subnet']=bad
                with self.assertRaisesRegex(ValueError,'ap_subnet'):validate(data)
        data=defaults()
        data['nodes'].append(dict(node_id='uav-002',role='uav',root_id='ugv-root',ap_subnet=8,enabled=False))
        with self.assertRaisesRegex(ValueError,'Duplicate AP subnet.*uav-001.*uav-002'):validate(data)

    def test_pool_exhaustion_does_not_partially_assign_or_recycle_leases(self):
        data={'schema':2,'nodes':[
            dict(node_id='ugv-root' if n==4 else f'node-{n}',
                 role='ugv_root' if n==4 else 'uav',root_id='ugv-root',ap_subnet=n)
            for n in range(4,255)]}
        with self.assertRaisesRegex(ValueError,'exhausted'):next_ap_subnet(data)
        data['nodes'].append(dict(node_id='overflow',role='uav',root_id='ugv-root'))
        before=copy.deepcopy(data)
        with self.assertRaisesRegex(ValueError,'exhausted'):assign_ap_subnets(data)
        self.assertEqual(before,data)

    def test_legacy_inventory_read_does_not_allocate_ephemeral_addresses(self):
        data=defaults()
        for entry in data['nodes']:entry.pop('ap_subnet')
        with tempfile.TemporaryDirectory() as directory:
            write_inventory(directory,data);path=Path(directory)/'config/nodes.json'
            before=path.read_bytes()
            self.assertEqual(data,load_inventory(directory));self.assertEqual(before,path.read_bytes())
        assign_ap_subnets(data)
        self.assertEqual(3,len({e['ap_subnet'] for e in data['nodes'] if e['ap_subnet'] is not None}))
        self.assertIsNone(data['nodes'][3]['ap_subnet'])

    def test_lab_rejects_missing_or_duplicate_reservations_before_sdk_and_credentials(self):
        import idf_env
        for duplicate in (False,True):
            data=defaults()
            if duplicate:data['nodes'][2]['ap_subnet']=6
            else:data['nodes'][2].pop('ap_subnet')
            with tempfile.TemporaryDirectory() as directory:
                path=Path(directory)/'inventory.json';path.write_text(json.dumps(data))
                argv=['lab.py','--role','uav','--node-id','uav-001','--inventory',str(path),'build']
                error=io.StringIO()
                with patch.object(sys,'argv',argv),patch.object(idf_env,'prepare_idf_environment') as sdk, \
                     patch('identity_env.ensure_identity') as identity,contextlib.redirect_stderr(error):
                    with self.assertRaises(SystemExit):lab.main()
                sdk.assert_not_called();identity.assert_not_called()
                self.assertIn('Duplicate AP subnet' if duplicate else 'No reserved AP subnet',error.getvalue())

    def test_real_two_uav_dry_runs_use_distinct_reserved_addresses_without_writes(self):
        path=ROOT/'config/nodes.json';before=path.read_bytes()
        for node,subnet in [('uav-001',8),('uav-002',9)]:
            with patch.object(sys,'argv',['lab.py','--role','uav','--node-id',node,'--dry-run']), \
                 contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(0,lab.main())
            self.assertIn(f'Reserved AP: 192.168.{subnet}.1/24',output.getvalue())
        self.assertEqual(before,path.read_bytes())

    def test_micro_nodes_need_no_ap_lease_or_remaining_pool_capacity(self):
        data=defaults()
        for n in range(10,255):
            data['nodes'].append(dict(node_id=f'uav-{n}',role='uav',root_id='ugv-root',ap_subnet=n))
        data['nodes'].append(dict(node_id='micro-002',role='micro_uav',root_id='ugv-root'))
        assign_ap_subnets(data)
        self.assertIsNone(data['nodes'][-1]['ap_subnet'])
        data['nodes'][-1]['ap_subnet']=9
        with self.assertRaisesRegex(ValueError,'STA-only'):validate(data)
        for node in ('micro-001','micro-002'):
            with patch.object(sys,'argv',['lab.py','--role','micro_uav','--node-id',node,'--dry-run']), \
                 contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(0,lab.main())
            self.assertIn('disabled (STA only)',output.getvalue())
        self.assertEqual('0',lab.expected_config('micro_uav','micro-001','ugv-root')['CONFIG_APP_SOFTAP_SUBNET'])


if __name__=='__main__':unittest.main()
