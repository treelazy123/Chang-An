"""Per-device enrollment/build isolation without IDF invocation or real credentials."""
from pathlib import Path
import contextlib
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from provision_mqtt import provision
from node_inventory import load_inventory,clients,valid_id,write_inventory
from node_identity import enroll,check_identity,enrollment_lock
from mqtt_terminal import Registry
import lab
class IdentityEnrollment(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        with contextlib.redirect_stdout(io.StringIO()):provision(self.root)
    def hashes(self):
        return {str(p.relative_to(self.root)):hashlib.sha256(p.read_bytes()).hexdigest()
                for p in (self.root/'secrets').rglob('*') if p.is_file() and p.name in ('ca.pem','ca.key','client.pem','client.key')}
    def test_all_roles_get_independent_credentials_without_changing_existing_keys(self):
        before=self.hashes();fingerprints=set()
        for role,node in [('ugv','ugv-002'),('pc_root','pc-root-002'),('uav','uav-002'),('micro_uav','micro-002')]:
            record=enroll(self.root,role,node,'ugv-002')
            self.assertTrue(record['created']);fingerprints.add(record['certificate_sha256'])
            self.assertEqual(record['certificate_sha256'],check_identity(self.root,node))
        self.assertEqual(4,len(fingerprints));after=self.hashes()
        for name,digest in before.items():self.assertEqual(digest,after[name])
        acl=(self.root/'runtime/acl.conf').read_text()
        self.assertIn('user micro-002',acl)
        self.assertIn('topic read mesh/v1/nodes/micro-002/commands',acl)
        self.assertNotIn('topic write mesh/v1/nodes/+/commands',acl)
        self.assertNotIn('ugv-002',clients(load_inventory(self.root)))
    def test_first_provision_follows_arbitrary_inventory_instead_of_fixed_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            data={'schema':1,'nodes':[{'node_id':'gateway_017','role':'ugv','ugv_id':'gateway_017'},
                                     {'node_id':'camera_028','role':'uav','ugv_id':'gateway_017'}]}
            write_inventory(root,data)
            with contextlib.redirect_stdout(io.StringIO()):provision(root)
            check_identity(root,'gateway_017');check_identity(root,'camera_028')
            self.assertFalse((root/'secrets/uav-001').exists())
            self.assertIn('user camera_028',(root/'runtime/acl.conf').read_text())
    def test_repeat_enrollment_reuses_identical_certificate_and_key(self):
        first=enroll(self.root,'micro_uav','micro-002');before=self.hashes()
        second=enroll(self.root,'micro_uav','micro-002')
        self.assertFalse(second['created']);self.assertEqual(first['certificate_sha256'],second['certificate_sha256'])
        self.assertEqual(before,self.hashes())
    def test_role_case_and_reserved_identity_collisions_are_rejected(self):
        enroll(self.root,'micro_uav','micro-002')
        for role,node in [('uav','micro-002'),('micro_uav','MICRO-002'),('uav','controller-001')]:
            with self.assertRaises(ValueError):enroll(self.root,role,node)
        for value in ('../escape','a/b','COM1','a b','x'*33):
            with self.assertRaises(ValueError):valid_id(value)
    def test_bad_cert_key_ca_and_changed_fingerprint_are_not_silently_accepted(self):
        enroll(self.root,'micro_uav','micro-002');directory=self.root/'secrets/micro-002'
        (directory/'client.key').write_bytes((self.root/'secrets/uav-001/client.key').read_bytes())
        with self.assertRaises(ValueError):enroll(self.root,'micro_uav','micro-002')
    def test_unknown_ugv_and_concurrent_enrollment_are_rejected(self):
        with self.assertRaises(ValueError):enroll(self.root,'uav','uav-002','missing-ugv')
        with enrollment_lock(self.root):
            with self.assertRaises(ValueError):enroll(self.root,'uav','uav-002')
    def test_inventory_is_authorization_not_message_learning(self):
        enroll(self.root,'micro_uav','micro-002')
        allowed=clients(load_inventory(self.root));registry=Registry(nodes=allowed)
        self.assertIn('micro-002',registry.nodes)
        self.assertFalse(registry.receive('mesh/v1/nodes/stranger/presence',dict(v=1,type='presence',node_id='stranger',online=True)))
        data=load_inventory(self.root)
        for e in data['nodes']:
            if e['node_id']=='micro-002':e['enabled']=False
        write_inventory(self.root,data)
        self.assertNotIn('micro-002',clients(load_inventory(self.root)))
    def test_real_lab_dispatch_generates_isolated_identity_defaults_for_every_role(self):
        # Stub every IDF process; only local enrollment/default generation executes.
        for path in ('tools','firmware/configs/profiles','firmware/configs/topologies','fake-idf/tools'):(self.root/path).mkdir(parents=True,exist_ok=True)
        (self.root/'fake-idf/tools/idf.py').write_text('# not executed')
        for file in ('firmware/sdkconfig.defaults','firmware/configs/profiles/mqtt_serial.defaults','firmware/configs/topologies/chain.defaults'):
            (self.root/file).write_text('# fixture')
        for role in ('ugv','pc_root','uav','micro_uav'):
            (self.root/'firmware/configs/profiles'/(role+'.defaults')).write_text('# fixture')
        import idf_env
        for role,node in [('ugv','ugv-002'),('pc_root','pc-root-002'),('uav','uav-002'),('micro_uav','micro-002')]:
            argv=['lab.py','--role',role,'--transport','mqtt_serial','--node-id',node,'--ugv-id','ugv-002','--port','COM_FAKE','flash']
            calls=[]
            with patch.object(lab,'__file__',str(self.root/'tools/lab.py')),patch.object(sys,'argv',argv), \
                 patch.object(idf_env,'prepare_idf_environment',return_value=({'IDF_PATH':str(self.root/'fake-idf')},sys.executable)), \
                 patch.object(lab.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout='ESP-IDF v6.1')), \
                 patch.object(lab.subprocess,'call',side_effect=lambda cmd,env:(calls.append(cmd) or 0)),contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(0,lab.main())
            self.assertEqual(1,len(calls));self.assertEqual('flash',calls[0][-1])
            self.assertIn(str(self.root/'build/mqtt_serial/nodes'/node/(role+'-chain')),calls[0])
            config=(self.root/'secrets'/node/'build/mqtt_serial-chain.defaults').read_text()
            self.assertIn('CONFIG_APP_NODE_ID="'+node+'"',config)
            self.assertIn('CONFIG_APP_UGV_NODE_ID="ugv-002"',config)
            self.assertIn('CONFIG_APP_ROLE_'+role.upper()+'=y',config)
    def test_mqtt_flash_requires_explicit_board_identity_before_any_enrollment(self):
        argv=['lab.py','--role','micro_uav','--transport','mqtt_serial','--port','COM_FAKE','flash']
        with patch.object(sys,'argv',argv),patch('node_identity.enroll') as enroll_mock,contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):lab.main()
        enroll_mock.assert_not_called()
    def test_controller_reloads_any_registered_identity_without_learning_from_mqtt(self):
        from mqtt_terminal import Controller
        import threading
        from types import SimpleNamespace
        controller=Controller.__new__(Controller)
        controller.registry=Registry(nodes=['pc-root-001'])
        controller.registry.nodes['pc-root-001']['preserved']='yes'
        controller.condition=threading.Condition();controller.connected=threading.Event();controller.connected.set()
        controller.inventory_path=self.root/'config/nodes.json'
        controller.inventory_text=None;controller.inventory_error=None
        subscriptions=[];controller.client=SimpleNamespace(subscribe=lambda topics:subscriptions.extend(topics))
        enroll(self.root,'uav','inspection_017')
        controller.refresh_inventory()
        self.assertIn('inspection_017',controller.registry.nodes)
        self.assertEqual('yes',controller.registry.nodes['pc-root-001']['preserved'])
        self.assertIn(('mesh/v1/nodes/inspection_017/capabilities',1),subscriptions)
        self.assertFalse(controller.registry.ready('inspection_017'))
        data=load_inventory(self.root)
        for e in data['nodes']:
            if e['node_id']=='inspection_017':e['enabled']=False
        write_inventory(self.root,data);controller.refresh_inventory()
        self.assertNotIn('inspection_017',controller.registry.nodes)
    def test_mismatched_cached_board_identity_never_reaches_flash(self):
        for path in ('tools','firmware/configs/profiles','firmware/configs/topologies','fake-idf/tools'):(self.root/path).mkdir(parents=True,exist_ok=True)
        for file in ('firmware/sdkconfig.defaults','firmware/configs/profiles/micro_uav.defaults','firmware/configs/profiles/mqtt_serial.defaults','firmware/configs/topologies/chain.defaults','fake-idf/tools/idf.py'):
            (self.root/file).write_text('# fixture')
        cache=self.root/'build/mqtt_serial/nodes/micro-002/micro_uav-chain';cache.mkdir(parents=True)
        config=cache/'sdkconfig';config.write_text('CONFIG_APP_ROLE_MICRO_UAV=y\nCONFIG_APP_TOPOLOGY_CHAIN=y\nCONFIG_APP_ARCHITECTURE_VERSION=2\nCONFIG_MESH_LITE_MAXIMUM_LEVEL_ALLOWED=4\nCONFIG_APP_TRANSPORT_MQTT_SERIAL=y\nCONFIG_APP_UGV_NODE_ID="ugv-001"\nCONFIG_APP_NODE_ID="micro-001"\n')
        before=config.read_bytes()
        import idf_env
        argv=['lab.py','--role','micro_uav','--node-id','micro-002','--transport','mqtt_serial','--port','COM_FAKE','flash']
        with patch.object(lab,'__file__',str(self.root/'tools/lab.py')),patch.object(sys,'argv',argv), \
             patch.object(idf_env,'prepare_idf_environment',return_value=({'IDF_PATH':str(self.root/'fake-idf')},sys.executable)), \
             patch.object(lab.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout='ESP-IDF v6.1')), \
             patch.object(lab.subprocess,'call') as flash,contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):lab.main()
        flash.assert_not_called();self.assertEqual(before,config.read_bytes())
    def test_custom_id_dry_run_never_enrolls_or_writes_a_profile(self):
        before=self.hashes()
        argv=['lab.py','--transport','mqtt_serial','--role','micro_uav','--node-id','micro-099','--dry-run']
        with patch.object(sys,'argv',argv),contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(0,lab.main())
        self.assertIn('micro-099',output.getvalue());self.assertEqual(before,self.hashes())
        self.assertFalse((ROOT/'secrets/micro-099').exists())
if __name__=='__main__':unittest.main()
