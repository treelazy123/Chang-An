"""Create an isolated lab CA, broker/device identities and local Mosquitto config. Never overwrites keys."""
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
import time

def provision(root):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
    root = Path(root).resolve()
    from node_inventory import load_inventory, write_inventory, write_acl
    inventory=load_inventory(root)
    secret = root / 'secrets'
    if secret.exists() and any(secret.iterdir()):
        raise ValueError('secrets is nonempty; existing keys are never overwritten. Use --node-id/--role for incremental enrollment, or --refresh-clock; existing keys are never replaced.')
    secret.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    def name(cn):
        return x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])
    def save_key(path, key):
        path.write_bytes(key.private_bytes(serialization.Encoding.PEM,
                         serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        path.chmod(0o600)
    ca_key = ec.generate_private_key(ec.SECP256R1())
    ca = (x509.CertificateBuilder().subject_name(name('Changan Mesh Lab CA'))
          .issuer_name(name('Changan Mesh Lab CA')).public_key(ca_key.public_key())
          .serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(days=1))
          .not_valid_after(now+timedelta(days=365))
          .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
          .add_extension(x509.KeyUsage(False, False, False, False, False, True, True, False, False), critical=True)
          .sign(ca_key, hashes.SHA256()))
    ca_bytes = ca.public_bytes(serialization.Encoding.PEM)
    (secret/'ca.pem').write_bytes(ca_bytes)
    save_key(secret/'ca.key', ca_key)
    for identity in ('ugv-broker.lab','controller-001',*(e['node_id'] for e in inventory['nodes'])):
        directory = secret/identity
        directory.mkdir()
        key = ec.generate_private_key(ec.SECP256R1())
        server = identity == 'ugv-broker.lab'
        builder = (x509.CertificateBuilder().subject_name(name(identity)).issuer_name(ca.subject)
                   .public_key(key.public_key()).serial_number(x509.random_serial_number())
                   .not_valid_before(now-timedelta(days=1)).not_valid_after(now+timedelta(days=90))
                   .add_extension(x509.BasicConstraints(ca=False,path_length=None), critical=True)
                   .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH if server else ExtendedKeyUsageOID.CLIENT_AUTH]), critical=False)
                   .add_extension(x509.KeyUsage(True, False, False, False, False, False, False, False, False), critical=True))
        if server:
            builder = builder.add_extension(x509.SubjectAlternativeName([x509.DNSName(identity)]), critical=False)
        cert = builder.sign(ca_key, hashes.SHA256())
        (directory/'client.pem').write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        save_key(directory/'client.key',key)
        (directory/'ca.pem').write_bytes(ca_bytes)
    runtime = root/'runtime'
    runtime.mkdir(parents=True, exist_ok=True)
    write_inventory(root,inventory)
    write_acl(root,inventory)
    from changan_ugv.deployment import render_broker_config
    config=render_broker_config(ca_file=secret/'ca.pem',server_cert=secret/'ugv-broker.lab/client.pem',
                               server_key=secret/'ugv-broker.lab/client.key',acl_file=runtime/'acl.conf')
    (runtime/'mosquitto.conf').write_text(config,encoding='utf-8')
    refresh_clock(root)
    print('Created lab identities and runtime/mosquitto.conf. Private keys are in ignored secrets/.')
def refresh_clock(root):
    root=Path(root)
    if not (root/'secrets/ca.pem').is_file():
        raise ValueError('Provision certificates first')
    (root/'secrets/clock.defaults').write_text('CONFIG_APP_TLS_BOOTSTRAP_UNIX='+str(int(time.time()))+'\n',encoding='utf-8')
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--refresh-clock',action='store_true')
    parser.add_argument('--sync-acl',action='store_true',help='Regenerate ACL from inventory without issuing certificates')
    parser.add_argument('--list',action='store_true',help='List all registered device identities and certificate status')
    parser.add_argument('--role',choices=('pc_root','ugv','uav','micro_uav'))
    parser.add_argument('--node-id',help='Incrementally enroll one device without replacing the CA or other keys')
    parser.add_argument('--ugv-id',help='UGV service identity for this device')
    args=parser.parse_args()
    try:
        if args.sync_acl:
            if args.list or args.node_id or args.role or args.ugv_id or args.refresh_clock:parser.error('--sync-acl is a standalone operation')
            from node_inventory import load_inventory,write_acl
            write_acl(args.root,load_inventory(args.root))
            print('ACL regenerated from administrator inventory; reload/restart the project Broker to apply.')
        elif args.list:
            if args.node_id or args.role or args.ugv_id or args.refresh_clock:parser.error('--list cannot combine with enrollment/clock options')
            from node_inventory import load_inventory
            from node_identity import check_identity
            for entry in load_inventory(args.root)['nodes']:
                try:check_identity(args.root,entry['node_id']);status='valid'
                except (OSError,ValueError):status='missing_or_invalid'
                print(entry['node_id']+' role='+entry['role']+' ugv='+entry.get('ugv_id','ugv-001')+
                      ' enabled='+str(entry.get('enabled',True))+' certificate='+status)
        elif args.node_id:
            if not args.role or args.refresh_clock: parser.error('--node-id requires --role and cannot combine with --refresh-clock')
            from node_identity import enroll
            result=enroll(args.root,args.role,args.node_id,args.ugv_id)
            print(('Created' if result['created'] else 'Reused')+' identity '+result['node_id']+' ('+result['role']+'). Existing keys preserved.')
            print('Inventory/ACL updated; restart or reload the project Broker to apply ACL changes; a running new-version mqtt_terminal reloads the inventory automatically.')
        elif args.role or args.ugv_id: parser.error('--role/--ugv-id require --node-id')
        elif args.refresh_clock: refresh_clock(args.root)
        else: provision(args.root)
    except (ValueError,OSError) as exc: parser.error(str(exc))
if __name__=='__main__': main()
