"""Background admission persists decisions without issuing keys or touching services."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import time
import unittest
from changan_ugv.nodes.admission import AdmissionManager
from changan_ugv.nodes.inventory import load_inventory,write_inventory,clients
from changan_ugv.tasks.store import Store
from provision_mqtt import provision


class AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        with contextlib.redirect_stdout(io.StringIO()):provision(self.root)
        write_inventory(self.root,load_inventory(self.root))
        self.file=self.root/'config/nodes.json'
        self.store=Store(self.root/'runtime/tasks.db');self.addCleanup(self.store.close)
        self.manager=AdmissionManager(self.store,self.file,'ugv-root',self.root/'secrets/ca.pem',
                                      self.root/'secrets',self.root/'runtime/acl.pending.conf')

    def request(self,status='revoked',revision=0,identity='change-1',target='ugv-001'):
        return dict(v=1,type='node.admission',node_id='http-local',msg_id=identity,
            deadline_unix=int(time.time())+20,target=target,trust_status=status,expected_revision=revision)

    def test_revoke_grant_replay_conflict_and_audit(self):
        request=self.request()
        first=self.manager.change(request)
        self.assertEqual(first,self.manager.change(request))
        self.assertNotIn('ugv-001',clients(load_inventory(self.root)))
        self.assertFalse(first['broker_acl_applied'])
        self.assertNotIn('user ugv-001\n',(self.root/'runtime/acl.pending.conf').read_text())
        with self.assertRaisesRegex(ValueError,'msg_id_conflict'):
            self.manager.change(dict(request,trust_status='trusted'))
        with self.assertRaisesRegex(ValueError,'admission_revision_conflict'):
            self.manager.change(self.request('trusted',0,'conflict'))
        self.manager.change(self.request('trusted',1,'grant'))
        self.assertIn('ugv-001',clients(load_inventory(self.root)))
        rows=self.store.db.execute('SELECT * FROM admission_decisions').fetchall()
        self.assertEqual(2,len(rows));self.assertTrue(rows[1]['certificate_sha256'])
        self.assertTrue(all(r['phase']=='applied' for r in rows))

    def test_bad_certificate_disabled_unknown_and_root_are_rejected(self):
        before=self.file.read_bytes()
        key=self.root/'secrets/ugv-001/client.key';digest=hashlib.sha256(key.read_bytes()).hexdigest()
        cert=self.root/'secrets/ugv-001/client.pem'
        cert.write_bytes((self.root/'secrets/uav-001/client.pem').read_bytes())
        with self.assertRaisesRegex(ValueError,'certificate_identity_mismatch'):
            self.manager.change(self.request('trusted'))
        self.assertEqual(before,self.file.read_bytes())
        self.assertEqual(digest,hashlib.sha256(key.read_bytes()).hexdigest())
        for target in ('unknown','../escape','http-local'):
            with self.assertRaises(ValueError):self.manager.change(self.request(target=target))
        data=load_inventory(self.root);data['nodes'][1]['enabled']=False;write_inventory(self.root,data)
        with self.assertRaisesRegex(ValueError,'node_disabled'):self.manager.change(self.request('trusted'))

    def test_retry_reconciles_inventory_committed_before_acl_write_failure(self):
        from unittest.mock import patch
        request=self.request()
        with patch.object(self.manager,'write_acl',side_effect=OSError('temporary failure')):
            with self.assertRaises(OSError):self.manager.change(request)
        self.assertNotIn('ugv-001',clients(load_inventory(self.root)))
        self.assertEqual('pending',self.store.db.execute('SELECT phase FROM admission_decisions').fetchone()[0])
        self.assertEqual(1,self.manager.change(request)['admission_revision'])
        self.assertEqual('applied',self.store.db.execute('SELECT phase FROM admission_decisions').fetchone()[0])
