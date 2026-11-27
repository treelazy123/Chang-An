"""Wire MCI binding; legacy view models stay private to this terminal."""
import re

ALIASES={'duration_s':'durationSeconds','stale_after_s':'staleAfterSeconds',
 'point_duration_s':'pointDurationSeconds','probe_node':'probeNodeId','parent':'parentNodeId'}
def transform(value,to_mci=True):
    aliases=ALIASES if to_mci else {v:k for k,v in ALIASES.items()}
    def key(k):
        if k in aliases:return aliases[k]
        return re.sub(r'_([a-z])',lambda m:m[1].upper(),k) if to_mci else re.sub(r'(?<!^)(?=[A-Z])','_',k).lower()
    if isinstance(value,dict):return {key(k):transform(v,to_mci) for k,v in value.items()}
    if isinstance(value,list):return [transform(v,to_mci) for v in value]
    return value

def envelope(packet):
    kind=packet['type'];params={k:v for k,v in packet.items() if k not in ('v','type','node_id','msg_id','deadline_unix')}
    target=None
    if kind=='list':
        service='Mesh_Node';method='Get_ServiceInstances' if params.pop('scope','nodes')=='services' else 'Get_NodeList'
    elif kind=='command':
        service='Mesh_Node';method={'ping':'Cnr_Ping','status':'Get_Status','echo':'Cnr_Echo'}[params.pop('op')]
        target=params.pop('target')
        if 'payload' in params:params['text']=params.pop('payload')
    elif kind=='node.admission':
        service='Mesh_Admission';method='Cnr_SetTrustStatus';target=params.pop('target')
    elif kind.startswith('node.parent'):
        service='Mesh_Parent';method='Get_Policy' if kind.endswith('.get') else 'Cnr_SetPolicy';target=params.pop('target')
    else:
        service='Mesh_Task'
        if kind=='task.control':
            op=params.pop('op');method='Cnr_'+({'delete':'DeleteTaskHistory'}.get(op,op.title()+'Task'))
        elif kind=='task.events':method='Get_TestIncidents' if params.pop('scope','tasks')=='incidents' else 'Get_TaskEvents'
        else:method={'task.create':'Cnr_CreateTask','task.update':'Cnr_UpdateTask','task.get':'Get_Task','task.list':'Get_TaskList'}[kind]
        if kind=='task.create':params['executorNodeId']=params.pop('target')
    body=dict(service=service,method=method,params=transform(params),requestId=packet['msg_id'],deadlineUnix=packet['deadline_unix'])
    if target is not None:body['target']=target
    return body

def legacy_response(packet,wire):
    base=dict(v=1,msg_id=packet['msg_id'],node_id='ugv-service')
    if 'error' in wire:return dict(base,type='error',error=wire['error']['code']+': '+wire['error']['message'])
    result=transform(wire['result'],False);kind=packet['type']
    if kind=='list':return dict(base,type='nodes',nodes=result.get('nodes',result.get('instances',[])),more=False)
    if kind=='command':return dict(base,type='ack',ok=True,target=packet['target'],op=packet['op'],payload=result.get('text') if packet['op']=='echo' else result,node_id=packet['target'])
    if kind.startswith('node.parent'):return dict(base,**result,type='node.parent.reply',target=packet['target'],ok=True)
    if kind=='node.admission':return dict(base,**result,type='node.admission.reply',node_id=packet['target'],ok=True)
    return dict(base,**result,type='task.reply',ok=True)

def legacy_event(body):
    payload=transform(body['params'],False)
    if 'cursor' in body:payload['cursor']=body['cursor']
    method=body['method']
    return dict(payload,type={'Ntf_TaskChanged':'task.event','Ntf_NodeSnapshot':'nodes.snapshot','Et_TestIncident':'test.incident'}[method])
