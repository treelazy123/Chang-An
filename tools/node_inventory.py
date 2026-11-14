"""Public, administrator-controlled device inventory; never learns authorization from MQTT messages."""
import json
from pathlib import Path
import re
ROLES=('pc_root','ugv','uav','micro_uav')
DEFAULT_IDS=dict(zip(ROLES,('pc-root-001','ugv-001','uav-001','micro-001')))
RESERVED={'controller-001','ugv-broker.lab'}
def valid_id(value):
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,32}',value):
        raise ValueError('Node ID must contain 1-32 ASCII letters, digits, dash or underscore')
    if value.casefold() in {x.casefold() for x in RESERVED} or re.fullmatch(r'(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])',value):
        raise ValueError('Reserved node ID: '+value)
    return value

def defaults():
    return {'schema':1,'nodes':[{'node_id':node,'role':role,'ugv_id':'ugv-001','enabled':True}
                               for role,node in DEFAULT_IDS.items()]}
def validate(data):
    if not isinstance(data,dict) or data.get('schema')!=1 or not isinstance(data.get('nodes'),list):
        raise ValueError('Expected node inventory schema=1 and nodes array')
    seen=set()
    for entry in data['nodes']:
        if not isinstance(entry,dict):raise ValueError('Invalid node entry')
        node=valid_id(entry.get('node_id'))
        if node.casefold() in seen:raise ValueError('Duplicate/case-conflicting node ID: '+node)
        seen.add(node.casefold())
        if entry.get('role') not in ROLES:raise ValueError('Invalid role for '+node)
        if type(entry.get('enabled',True)) is not bool:raise ValueError('enabled must be boolean')
        valid_id(entry.get('ugv_id','ugv-001'))
        if entry['role']=='ugv' and entry.get('ugv_id',node)!=node:
            raise ValueError('UGV must advertise its own identity')
    return data

def load_inventory(root=None):
    root=Path(root) if root is not None else Path(__file__).resolve().parents[1]
    path=root/'host/config/nodes.json'
    return validate(json.loads(path.read_text(encoding='utf-8')) if path.exists() else defaults())
def clients(data):
    return tuple(e['node_id'] for e in validate(data)['nodes'] if e.get('enabled',True) and e['role']!='ugv')
def write_inventory(root,data):
    path=Path(root)/'host/config/nodes.json';path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix('.json.tmp');temp.write_text(json.dumps(validate(data),ensure_ascii=False,indent=2)+'\n',encoding='utf-8');temp.replace(path)
def write_acl(root,data):
    rows=['# Generated from host/config/nodes.json by provision_mqtt.py; edit the inventory instead.']
    for node in clients(data):
        rows+=['user '+node]
        rows += [f'topic write mesh/v1/nodes/{node}/{s}' for s in ('presence','capabilities','telemetry','acks','task_events')]
        rows += [f'topic read mesh/v1/nodes/{node}/commands',f'topic read mesh/v1/nodes/{node}/task_commands','topic read mesh/v1/clock']
        role=next(e['role'] for e in data['nodes'] if e['node_id']==node)
        if role=='pc_root':
            rows += [f'topic write mesh/v1/terminals/{node}/requests',f'topic read mesh/v1/terminals/{node}/responses',f'topic read mesh/v1/terminals/{node}/events']
        rows += ['']
    rows += ['user controller-001']
    rows += [f'topic read mesh/v1/nodes/+/{s}' for s in ('presence','capabilities','telemetry','acks','task_events')]
    rows += ['topic write mesh/v1/clock','topic read mesh/v1/terminals/+/requests','topic write mesh/v1/terminals/+/responses','topic write mesh/v1/terminals/+/events']
    rows += [f'topic write mesh/v1/nodes/{node}/commands' for node in clients(data)]
    rows += [f'topic write mesh/v1/nodes/{node}/task_commands' for node in clients(data)]
    path=Path(root)/'host/runtime/acl.conf';path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix('.conf.tmp');temp.write_text('\n'.join(rows)+'\n',encoding='utf-8');temp.replace(path)
