"""Exercise cache repair dispatch with a fake runner; never invokes IDF/Ninja."""
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from lab import execute_idf, backup_config, config_mismatches, expected_config

class CacheRepair(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory=Path(self.temp.name)
        self.calls=[]
        self.command=['idf-python','idf.py','-B',str(self.directory),'-p','COM7','flash']
    def runner(self,cmd,env):
        self.calls.append(cmd)
        return 0
    def test_missing_bootloader_metadata_reconfigures_without_touching_sdkconfig(self):
        (self.directory/'build.ninja').write_text('fixture')
        config=self.directory/'sdkconfig';config.write_text('CONFIG_APP_NODE_ID="http-local"\n')
        before=config.read_bytes()
        self.assertEqual(0,execute_idf(self.command,self.directory,{},self.runner))
        self.assertEqual(['reconfigure','flash'],[c[-1] for c in self.calls])
        self.assertEqual(self.command[:-1],self.calls[0][:-1])
        self.assertEqual(before,config.read_bytes())
    def test_failed_reconfigure_does_not_flash(self):
        (self.directory/'build.ninja').write_text('fixture')
        def fail(cmd,env):
            self.calls.append(cmd)
            return 9
        self.assertEqual(9,execute_idf(self.command,self.directory,{},fail))
        self.assertEqual(['reconfigure'],[c[-1] for c in self.calls])
    def test_reset_forces_reconfigure_and_validates_before_flash(self):
        order=[]
        def runner(cmd,env):
            order.append(cmd[-1]);return 0
        execute_idf(self.command,self.directory,{},runner,force_reconfigure=True,
                    verify_config=lambda:order.append('validate'))
        self.assertEqual(['reconfigure','validate','flash'],order)
    def test_reset_failure_or_invalid_generated_config_never_flashes(self):
        def fail(cmd,env):
            self.calls.append(cmd);return 8
        self.assertEqual(8,execute_idf(self.command,self.directory,{},fail,force_reconfigure=True))
        self.assertEqual(['reconfigure'],[c[-1] for c in self.calls])
        self.calls.clear()
        def invalid():raise ValueError('wrong root in generated config')
        with self.assertRaisesRegex(ValueError,'wrong root'):
            execute_idf(self.command,self.directory,{},self.runner,force_reconfigure=True,verify_config=invalid)
        self.assertEqual(['reconfigure'],[c[-1] for c in self.calls])
    def test_fresh_or_complete_cache_runs_requested_action_once(self):
        execute_idf(self.command,self.directory,{},self.runner)
        self.assertEqual(['flash'],[c[-1] for c in self.calls])
        self.calls.clear()
        (self.directory/'build.ninja').write_text('fixture')
        metadata=self.directory/'bootloader-prefix/tmp/bootloader-cfgcmd.txt'
        metadata.parent.mkdir(parents=True);metadata.write_text('fixture')
        execute_idf(self.command,self.directory,{},self.runner)
        self.assertEqual(['flash'],[c[-1] for c in self.calls])
    def test_monitor_and_explicit_reconfigure_do_not_add_reconfigure(self):
        (self.directory/'build.ninja').write_text('fixture')
        for action in ('monitor','reconfigure'):
            self.calls.clear()
            execute_idf(self.command[:-1]+[action],self.directory,{},self.runner)
            self.assertEqual([action],[c[-1] for c in self.calls])

class ConfigReset(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.config=self.root/'build/mqtt_serial/nodes/ugv-001/ugv-chain/sdkconfig'
        self.config.parent.mkdir(parents=True)
        self.config.write_text('CONFIG_APP_ROLE_UGV=y\nCONFIG_APP_NODE_ID="ugv-001"\n'
                               'CONFIG_APP_ARCHITECTURE_VERSION=2\nCONFIG_APP_UGV_NODE_ID="ugv-001"\n')
    def test_reset_archives_exact_config_preserving_credentials_and_other_build_files(self):
        preserved=[self.root/'secrets/ugv-001/client.key',self.root/'runtime/ugv-root/tasks.sqlite3',
                   self.config.parent/'sdkconfig.old',self.config.parent/'build.ninja']
        for path in preserved:
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'preserve me')
        before=self.config.read_bytes()
        backup=backup_config(self.config,self.root,'ugv','ugv-001')
        self.assertEqual(before,backup.read_bytes());self.assertFalse(self.config.exists())
        self.assertTrue(backup.name.startswith('sdkconfig.before-reset-'))
        for path in preserved:self.assertEqual(b'preserve me',path.read_bytes())
    def test_reset_cannot_bypass_device_role_or_build_directory(self):
        before=self.config.read_bytes()
        for role,node in [('uav','ugv-001'),('ugv','ugv-002')]:
            with self.assertRaisesRegex(ValueError,'identity/role'):
                backup_config(self.config,self.root,role,node)
            self.assertEqual(before,self.config.read_bytes())
        with self.assertRaisesRegex(ValueError,'outside'):
            backup_config(self.config,self.root/'elsewhere','ugv','ugv-001')
        self.assertEqual(before,self.config.read_bytes())
    def test_diagnostics_include_both_old_architecture_and_old_root(self):
        differences=config_mismatches(self.config,expected_config('ugv','ugv-001','ugv-root'))
        self.assertIn('CONFIG_APP_ARCHITECTURE_VERSION: cached=2, expected=3',differences)
        self.assertIn('CONFIG_APP_UGV_NODE_ID: cached="ugv-001", expected="ugv-root"',differences)
if __name__=='__main__': unittest.main()
