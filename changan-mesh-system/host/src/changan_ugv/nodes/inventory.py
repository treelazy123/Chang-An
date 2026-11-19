"""Public, administrator-controlled device inventory; never learns authorization from MQTT messages."""
from changan_ugv.paths import repository_root
import json
from pathlib import Path
import re
ROLES=('ugv_root','ugv','uav','micro_uav')
DEFAULT_IDS=dict(zip(ROLES,('ugv-root','ugv-001','uav-001','micro-001')))
RESERVED={'controller-001','ugv-broker.lab'}
def valid_id(value):
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,32}',value):
        raise ValueError('Node ID must contain 1-32 ASCII letters, digits, dash or underscore')
    if value.casefold() in {x.casefold() for x in RESERVED} or re.fullmatch(r'(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])',value):
        raise ValueError('Reserved node ID: '+value)
    return value

def defaults():
    subnets={'ugv_root':5,'ugv':6,'uav':8,'micro_uav':None}
    return {'schema':2,'nodes':[{'node_id':DEFAULT_IDS[role],'role':role,'root_id':'ugv-root','enabled':True,
                               'ap_subnet':subnets[role]}
                               for role in ROLES]}

def root_of(entry):
    return entry.get('root_id','ugv-root')

def is_gateway(entry):
    return entry['role']=='ugv_root'

def authorized(entry):
    return entry.get('enabled',True) and entry.get('trust_status','trusted')=='trusted'
def validate(data):
    if not isinstance(data,dict) or data.get('schema')!=2 or not isinstance(data.get('nodes'),list):
        raise ValueError('Expected node inventory schema=2 and nodes array')
    seen=set();subnets={}
    for entry in data['nodes']:
        if not isinstance(entry,dict):raise ValueError('Invalid node entry')
        node=valid_id(entry.get('node_id'))
        if node.casefold() in seen:raise ValueError('Duplicate/case-conflicting node ID: '+node)
        seen.add(node.casefold())
        if entry.get('role')=='micro_uav' and entry.get('ap_subnet') is not None:
            raise ValueError('STA-only micro_uav must have ap_subnet=null: '+node)
        if 'ap_subnet' in entry and not (entry.get('role')=='micro_uav' and entry['ap_subnet'] is None):
            subnet=entry['ap_subnet']
            if type(subnet) is not int or not 4<=subnet<=254:
                raise ValueError('ap_subnet must be an integer in 4..254: '+node)
            if subnet in subnets:
                raise ValueError(f'Duplicate AP subnet 192.168.{subnet}.0/24: {subnets[subnet]} and {node}')
            subnets[subnet]=node
        if entry.get('role') not in ROLES:raise ValueError('Invalid role for '+node)
        if 'credential_id' in entry or 'ugv_id' in entry:raise ValueError('Use root_id; aliases are not node identities')
        if type(entry.get('enabled',True)) is not bool:raise ValueError('enabled must be boolean')
        if entry.get('trust_status','trusted') not in ('pending','trusted','revoked'):
            raise ValueError('Invalid trust status')
        revision=entry.get('admission_revision',0)
        if type(revision) is not int or revision<0:raise ValueError('Invalid admission revision')
        valid_id(root_of(entry))
        valid_id(entry.get('root_id'))
        if entry['role']=='ugv_root' and root_of(entry)!=node:
            raise ValueError('Root must own its identity')
    if data['schema']==2:
        roots={e['node_id'] for e in data['nodes'] if e['role']=='ugv_root' and e.get('enabled',True)}
        for entry in data['nodes']:
            if entry.get('enabled',True) and root_of(entry) not in roots:
                raise ValueError('Enabled node must belong to an enabled root')
    return data

def next_ap_subnet(data):
    """Reserve across the whole inventory, including disabled/revoked devices."""
    used={e['ap_subnet'] for e in validate(data)['nodes'] if 'ap_subnet' in e}
    for subnet in range(10,255):
        if subnet not in used:return subnet
    raise ValueError('AP subnet pool exhausted (192.168.10.0/24 through 192.168.254.0/24)')

def assign_ap_subnets(data):
    """Administrative migration only; persist the result, never allocate on read."""
    validate(data)
    missing=[e for e in data['nodes'] if 'ap_subnet' not in e and e['role']!='micro_uav']
    used={e.get('ap_subnet') for e in data['nodes']}
    free=[n for n in range(10,255) if n not in used]
    if len(missing)>len(free):raise ValueError('AP subnet pool exhausted')
    for entry,subnet in zip(missing,free):entry['ap_subnet']=subnet
    for entry in data['nodes']:
        if entry['role']=='micro_uav':entry['ap_subnet']=None
    return validate(data)

def load_inventory(root=None, *, path=None):
    explicit=path is not None
    root=Path(root) if root is not None else repository_root()
    path=Path(path) if path is not None else root/'config/nodes.json'
    if explicit and not path.is_file():raise FileNotFoundError(path)
    return validate(json.loads(path.read_text(encoding='utf-8')) if path.exists() else defaults())
def clients(data):
    return tuple(e['node_id'] for e in validate(data)['nodes'] if authorized(e) and not is_gateway(e))
def write_inventory(root,data):
    path=Path(root)/'config/nodes.json';path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix('.json.tmp');temp.write_text(json.dumps(validate(data),ensure_ascii=False,indent=2)+'\n',encoding='utf-8');temp.replace(path)
def render_acl(data):
    rows=['# Generated from config/nodes.json by provision_mqtt.py; edit the inventory instead.']
    for node in clients(data):
        rows+=['user '+node]
        rows += [f'topic write mesh/v1/nodes/{node}/{s}' for s in ('presence','capabilities','telemetry','acks','task_events','image')]
        rows += [f'topic read mesh/v1/nodes/{node}/commands',f'topic read mesh/v1/nodes/{node}/task_commands','topic read mesh/v1/clock']
        rows += ['']
    rows += ['user controller-001']
    rows += [f'topic read mesh/v1/nodes/+/{s}' for s in ('presence','capabilities','telemetry','acks','task_events','image')]
    rows += ['topic write mesh/v1/clock']
    rows += [f'topic write mesh/v1/nodes/{node}/commands' for node in clients(data)]
    rows += [f'topic write mesh/v1/nodes/{node}/task_commands' for node in clients(data)]
    return '\n'.join(rows)+'\n'

def write_acl(root,data):
    path=Path(root)/'runtime/ugv-root/acl.conf';path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix('.conf.tmp');temp.write_text(render_acl(data),encoding='utf-8');temp.replace(path)
