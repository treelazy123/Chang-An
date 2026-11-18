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
from changan_ugv.nodes.controller import Registry
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
        for role,node in [('ugv','ugv-002'),('uav','uav-002'),('micro_uav','micro-002')]:
            record=enroll(self.root,role,node,'ugv-root')
            self.assertTrue(record['created']);fingerprints.add(record['certificate_sha256'])
            self.assertEqual(record['certificate_sha256'],check_identity(self.root,node))
        entries=load_inventory(self.root)['nodes']
        aps=[e for e in entries if e['role']!='micro_uav']
        self.assertEqual(len(aps),len({e['ap_subnet'] for e in aps}))
        self.assertTrue(all(e['ap_subnet'] is None for e in entries if e['role']=='micro_uav'))
        self.assertEqual(3,len(fingerprints));after=self.hashes()
        for name,digest in before.items():self.assertEqual(digest,after[name])
        acl=(self.root/'runtime/ugv-root/acl.conf').read_text()
        self.assertIn('user micro-002',acl)
        self.assertIn('topic read mesh/v1/nodes/micro-002/commands',acl)
        self.assertNotIn('topic write mesh/v1/nodes/+/commands',acl)
        self.assertIn('ugv-002',clients(load_inventory(self.root)))
    def test_first_provision_follows_arbitrary_inventory_instead_of_fixed_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            data={'schema':2,'nodes':[{'node_id':'gateway_017','role':'ugv_root','root_id':'gateway_017'},
                                     {'node_id':'camera_028','role':'uav','root_id':'gateway_017'}]}
            write_inventory(root,data)
            with contextlib.redirect_stdout(io.StringIO()):provision(root)
            self.assertFalse((root/'secrets/gateway_017').exists());check_identity(root,'camera_028')
            self.assertFalse((root/'secrets/uav-001').exists())
            self.assertIn('user camera_028',(root/'runtime/ugv-root/acl.conf').read_text())
    def test_repeat_enrollment_reuses_identical_certificate_and_key(self):
        first=enroll(self.root,'micro_uav','micro-002');before=self.hashes()
        second=enroll(self.root,'micro_uav','micro-002')
        self.assertFalse(second['created']);self.assertEqual(first['certificate_sha256'],second['certificate_sha256'])
        self.assertEqual(before,self.hashes())
        self.assertEqual(first['ap_subnet'],second['ap_subnet'])
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
        for role in ('ugv_root','ugv','uav','micro_uav'):
            (self.root/'firmware/configs/profiles'/(role+'.defaults')).write_text('# fixture')
        import idf_env
        for role,node in [('ugv','ugv-002'),('uav','uav-002'),('micro_uav','micro-002')]:
            argv=['lab.py','--role',role,'--transport','mqtt_serial','--node-id',node,'--ugv-id','ugv-root','--port','COM_FAKE','flash']
            enroll(self.root,role,node,'ugv-root')
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
            self.assertIn('CONFIG_APP_UGV_NODE_ID="ugv-root"',config)
            self.assertIn('CONFIG_APP_ROLE_'+role.upper()+'=y',config)
            entry=next(e for e in load_inventory(self.root)['nodes'] if e['node_id']==node)
            self.assertIn('CONFIG_APP_SOFTAP_SUBNET='+str(entry['ap_subnet'] or 0),config)
    def test_mqtt_flash_requires_explicit_board_identity_before_any_enrollment(self):
        argv=['lab.py','--role','micro_uav','--transport','mqtt_serial','--port','COM_FAKE','flash']
        with patch.object(sys,'argv',argv),patch('node_identity.enroll') as enroll_mock,contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):lab.main()
        enroll_mock.assert_not_called()
    def test_old_architecture_requires_reset_then_reconfigures_before_requested_action(self):
        # Simulate SDK processes; exercise the real CLI/defaults/credential checks.
        for path in ('tools','firmware/configs/profiles','firmware/configs/topologies','fake-idf/tools'):
            (self.root/path).mkdir(parents=True,exist_ok=True)
        for file in ('firmware/sdkconfig.defaults','firmware/configs/profiles/ugv.defaults',
                     'firmware/configs/profiles/mqtt_serial.defaults','firmware/configs/topologies/chain.defaults',
                     'fake-idf/tools/idf.py'):
            (self.root/file).write_text('# fixture')
        cache=self.root/'build/mqtt_serial/nodes/ugv-001/ugv-chain';cache.mkdir(parents=True)
        config=cache/'sdkconfig'
        old='CONFIG_APP_ROLE_UGV=y\nCONFIG_APP_NODE_ID="ugv-001"\nCONFIG_APP_ARCHITECTURE_VERSION=2\nCONFIG_APP_UGV_NODE_ID="ugv-001"\n'
        config.write_text(old)
        old_bytes=config.read_bytes();identities=self.hashes()
        import idf_env
        argv=['lab.py','--role','ugv','--node-id','ugv-001','--port','COM_FAKE','flash']
        output=io.StringIO()
        with patch.object(lab,'__file__',str(self.root/'tools/lab.py')),patch.object(sys,'argv',argv), \
             patch.object(idf_env,'prepare_idf_environment') as environment,contextlib.redirect_stderr(output):
            with self.assertRaises(SystemExit):lab.main()
        environment.assert_not_called()
        self.assertIn('CONFIG_APP_ARCHITECTURE_VERSION: cached=2, expected=3',output.getvalue())
        self.assertIn('--reset-config',output.getvalue());self.assertEqual(old_bytes,config.read_bytes())
        with patch.object(lab,'__file__',str(self.root/'tools/lab.py')), \
             patch.object(sys,'argv',argv+['--reset-config','--dry-run']), \
             patch.object(idf_env,'prepare_idf_environment') as environment,contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(0,lab.main())
        environment.assert_not_called();self.assertEqual(old_bytes,config.read_bytes())
        self.assertEqual([],list(cache.glob('sdkconfig.before-reset-*')))
        for action in ('build','flash','reconfigure','menuconfig'):
            with self.subTest(action=action):
                config.write_bytes(old_bytes);calls=[]
                def runner(cmd,env):
                    calls.append(cmd[-1])
                    if cmd[-1] in ('reconfigure','menuconfig'):
                        config.write_text(''.join(k+'='+v+'\n' for k,v in lab.expected_config('ugv','ugv-001','ugv-root',6).items()))
                    return 0
                with patch.object(lab,'__file__',str(self.root/'tools/lab.py')), \
                     patch.object(sys,'argv',argv[:-1]+['--reset-config',action]), \
                     patch.object(idf_env,'prepare_idf_environment',return_value=({'IDF_PATH':str(self.root/'fake-idf')},sys.executable)), \
                     patch.object(lab.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout='ESP-IDF v6.1')), \
                     patch.object(lab.subprocess,'call',side_effect=runner),contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(0,lab.main())
                self.assertEqual(['reconfigure',action] if action in ('build','flash') else [action],calls)
                self.assertEqual([],lab.config_mismatches(config,lab.expected_config('ugv','ugv-001','ugv-root',6)))
                self.assertEqual(identities,self.hashes())
        backups=list(cache.glob('sdkconfig.before-reset-*'))
        self.assertEqual(4,len(backups))
        for backup in backups:self.assertEqual(old_bytes,backup.read_bytes())
    def test_controller_reloads_any_registered_identity_without_learning_from_mqtt(self):
        from changan_ugv.nodes.controller import Controller
        import threading
        from types import SimpleNamespace
        controller=Controller.__new__(Controller)
        controller.registry=Registry(nodes=['uav-001'])
        controller.registry.nodes['uav-001']['preserved']='yes'
        controller.condition=threading.Condition();controller.connected=threading.Event();controller.connected.set()
        controller.inventory_path=self.root/'config/nodes.json'
        controller.inventory_text=None;controller.inventory_error=None
        subscriptions=[];controller.client=SimpleNamespace(subscribe=lambda topics:subscriptions.extend(topics))
        enroll(self.root,'uav','inspection_017')
        controller.refresh_inventory()
        self.assertIn('inspection_017',controller.registry.nodes)
        self.assertEqual('yes',controller.registry.nodes['uav-001']['preserved'])
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
        config=cache/'sdkconfig';config.write_text('CONFIG_APP_ROLE_MICRO_UAV=y\nCONFIG_APP_TOPOLOGY_CHAIN=y\nCONFIG_APP_ARCHITECTURE_VERSION=3\nCONFIG_MESH_LITE_MAXIMUM_LEVEL_ALLOWED=4\nCONFIG_APP_TRANSPORT_MQTT_SERIAL=y\nCONFIG_APP_UGV_NODE_ID="ugv-root"\nCONFIG_APP_NODE_ID="micro-001"\n')
        before=config.read_bytes()
        import idf_env
        argv=['lab.py','--role','micro_uav','--node-id','micro-002','--transport','mqtt_serial','--port','COM_FAKE','flash']
        for flags in ([],['--reset-config'],['--reset-config','--dry-run']):
            with patch.object(lab,'__file__',str(self.root/'tools/lab.py')),patch.object(sys,'argv',argv+flags), \
                 patch.object(idf_env,'prepare_idf_environment') as environment, \
                 patch.object(lab.subprocess,'call') as flash,contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):lab.main()
            environment.assert_not_called();flash.assert_not_called();self.assertEqual(before,config.read_bytes())
    def test_custom_id_dry_run_never_enrolls_or_writes_a_profile(self):
        before=self.hashes()
        argv=['lab.py','--transport','mqtt_serial','--role','micro_uav','--node-id','micro-099','--dry-run']
        with patch.object(sys,'argv',argv),contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(0,lab.main())
        self.assertIn('micro-099',output.getvalue());self.assertEqual(before,self.hashes())
        self.assertFalse((ROOT/'secrets/micro-099').exists())
if __name__=='__main__':unittest.main()
