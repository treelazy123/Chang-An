"""UGV Service owns admission decisions; Mosquitto owns certificate/ACL enforcement.

Only pre-enrolled, root-scoped nodes can be granted access. This module neither
issues certificates nor reads private keys nor reloads production Broker services.
"""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import threading
import time
from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.x509.oid import ExtendedKeyUsageOID,NameOID
from changan_ugv.nodes.inventory import load_inventory,validate,valid_id,root_of,render_acl


class AdmissionManager:
    def __init__(self,store,inventory_file,root_id,ca_file,identities_dir,acl_output):
        self.store=store
        self.inventory_file=Path(inventory_file)
        self.root_id=root_id
        self.ca_file=Path(ca_file)
        self.identities_dir=Path(identities_dir)
        self.acl_output=Path(acl_output)
        self.lock=threading.RLock()
        with store.lock,store.db:
            store.db.execute('''CREATE TABLE IF NOT EXISTS admission_decisions (
                msg_id TEXT PRIMARY KEY, canonical TEXT NOT NULL, node_id TEXT NOT NULL,
                revision INTEGER NOT NULL, trust_status TEXT NOT NULL,
                certificate_sha256 TEXT, decided_at REAL NOT NULL, phase TEXT NOT NULL)''')

    def certificate(self,node_id):
        ca=x509.load_pem_x509_certificate(self.ca_file.read_bytes())
        cert=x509.load_pem_x509_certificate((self.identities_dir/node_id/'client.pem').read_bytes())
        try:cert.verify_directly_issued_by(ca)
        except (ValueError,TypeError,InvalidSignature) as exc:raise ValueError('certificate_not_trusted') from exc
        now=datetime.now(timezone.utc)
        if not ca.not_valid_before_utc<=now<=ca.not_valid_after_utc or not cert.not_valid_before_utc<=now<=cert.not_valid_after_utc:
            raise ValueError('certificate_expired_or_not_yet_valid')
        if [a.value for a in cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)]!=[node_id]:
            raise ValueError('certificate_identity_mismatch')
        try:
            if not ca.extensions.get_extension_for_class(x509.BasicConstraints).value.ca:
                raise ValueError('invalid_ca')
            if ExtendedKeyUsageOID.CLIENT_AUTH not in cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value:
                raise ValueError('certificate_not_client')
        except x509.ExtensionNotFound as exc:raise ValueError('certificate_missing_required_extension') from exc
        from cryptography.hazmat.primitives import hashes
        fingerprint=cert.fingerprint(hashes.SHA256()).hex()
        metadata=self.identities_dir/node_id/'identity.json'
        if metadata.exists():
            record=json.loads(metadata.read_text(encoding='utf-8'))
            if not isinstance(record,dict) or record.get('node_id')!=node_id or record.get('certificate_sha256')!=fingerprint:
                raise ValueError('enrolled_certificate_fingerprint_mismatch')
        return fingerprint

    def change(self,request):
        fields={'v','type','node_id','msg_id','deadline_unix','target','trust_status','expected_revision'}
        if set(request)-fields:raise ValueError('unknown_admission_fields')
        node_id=valid_id(request.get('target'))
        status=request.get('trust_status');revision=request.get('expected_revision')
        if status not in ('pending','trusted','revoked'):raise ValueError('invalid_trust_status')
        if type(revision) is not int or revision<0:raise ValueError('invalid_admission_revision')
        canonical=hashlib.sha256(json.dumps(request,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        with self.lock:
            data=load_inventory(path=self.inventory_file)
            entry=next((e for e in data['nodes'] if e['node_id']==node_id),None)
            if entry is None or root_of(entry)!=self.root_id:raise ValueError('node_not_managed')
            if node_id==self.root_id:raise ValueError('root_admission_requires_offline_configuration')
            with self.store.lock:
                old=self.store.db.execute('SELECT * FROM admission_decisions WHERE msg_id=?',(request['msg_id'],)).fetchone()
            if old:
                if old['canonical']!=canonical:raise ValueError('msg_id_conflict')
                if old['phase']=='applied' or (entry.get('admission_revision',0)==old['revision'] and entry.get('trust_status','trusted')==old['trust_status']):
                    self.write_acl(data)
                    self.applied(request['msg_id'])
                    return self.receipt(node_id,old['trust_status'],old['revision'])
                raise ValueError('admission_uncertain_query_inventory')
            if entry.get('admission_revision',0)!=revision:raise ValueError('admission_revision_conflict')
            fingerprint=None
            if status=='trusted':
                if not entry.get('enabled',True):raise ValueError('node_disabled')
                fingerprint=self.certificate(node_id)
            entry.update(trust_status=status,admission_revision=revision+1)
            validate(data)
            # Intent is durable before the atomic inventory replacement. A retry
            # reconciles a crash after replacement rather than silently granting twice.
            with self.store.lock,self.store.db:
                self.store.db.execute('INSERT INTO admission_decisions VALUES(?,?,?,?,?,?,?,?)',
                    (request['msg_id'],canonical,node_id,revision+1,status,fingerprint,time.time(),'pending'))
            temporary=self.inventory_file.with_suffix('.admission.tmp')
            temporary.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            temporary.replace(self.inventory_file)
            self.write_acl(data)
            self.applied(request['msg_id'])
            return self.receipt(node_id,status,revision+1)

    def write_acl(self,data):
        self.acl_output.parent.mkdir(parents=True,exist_ok=True)
        temp=self.acl_output.with_suffix('.tmp')
        temp.write_text(render_acl(data),encoding='utf-8');temp.replace(self.acl_output)

    def applied(self,msg_id):
        with self.store.lock,self.store.db:
            self.store.db.execute("UPDATE admission_decisions SET phase='applied' WHERE msg_id=?",(msg_id,))

    def receipt(self,node_id,status,revision):
        return dict(node_id=node_id,trust_status=status,admission_revision=revision,
                    broker_acl_applied=False,broker_acl_reload_required=True)
