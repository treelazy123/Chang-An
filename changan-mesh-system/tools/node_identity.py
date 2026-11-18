"""Incremental per-device credentials using the existing lab CA. Existing private keys never change."""
from contextlib import contextmanager
from datetime import datetime,timedelta,timezone
import json
import os
from pathlib import Path
import shutil
import tempfile
import time
from node_inventory import ROLES,valid_id,load_inventory,write_inventory,write_acl,assign_ap_subnets,next_ap_subnet

def check_identity(root,node_id):
    from cryptography import x509
    from cryptography.hazmat.primitives import serialization,hashes
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID,ExtendedKeyUsageOID
    root=Path(root);valid_id(node_id);secret=root/'secrets';directory=secret/node_id
    ca=x509.load_pem_x509_certificate((secret/'ca.pem').read_bytes())
    cert=x509.load_pem_x509_certificate((directory/'client.pem').read_bytes())
    key=serialization.load_pem_private_key((directory/'client.key').read_bytes(),password=None)
    if (directory/'ca.pem').read_bytes()!=(secret/'ca.pem').read_bytes():raise ValueError('Device CA mismatch: '+node_id)
    if [n.value for n in cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)]!=[node_id]:raise ValueError('Certificate CN does not match node ID')
    if cert.issuer!=ca.subject:raise ValueError('Unexpected certificate issuer')
    from cryptography.exceptions import InvalidSignature
    try:ca.public_key().verify(cert.signature,cert.tbs_certificate_bytes,ec.ECDSA(cert.signature_hash_algorithm))
    except InvalidSignature as exc:raise ValueError('Device certificate is not signed by this lab CA') from exc
    encoding=serialization.Encoding.DER;form=serialization.PublicFormat.SubjectPublicKeyInfo
    if key.public_key().public_bytes(encoding,form)!=cert.public_key().public_bytes(encoding,form):raise ValueError('Device key/certificate mismatch')
    if ExtendedKeyUsageOID.CLIENT_AUTH not in cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value:raise ValueError('Not a client certificate')
    now=datetime.now(timezone.utc)
    if not cert.not_valid_before_utc<=now<=cert.not_valid_after_utc:raise ValueError('Device certificate expired or not yet valid')
    if not ca.not_valid_before_utc<=now<=ca.not_valid_after_utc:raise ValueError('Lab CA expired or not yet valid')
    return cert.fingerprint(hashes.SHA256()).hex()

@contextmanager
def enrollment_lock(root):
    path=Path(root)/'secrets/.enrollment.lock'
    try:fd=os.open(str(path),os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    except FileExistsError:raise ValueError('Another enrollment is in progress (secrets/.enrollment.lock); retry after it finishes')
    try:yield
    finally:os.close(fd);path.unlink()

def issue(root,node_id):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes,serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID,ExtendedKeyUsageOID
    secret=Path(root)/'secrets'
    ca=x509.load_pem_x509_certificate((secret/'ca.pem').read_bytes())
    ca_key=serialization.load_pem_private_key((secret/'ca.key').read_bytes(),password=None)
    encoding=serialization.Encoding.DER;form=serialization.PublicFormat.SubjectPublicKeyInfo
    if ca_key.public_key().public_bytes(encoding,form)!=ca.public_key().public_bytes(encoding,form):
        raise ValueError('CA key/certificate mismatch')
    now=datetime.now(timezone.utc)
    if not ca.not_valid_before_utc<=now<ca.not_valid_after_utc:raise ValueError('CA validity does not cover enrollment time')
    key=ec.generate_private_key(ec.SECP256R1())
    cert=(x509.CertificateBuilder().subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,node_id)]))
          .issuer_name(ca.subject).public_key(key.public_key()).serial_number(x509.random_serial_number())
          .not_valid_before(max(now-timedelta(minutes=5),ca.not_valid_before_utc))
          .not_valid_after(min(now+timedelta(days=90),ca.not_valid_after_utc))
          .add_extension(x509.BasicConstraints(ca=False,path_length=None),critical=True)
          .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH]),critical=False)
          .add_extension(x509.KeyUsage(True,False,False,False,False,False,False,False,False),critical=True)
          .sign(ca_key,hashes.SHA256()))
    staging=Path(tempfile.mkdtemp(prefix='.enroll-',dir=secret))
    try:
        (staging/'client.pem').write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        keyfile=staging/'client.key';keyfile.write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()));keyfile.chmod(0o600)
        (staging/'ca.pem').write_bytes((secret/'ca.pem').read_bytes())
        staging.rename(secret/node_id)
    finally:
        if staging.exists():
            if staging.resolve().parent!=secret.resolve() or not staging.name.startswith('.enroll-'):
                raise ValueError('Refusing cleanup outside enrollment staging directory')
            shutil.rmtree(staging)

def enroll(root,role,node_id,ugv_id=None):
    root=Path(root).resolve();valid_id(node_id)
    if role not in ROLES:raise ValueError('Unknown device role')
    if not (root/'secrets/ca.key').is_file():raise ValueError('Initialize the lab CA with tools/provision_mqtt.py first')
    with enrollment_lock(root):
        data=assign_ap_subnets(load_inventory(root))
        entry=next((e for e in data['nodes'] if e['node_id'].casefold()==node_id.casefold()),None)
        if entry and (entry['node_id']!=node_id or entry['role']!=role):raise ValueError('ID already belongs to a different role or spelling: '+node_id)
        if entry and not entry.get('enabled',True):raise ValueError('Node is disabled in administrator inventory: '+node_id)
        subnet=None if role=='micro_uav' else (entry['ap_subnet'] if entry else next_ap_subnet(data))
        target=node_id if role=='ugv_root' else (ugv_id or (entry or {}).get('root_id','ugv-root'))
        valid_id(target)
        if role!='ugv_root' and not any(e['node_id']==target and e['role']=='ugv_root' and e.get('enabled',True) for e in data['nodes']):
            raise ValueError('Enroll the target root identity first: '+target)
        if role=='ugv_root':
            record=dict(node_id=node_id,role=role,root_id=node_id,enabled=True,ap_subnet=subnet)
            if entry:entry.update(record)
            else:data['nodes'].append(record)
            write_inventory(root,data);write_acl(root,data)
            return dict(record,created=False,certificate_sha256=None)
        directory=root/'secrets'/node_id
        metadata=directory/'identity.json'
        if metadata.exists():
            old=json.loads(metadata.read_text(encoding='utf-8'))
            if old.get('node_id')!=node_id or old.get('role')!=role:raise ValueError('Existing device identity cannot change role')
        elif directory.exists() and entry is None:
            raise ValueError('Existing unregistered identity directory; inspect before enrollment: '+node_id)
        created=not directory.exists()
        if created:issue(root,node_id)
        fingerprint=check_identity(root,node_id)
        if metadata.exists() and old.get('certificate_sha256')!=fingerprint:
            raise ValueError('Certificate fingerprint changed; inspect identity rather than silently reusing it')
        record={'node_id':node_id,'role':role,'root_id':target,'enabled':(entry or {}).get('enabled',True),'ap_subnet':subnet}
        if entry:entry.update(record)
        else:data['nodes'].append(record)
        metadata.write_text(json.dumps(dict(record,certificate_sha256=fingerprint),indent=2)+'\n',encoding='utf-8')
        clock=directory/'clock.defaults'
        clock.write_text('CONFIG_APP_TLS_BOOTSTRAP_UNIX='+str(int(time.time()))+'\n',encoding='utf-8')
        write_inventory(root,data);write_acl(root,data)
        return dict(record,created=created,certificate_sha256=fingerprint)
