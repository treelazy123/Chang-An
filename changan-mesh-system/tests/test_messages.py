"""Current JSON protocol: bounds, duplicate keys and command validation."""
import json
import unittest
from changan_ugv.protocol.messages import encode,command,_unique_object,validate
class Messages(unittest.TestCase):
    def test_json_roundtrip_and_unicode(self):
        packet=command('echo ugv-001 hello','request-1')
        self.assertEqual(packet,json.loads(encode(packet)))
    def test_invalid_objects_duplicate_keys_nonfinite_and_limits(self):
        for obj in ([],{'v':True,'type':'list'},{'v':1,'type':{}},{'v':1,'type':'x','payload':'x'*2000}):
            with self.assertRaises(ValueError):encode(obj)
        with self.assertRaises(ValueError):json.loads('{"v":1,"v":1}',object_pairs_hook=_unique_object)
        with self.assertRaises(ValueError):encode(dict(v=1,type='list',number=float('nan')))
        for line in ('ping ../bad','list extra','echo uav-001','reboot ugv-root'):
            with self.assertRaises(ValueError):command(line)
