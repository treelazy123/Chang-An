"""Prepare a separate untrusted UAV client identity; never overwrite enrolled credentials."""
import argparse
from datetime import timedelta
import hashlib
import json
from pathlib import Path

def prepare(root,node_id):
    from cryptography import x509
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import hashes,serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID,ExtendedKeyUsageOID
    from node_inventory import valid_id
    valid_id(node_id);root=Path(root).resolve();source=root/'secrets'/node_id
    metadata=json.loads((source/'identity.json').read_text(encoding='utf-8'))
    if metadata.get('node_id')!=node_id or metadata.get('role')!='uav':
        raise ValueError('Negative client certificate mode is restricted to an existing UAV identity')
    original=x509.load_pem_x509_certificate((source/'client.pem').read_bytes())
    trusted_ca=x509.load_pem_x509_certificate((source/'ca.pem').read_bytes())
    if original.fingerprint(hashes.SHA256()).hex()!=metadata.get('certificate_sha256'):
        raise ValueError('Enrolled certificate fingerprint changed; preserve and inspect the original identity')
    target=root/'runtime/tls-negative'/node_id
    manifest=target/'test-identity.json'
    if target.exists():
        if not manifest.is_file():raise ValueError('Existing incomplete test directory; inspect it instead of overwriting')
        record=json.loads(manifest.read_text(encoding='utf-8'))
        if record.get('source_sha256')!=hashlib.sha256((source/'client.pem').read_bytes()).hexdigest():
            raise ValueError('Original certificate changed since test preparation')
    else:
        # Keep the original validity window so the lab's provisioned clock cannot
        # reject this leaf before the intended broker trust-chain check.
        start=original.not_valid_before_utc;end=original.not_valid_after_utc
        issuer=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'Changan Untrusted Test CA')])
        ca_key=ec.generate_private_key(ec.SECP256R1())
        ca=(x509.CertificateBuilder().subject_name(issuer).issuer_name(issuer)
            .public_key(ca_key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(start-timedelta(days=1)).not_valid_after(end+timedelta(days=1))
            .add_extension(x509.BasicConstraints(ca=True,path_length=0),critical=True)
            .add_extension(x509.KeyUsage(False,False,False,False,False,True,True,False,False),critical=True)
            .sign(ca_key,hashes.SHA256()))
        key=ec.generate_private_key(ec.SECP256R1())
        cert=(x509.CertificateBuilder().subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,node_id)]))
              .issuer_name(issuer).public_key(key.public_key()).serial_number(x509.random_serial_number())
              .not_valid_before(start).not_valid_after(end)
              .add_extension(x509.BasicConstraints(ca=False,path_length=None),critical=True)
              .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH]),critical=False)
              .add_extension(x509.KeyUsage(True,False,False,False,False,False,False,False,False),critical=True)
              .sign(ca_key,hashes.SHA256()))
        target.mkdir(parents=True,exist_ok=False)
        (target/'ca.pem').write_bytes((source/'ca.pem').read_bytes())
        (target/'untrusted-ca.pem').write_bytes(ca.public_bytes(serialization.Encoding.PEM))
        (target/'client.pem').write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        private=target/'client.key'
        private.write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
        private.chmod(0o600)
        record={'node_id':node_id,'test':'untrusted_client_ca','source_sha256':hashlib.sha256((source/'client.pem').read_bytes()).hexdigest()}
        manifest.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    # Verify the test is a matching pair and isolates the intended failure.
    cert=x509.load_pem_x509_certificate((target/'client.pem').read_bytes())
    key=serialization.load_pem_private_key((target/'client.key').read_bytes(),password=None)
    ca=x509.load_pem_x509_certificate((target/'untrusted-ca.pem').read_bytes())
    der=serialization.Encoding.DER;fmt=serialization.PublicFormat.SubjectPublicKeyInfo
    if key.public_key().public_bytes(der,fmt)!=cert.public_key().public_bytes(der,fmt):
        raise ValueError('Test private key does not match test certificate')
    cert.verify_directly_issued_by(ca)
    try:cert.verify_directly_issued_by(trusted_ca)
    except (ValueError,InvalidSignature):pass
    else:raise ValueError('Test certificate unexpectedly chains to the real CA')
    if (target/'ca.pem').read_bytes()!=(source/'ca.pem').read_bytes():raise ValueError('Server trust CA must stay unchanged')
    if [n.value for n in cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)]!=[node_id]:raise ValueError('Test CN mismatch')
    if ExtendedKeyUsageOID.CLIENT_AUTH not in cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value:
        raise ValueError('Test certificate must have clientAuth usage')
    if cert.not_valid_before_utc!=original.not_valid_before_utc or cert.not_valid_after_utc!=original.not_valid_after_utc:
        raise ValueError('Test certificate validity window changed')
    return {'node_id':node_id,'directory':str(target),'original_credentials':'unchanged','expected_result':'Broker rejects untrusted client certificate'}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--node-id',required=True)
    args=parser.parse_args()
    try:record=prepare(args.root,args.node_id)
    except (ValueError,OSError) as exc:parser.exit(2,str(exc)+'\n')
    print(json.dumps(record,ensure_ascii=False))
if __name__=='__main__':main()
