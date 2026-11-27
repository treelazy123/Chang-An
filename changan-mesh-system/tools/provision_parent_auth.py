"""Incremental parent-auth signing enrollment; existing TLS credentials are untouched."""
import argparse
import hashlib
import json
from pathlib import Path
from _bootstrap import bootstrap
bootstrap()
from cryptography.hazmat.primitives.asymmetric import ec
from changan_ugv.nodes.inventory import load_inventory, authorized
from changan_ugv.nodes.parent_authority import private_key, public_bytes


def pair(directory, name):
    private, public = directory / (name+'.key'), directory / (name+'.pub')
    if private.exists() != public.exists():
        raise ValueError('Incomplete parent-auth key pair; preserve files and inspect '+str(directory))
    if private.exists():
        key = private_key(private.read_bytes())
        if public_bytes(key.public_key()) != public.read_bytes():
            raise ValueError('Existing parent-auth public/private mismatch')
    else:
        key = ec.generate_private_key(ec.SECP256R1())
        directory.mkdir(parents=True, exist_ok=True)
        with private.open('xb') as stream:
            stream.write(key.private_numbers().private_value.to_bytes(32, 'big'))
        with public.open('xb') as stream:
            stream.write(public_bytes(key.public_key()))
    return public.read_bytes()


def provision(root,node_ids=None):
    from node_identity import enrollment_lock
    with enrollment_lock(root):
        return _provision(root,node_ids)


def _provision(root,node_ids=None):
    root = Path(root)
    data = load_inventory(root)
    if node_ids:
        unknown=set(node_ids)-{e['node_id'] for e in data['nodes']}
        if unknown:raise ValueError('Unknown enrolled node: '+','.join(sorted(unknown)))
        entries=[e for e in data['nodes'] if e['node_id'] in node_ids]
    else:
        entries=[e for e in data['nodes'] if authorized(e)]
    directory = root / 'secrets/parent-auth'
    # Check all current TLS enrollments before creating any new parent-auth keys.
    from node_identity import check_identity
    fingerprints = {e['node_id']: None if e['role']=='ugv_root' else check_identity(root,e['node_id'])
                    for e in entries}
    path = directory / 'bindings.json'
    record = json.loads(path.read_text(encoding='utf-8')) if path.exists() else dict(schema=1,nodes={})
    if record.get('schema') != 1 or not isinstance(record.get('nodes'),dict):
        raise ValueError('Invalid existing parent-auth bindings')
    if path.exists():
        for name in ('authority.key','authority.pub'):
            if not (directory/name).is_file():raise ValueError('Missing enrolled authority key; restore the original')
        if record.get('authority_sha256')!=hashlib.sha256((directory/'authority.pub').read_bytes()).hexdigest():
            raise ValueError('Existing authority fingerprint mismatch')
        for node,binding in record['nodes'].items():
            for name in ('auth.key','auth.pub'):
                if not (directory/'nodes'/node/name).is_file():raise ValueError('Missing enrolled node key: '+node)
            public=pair(directory/'nodes'/node,'auth')
            if public.hex()!=binding['public_key']:raise ValueError('Existing node signing identity mismatch: '+node)
    # Reject enrollment changes before generating any new node keys.
    for entry in entries:
        previous=record['nodes'].get(entry['node_id'])
        if previous and (previous['root_id']!=entry.get('root_id','ugv-root') or previous['role']!=entry['role'] or
                         previous['certificate_sha256']!=fingerprints[entry['node_id']]):
            raise ValueError('Existing parent-auth enrollment differs: '+entry['node_id'])
    authority = pair(directory, 'authority')
    record['authority_sha256']=hashlib.sha256(authority).hexdigest()
    seen={authority.hex():'authority'}
    for node,binding in record['nodes'].items():
        previous=seen.get(binding['public_key'])
        if previous is not None and previous!=node:raise ValueError('Signing key is shared with '+previous)
        seen[binding['public_key']]=node
    for entry in entries:
        node = entry['node_id']
        public = pair(directory / 'nodes' / node, 'auth')
        previous=seen.get(public.hex())
        if previous is not None and previous!=node:raise ValueError('Signing key is shared with '+previous)
        seen[public.hex()]=node
        binding = dict(root_id=entry.get('root_id','ugv-root'),role=entry['role'],public_key=public.hex(),
                       certificate_sha256=fingerprints[node])
        if node in record['nodes'] and record['nodes'][node] != binding:
            raise ValueError('Existing parent-auth enrollment differs: '+node)
        record['nodes'][node] = binding
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    temporary.replace(path)
    return dict(nodes=len(record['nodes']),authority_sha256=hashlib.sha256(authority).hexdigest(),
                directory=str(directory),tls_credentials='unchanged',
                skipped=[e['node_id'] for e in data['nodes'] if e not in entries])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--node-id',action='append',help='Explicit enrolled devices; default selects enabled trusted nodes')
    args=parser.parse_args()
    try:print(json.dumps(provision(args.root,args.node_id)))
    except (ValueError,OSError) as exc:parser.error(str(exc))
