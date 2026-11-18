"""Bounded UGV request contract shared by authenticated MQTT terminals and local compatibility UI."""
from collections import OrderedDict
import json
import re
import threading
import time
from changan_ugv.protocol.messages import encode
from changan_ugv.nodes.inventory import load_inventory,root_of
from changan_ugv.nodes.network import read_network_status
from changan_ugv.tasks.store import ACTIONS
class Requests:
    def __init__(self,controller,root=None,clock=time.time, *, inventory_loader=None, local_owner='http-local'):
        self.controller=controller;self.root=root;self.clock=clock
        self.lock=threading.Lock();self.cache=OrderedDict()
        self.inventory_loader=inventory_loader or (lambda:load_inventory(self.root))
        self.local_owner=local_owner
    def error(self,request,text):
        return {'v':1,'type':'error','node_id':'ugv-service','msg_id':request.get('msg_id'),
                'target':request.get('target'),'error':text}
    def handle(self,request, *, local=True):
        if not isinstance(request,dict):return [self.error({},'invalid_request')]
        if not local:return [self.error(request,'http_transport_required')]
        source=self.local_owner
        request=dict(request,node_id=source)
        identity=request.get('msg_id') if isinstance(request,dict) else None
        if not isinstance(identity,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',identity):
            return [self.error({},'invalid_msg_id')]
        deadline=request.get('deadline_unix')
        if type(deadline) not in (int,float) or not self.clock()<=deadline<=self.clock()+60:
            return [self.error(request,'expired_or_invalid_deadline')]
        supported={'list','command','node.parent','node.parent.get'}|ACTIONS|({'node.admission'} if local else set())
        if not isinstance(request.get('type'),str) or type(request.get('v')) is not int or request.get('v')!=1 or request.get('type') not in supported:
            return [self.error(request,'invalid_request')]
        if len(json.dumps(request,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode())>(16384 if local else 512):
            return [self.error(request,'request_too_large')]
        if request['type'] in ('node.parent','node.parent.get'):
            try:
                manager=self.controller.parents
                result=manager.change(request) if request['type']=='node.parent' else manager.get(request.get('target'))
                return [dict(v=1,type='node.parent.reply',msg_id=identity,ok=True,**result)]
            except (ValueError,OSError) as exc:return [self.error(request,str(exc))]
        if request['type']=='node.admission':
            try:
                result=self.controller.admission.change(request)
                self.controller.refresh_inventory()
                return [dict(v=1,type='node.admission.reply',msg_id=identity,ok=True,**result)]
            except (ValueError,OSError) as exc:return [self.error(request,str(exc))]
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
                    scope=request.get('scope','nodes')
                    if scope not in ('nodes','services'):raise ValueError('invalid_list_scope')
                    self.controller.refresh_inventory()
                    with self.controller.condition:rows=self.controller.registry.snapshot()
                    tasks=getattr(self.controller,'tasks',None)
                    if tasks is not None:
                        registration={e['node_id']:e for e in self.inventory_loader()['nodes'] if root_of(e)==tasks.ugv_id}
                        present={row['node_id'] for row in rows}
                        if local:
                            for node_id,entry in registration.items():
                                if node_id!=tasks.ugv_id and node_id not in present:
                                    rows.append(dict(node_id=node_id,ready=False,online=None,operations=[],task_types=[],status=None))
                            for row in rows:
                                entry=registration.get(row['node_id'],{})
                                row.update(role=entry.get('role'),root_id=root_of(entry),
                                           trust_status=entry.get('trust_status','trusted'),enabled=entry.get('enabled',True),
                                           admission_revision=entry.get('admission_revision',0))
                                if not entry.get('enabled',True) or entry.get('trust_status','trusted')!='trusted':row['ready']=False
                                if entry.get('role')=='micro_uav' and hasattr(self.controller,'parents'):
                                    row['parent_policy']=self.controller.parents.get(row['node_id'])
                        entry=next((e for e in self.inventory_loader()['nodes'] if e['node_id']==tasks.ugv_id),{})
                        ugv_status=dict(role=entry.get('role','ugv'),execution_host='local')
                        network=read_network_status(tasks.ugv_id,self.root)
                        if network is not None:ugv_status['network_status']=network
                        rows.append(dict(node_id=tasks.ugv_id,ready=self.controller.connected.is_set(),operations=[],
                                         task_types=['diagnostics',*getattr(getattr(tasks,'local',None),'concurrent_kinds',())],status=ugv_status))
                        if local:rows[-1].update(role=entry.get('role','ugv'),root_id=tasks.ugv_id)
                    if scope == 'services':
                        rows=tasks.service_snapshot(source or 'local-console') if tasks is not None else []
                    # One node per frame, final marker: fits the C6 1024-byte frame bound for growing fleets.
                    result=[dict(v=1,type='nodes',node_id='ugv-service',msg_id=identity,nodes=[row],more=True) for row in rows]
                    result.append(dict(v=1,type='nodes',node_id='ugv-service',msg_id=identity,nodes=[],more=False))
                else:
                    node=request.get('target');op=request.get('op')
                    result=[self.controller.command(node,op,request.get('payload'),
                             timeout=min(10,max(.1,deadline-self.clock())),msg_id=identity,deadline_unix=deadline)]
                if not local:
                    for row in result:encode(row)
            except (ValueError,OSError,TimeoutError) as exc:result=[self.error(request,str(exc))]
            self.cache[key]=(canonical,result)
            while len(self.cache)>64:self.cache.popitem(last=False)
            return result
