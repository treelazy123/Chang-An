"""Regression checks for the SDK migration boundary; no device is accessed."""
import hashlib
import importlib.util
import itertools
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('prepare_napt', ROOT/'tools/prepare_napt.py')
napt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(napt)


class NaptCompatibility(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(ROOT/'tools'))
        from idf_env import prepare_idf_environment
        env, _ = prepare_idf_environment(ROOT)
        sdk = Path(env['IDF_PATH'])/'components/lwip/lwip/src/core/ipv4'
        cls.source_path = sdk/'ip4_napt.c'
        cls.source_bytes = cls.source_path.read_bytes()
        cls.source = cls.source_path.read_text(encoding='utf-8')
        cls.ip4 = (sdk/'ip4.c').read_text(encoding='utf-8')
        cls.patch = (ROOT/'third_party/iot_bridge/patch/ip4_napt.patch').read_text(encoding='utf-8')

    def test_generated_source_and_idempotence(self):
        generated = napt.prepare(self.source, self.ip4, self.patch)
        self.assertIn('void ip_napt_table_clear(void)', generated)
        self.assertIn('IP_NAPT_ADD_FAILED_HOOK();', generated)
        self.assertEqual(generated, napt.prepare(generated, self.ip4, self.patch))
        self.assertEqual(self.source_bytes, self.source_path.read_bytes())

    def test_mismatched_sdk_is_rejected(self):
        with self.assertRaises(ValueError):
            napt.prepare(self.source.replace('ip_napt_add() failed to insert', 'changed'), self.ip4, self.patch)
        with self.assertRaises(ValueError):
            napt.prepare(self.source, '', self.patch)

    def test_partial_patch_is_rejected(self):
        with self.assertRaises(ValueError):
            napt.prepare(self.source + '\nvoid ip_napt_table_clear(void);', self.ip4, self.patch)

    def test_missing_patch_implementation_is_rejected(self):
        with self.assertRaises(ValueError):
            napt.prepare(self.source, self.ip4, '')


class BuildConfiguration(unittest.TestCase):
    def test_all_twelve_dry_runs_are_isolated(self):
        dirs = set()
        for role, topology in itertools.product(('pc_root', 'ugv', 'uav', 'micro_uav'), ('star', 'chain', 'auto')):
            result = subprocess.run([sys.executable, str(ROOT/'tools/lab.py'), '--role', role,
                                     '--topology', topology, '--dry-run'], capture_output=True, text=True)
            self.assertEqual(0, result.returncode, result.stderr)
            directory = str(ROOT/'build'/'four-node'/(role+'-'+topology))
            self.assertIn(directory, result.stdout)
            self.assertIn('SDKCONFIG='+str(Path(directory)/'sdkconfig'), result.stdout)
            dirs.add(directory)
        self.assertEqual(12, len(dirs))

    def test_flash_and_monitor_require_explicit_port(self):
        for action in ('flash', 'monitor'):
            result = subprocess.run([sys.executable, str(ROOT/'tools/lab.py'), '--role', 'pc_root',
                                     '--dry-run', action], capture_output=True, text=True)
            self.assertNotEqual(0, result.returncode)
            self.assertIn('Provide --port', result.stderr)

    def test_partition_preserves_nvs_and_fits_two_mib(self):
        lines = (ROOT/'firmware/partitions.csv').read_text(encoding='utf-8').splitlines()
        partitions = [line.split(',') for line in lines if line.strip() and not line.startswith('#')]
        nvs, phy, app = [[field.strip() for field in row] for row in partitions]
        self.assertEqual((0x9000, 0x6000), (int(nvs[3], 0), int(nvs[4], 0)))
        self.assertEqual(0x10000, int(app[3], 0))
        self.assertEqual(0x200000, int(app[3], 0) + int(app[4], 0))


if __name__ == '__main__':
    unittest.main()
