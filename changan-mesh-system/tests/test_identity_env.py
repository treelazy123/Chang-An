"""Exercise missing-IDF-crypto fallback with real uv Python and temporary credentials, no IDF/flash."""
from pathlib import Path
import contextlib
import hashlib
import io
import os
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from provision_mqtt import provision
from identity_env import ensure_identity
class HostIdentityEnvironment(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        with contextlib.redirect_stdout(io.StringIO()):provision(self.root)
    def hashes(self):
        return {str(p.relative_to(self.root)):hashlib.sha256(p.read_bytes()).hexdigest()
                for p in (self.root/'secrets').rglob('*') if p.is_file() and p.suffix in ('.pem','.key')}
    def test_idf_without_crypto_delegates_to_host_and_preserves_existing_keys(self):
        before=self.hashes()
        with patch('identity_env.crypto_available',return_value=False),contextlib.redirect_stdout(io.StringIO()):
            record=ensure_identity(self.root,'ugv','ugv-001','ugv-001',host_python=sys.executable)
        self.assertFalse(record['created']);self.assertEqual('ugv-001',record['node_id'])
        self.assertEqual(before,self.hashes())
    def test_new_node_can_be_enrolled_in_host_process_and_monitor_only_checks(self):
        with patch('identity_env.crypto_available',return_value=False),contextlib.redirect_stdout(io.StringIO()):
            added=ensure_identity(self.root,'micro_uav','micro-099','ugv-001',host_python=sys.executable)
            before=self.hashes()
            checked=ensure_identity(self.root,'micro_uav','micro-099','ugv-001',check_only=True,host_python=sys.executable)
        self.assertTrue(added['created']);self.assertFalse(checked['created']);self.assertEqual(before,self.hashes())
    def test_missing_host_environment_reports_uv_sync_without_touching_idf(self):
        with patch('identity_env.crypto_available',return_value=False):
            with self.assertRaisesRegex(ValueError,'uv sync --locked'):
                ensure_identity(self.root,'ugv','ugv-001')
    def test_idf_pythonpath_does_not_leak_into_host_imports(self):
        with patch('identity_env.crypto_available',return_value=False),patch.dict(os.environ,{'PYTHONHOME':str(self.root/'invalid-python'),'PYTHONPATH':str(self.root/'invalid-imports')}),contextlib.redirect_stdout(io.StringIO()):
            record=ensure_identity(self.root,'uav','uav-001',check_only=True,host_python=sys.executable)
        self.assertEqual('uav-001',record['node_id'])
    def test_worker_rejection_propagates_and_never_replaces_keys(self):
        before=self.hashes()
        with patch('identity_env.crypto_available',return_value=False):
            with self.assertRaisesRegex(ValueError,'different role'):
                ensure_identity(self.root,'uav','micro-001',host_python=sys.executable)
        self.assertEqual(before,self.hashes())
if __name__=='__main__':unittest.main()
