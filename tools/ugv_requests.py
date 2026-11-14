"""Bounded UGV request contract shared by authenticated MQTT terminals and local compatibility UI."""
from collections import OrderedDict
import json
import re
import threading
import time
from mesh_protocol import encode
from node_inventory import load_inventory
from task_store import ACTIONS
class Requests:
    def __init__(self,controller,root,clock=time.time):
        self.controller=controller;self.root=root;self.clock=clock
        self.lock=threading.Lock();self.cache=OrderedDict()
    def allowed(self,source):
        return any(e['node_id']==source and e['role']=='pc_root' and e.get('enabled',True)
                   for e in load_inventory(self.root)['nodes'])
    def error(self,request,text):
        return {'v':1,'type':'error','node_id':'ugv-service','msg_id':request.get('msg_id'),
                'target':request.get('target'),'error':text}
    def handle(self,request,source=None):
        identity=request.get('msg_id') if isinstance(request,dict) else None
        if not isinstance(identity,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',identity):
            return [self.error({},'invalid_msg_id')]
        if source is not None:
            try:authorized=self.allowed(source) and request.get('node_id')==source
            except (ValueError,OSError):authorized=False
            if not authorized:return [self.error(request,'terminal_not_authorized')]
        deadline=request.get('deadline_unix')
        if type(deadline) not in (int,float) or not self.clock()<=deadline<=self.clock()+60:
            return [self.error(request,'expired_or_invalid_deadline')]
        if not isinstance(request.get('type'),str) or type(request.get('v')) is not int or request.get('v')!=1 or request.get('type') not in ({'list','command'} | ACTIONS):
            return [self.error(request,'invalid_request')]
        if len(json.dumps(request,ensure_ascii=False,separators=(',',':')).encode())>512:
            return [self.error(request,'request_too_large')]
        if request['type'] in ACTIONS:
            try:
                tasks=getattr(self.controller,'tasks',None)
                if tasks is None:raise ValueError('task_service_not_available')
                return [tasks.handle(request,source or 'local-console')]
            except (ValueError,OSError) as exc:return [self.error(request,str(exc))]
        if request['type']=='command':
            target=request.get('target');op=request.get('op')
            if not isinstance(target,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,32}',target) or op not in ('ping','status','echo'):
                return [self.error(request,'invalid_command')]
            if op=='echo' and not isinstance(request.get('payload',''),str):
                return [self.error(request,'invalid_echo_payload')]
        canonical=json.dumps(request,sort_keys=True,separators=(',',':'),ensure_ascii=False)
        key=(source or 'local-console',identity)
        # One dispatch lock also serializes duplicate requests until the first result is cached.
        with self.lock:
            if key in self.cache:
                original,result=self.cache[key]
                return result if original==canonical else [self.error(request,'msg_id_conflict')]
            try:
                if not self.controller.connected.is_set():raise ConnectionError('broker_offline')
                if request['type']=='list':
                    self.controller.refresh_inventory()
                    with self.controller.condition:rows=self.controller.registry.snapshot()
                    tasks=getattr(self.controller,'tasks',None)
                    if tasks is not None:
                        rows.append(dict(node_id=tasks.ugv_id,ready=self.controller.connected.is_set(),operations=[],
                                         task_types=['diagnostics'],status=dict(role='ugv',execution_host='local')))
                    # One node per frame, final marker: fits the C6 1024-byte frame bound for growing fleets.
                    result=[dict(v=1,type='nodes',node_id='ugv-service',msg_id=identity,nodes=[row],more=True) for row in rows]
                    result.append(dict(v=1,type='nodes',node_id='ugv-service',msg_id=identity,nodes=[],more=False))
                else:
                    node=request.get('target');op=request.get('op')
                    result=[self.controller.command(node,op,request.get('payload'),
                             timeout=min(10,max(.1,deadline-self.clock())),msg_id=identity,deadline_unix=deadline)]
                for row in result:encode(row)
            except (ValueError,OSError,TimeoutError) as exc:result=[self.error(request,str(exc))]
            self.cache[key]=(canonical,result)
            while len(self.cache)>64:self.cache.popitem(last=False)
            return result
