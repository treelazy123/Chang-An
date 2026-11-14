"""Exercise cache repair dispatch with a fake runner; never invokes IDF/Ninja."""
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from lab import execute_idf

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
        config=self.directory/'sdkconfig';config.write_text('CONFIG_APP_NODE_ID="pc-root-001"\n')
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
if __name__=='__main__': unittest.main()
