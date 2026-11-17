"""Untrusted-client experiments preserve all enrolled credentials and normal build paths."""
from pathlib import Path
import contextlib
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
sys.path.insert(0,str(ROOT/'host/src'))
from provision_mqtt import provision
from tls_negative_identity import prepare
class NegativeIdentity(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        with contextlib.redirect_stdout(io.StringIO()):provision(self.root)
        from node_identity import enroll
        enroll(self.root,"uav","uav-001","ugv-001")
        enroll(self.root,"micro_uav","micro-001","ugv-001")
    def snapshot(self):
        return {str(p.relative_to(self.root)):hashlib.sha256(p.read_bytes()).hexdigest()
                for p in (self.root/'secrets').rglob('*') if p.is_file()}
    def test_pair_is_matching_untrusted_and_preserves_existing_identity(self):
        before=self.snapshot();record=prepare(self.root,'uav-001')
        self.assertEqual(before,self.snapshot())
        target=Path(record['directory']);self.assertEqual(self.root/'runtime/tls-negative/uav-001',target)
        self.assertEqual((self.root/'secrets/uav-001/ca.pem').read_bytes(),(target/'ca.pem').read_bytes())
        self.assertTrue((target/'client.pem').is_file());self.assertTrue((target/'client.key').is_file())
        hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in target.iterdir()}
        prepare(self.root,'uav-001')
        self.assertEqual(hashes,{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in target.iterdir()})
    def test_key_mismatch_is_rejected_instead_of_silent_regeneration(self):
        record=prepare(self.root,'uav-001');target=Path(record['directory'])
        (target/'client.key').write_bytes((self.root/'secrets/micro-001/client.key').read_bytes())
        with self.assertRaises(ValueError):prepare(self.root,'uav-001')
    def test_non_uav_and_original_identity_tampering_are_rejected(self):
        with self.assertRaises(ValueError):prepare(self.root,'micro-001')
        p=self.root/'secrets/uav-001/identity.json';metadata=json.loads(p.read_text());metadata['certificate_sha256']='changed';p.write_text(json.dumps(metadata))
        with self.assertRaises(ValueError):prepare(self.root,'uav-001')
class NegativeBuildMode(unittest.TestCase):
    def dry(self,*extra):
        return subprocess.run([sys.executable,str(ROOT/'tools/lab.py'),'--transport','mqtt_serial',
                               '--role','uav','--node-id','uav-001','--dry-run',*extra],capture_output=True,text=True)
    def test_test_build_and_identity_override_are_separate_from_normal(self):
        normal=self.dry();negative=self.dry('--tls-test-untrusted-client')
        self.assertEqual(0,normal.returncode,normal.stderr);self.assertEqual(0,negative.returncode,negative.stderr)
        self.assertIn(str(ROOT/'build/mqtt_serial/nodes/uav-001/uav-chain'),normal.stdout)
        self.assertIn(str(ROOT/'build/mqtt_serial/tls-negative/uav-001/uav-chain'),negative.stdout)
        self.assertIn('MESH_TLS_TEST_IDENTITY_DIR='+str(ROOT/'runtime/tls-negative/uav-001').replace('\\','/'),negative.stdout)
        self.assertNotIn('runtime/tls-negative/uav-001',normal.stdout)
    def test_wrong_role_is_rejected_without_touching_identities(self):
        result=subprocess.run([sys.executable,str(ROOT/'tools/lab.py'),'--transport','mqtt_serial',
            '--role','micro_uav','--node-id','micro-001','--tls-test-untrusted-client','--dry-run'],capture_output=True,text=True)
        self.assertNotEqual(0,result.returncode)
if __name__=='__main__':unittest.main()
