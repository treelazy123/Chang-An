"""Authenticated local UGV controller: clock, fixed device registry, list/ping/status/echo."""
import argparse
import json
import logging
import re
from pathlib import Path
import shlex
import ssl
import threading
import time
import uuid
from changan_ugv.protocol.frames import _unique_object
from changan_ugv.config import BrokerConfig
from changan_ugv.nodes.inventory import load_inventory, clients
from changan_ugv.tasks.workflows import WORKFLOW_ROLES, MODE
NODES = clients(load_inventory())
OPERATIONS = ('ping', 'status', 'echo')
class BrokerTLSContext(ssl.SSLContext):
    """Connect to loopback while verifying the fixed broker service identity."""
    def __new__(cls, protocol=ssl.PROTOCOL_TLS_CLIENT, *, server_name='ugv-broker.lab'):
        context=super().__new__(cls,protocol)
        context.server_name=server_name
        return context
    def __init__(self, protocol=ssl.PROTOCOL_TLS_CLIENT, *, server_name='ugv-broker.lab'):
        pass
    def wrap_socket(self, *args, server_hostname=None, **kwargs):
        return super().wrap_socket(*args, server_hostname=self.server_name, **kwargs)
class Registry:
    def __init__(self, clock=time.monotonic, nodes=None):
        self.clock=clock
        self.allowed=tuple(nodes) if nodes is not None else clients(load_inventory())
        self.nodes={n: {} for n in self.allowed}
    def receive(self, topic, body, retained=False):
        parts=topic.split('/')
        if len(parts)!=5 or parts[:3]!=['mesh','v1','nodes'] or parts[3] not in self.nodes:
            return False
        node,kind=parts[3:]
        if not isinstance(body,dict) or body.get('v')!=1 or body.get('node_id')!=node:
            return False
        entry=self.nodes[node]
        if kind=='presence' and body.get('type')=='presence' and type(body.get('online')) is bool:
            entry['presence']=body
        elif kind=='capabilities' and body.get('type')=='capabilities':
            if 'task_status' in body and body['task_status'] not in ('IDLE','ACCEPTED','RUNNING','PAUSED','UNKNOWN','SUCCEEDED','FAILED','CANCELLED','REJECTED'):
                return False
            if 'task_id' in body and (not isinstance(body['task_id'],str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,32}',body['task_id'])):
                return False
            ops=body.get('operations')
            if not isinstance(ops,list) or not ops or any(op not in OPERATIONS for op in ops):
                return False
            tasks=body.get('task_types',[])
            if not isinstance(tasks,list) or any(t not in ('diagnostics',*WORKFLOW_ROLES) for t in tasks):return False
            for task in tasks:
                if task in WORKFLOW_ROLES and (body.get('task_role')!=WORKFLOW_ROLES[task] or body.get('execution_mode')!=MODE):
                    return False
            if any(t in WORKFLOW_ROLES for t in tasks):
                task_ops=body.get('task_operations')
                if not isinstance(task_ops,list) or any(not isinstance(op,str) for op in task_ops) or set(task_ops)!={'start','pause','resume','cancel','query'}:return False
            entry['capabilities']=body
        elif kind=='telemetry' and body.get('type')=='telemetry' and not retained:
            entry['telemetry']=body
            entry['last_seen']=self.clock()
        else:
            return False
        return True
    def reconcile(self,nodes):
        allowed=tuple(nodes)
        added=tuple(n for n in allowed if n not in self.nodes)
        self.nodes={n:self.nodes.get(n,{}) for n in allowed}
        self.allowed=allowed
        return added
    def ready(self,node):
        entry=self.nodes.get(node,{})
        presence=entry.get('presence',{})
        cap=entry.get('capabilities',{})
        telemetry=entry.get('telemetry',{})
        boot=presence.get('boot_id')
        return bool(presence.get('online') and boot and cap.get('boot_id')==boot and
                    telemetry.get('boot_id')==boot and self.clock()-entry.get('last_seen',-1000)<20)
    def snapshot(self):
        return [{'node_id':n,'ready':self.ready(n),
                 'online':e.get('presence',{}).get('online'),
                 'status_age_s':round(max(0,self.clock()-e['last_seen']),1) if 'last_seen' in e else None,
                 'status_current_boot':bool(e.get('presence',{}).get('boot_id') and
                     e.get('presence',{}).get('boot_id')==e.get('telemetry',{}).get('boot_id')),
                 'operations':e.get('capabilities',{}).get('operations',[]),
                 'status':e.get('telemetry',{}).get('payload'),
                 'task_types':e.get('capabilities',{}).get('task_types',[])} for n,e in self.nodes.items()]
class Controller:
    def __init__(self,secret=None,port=8883,inventory=None,inventory_path=None, *, broker=None,lock_file=None):
        from changan_ugv.nodes.lease import Lease
        broker=broker or BrokerConfig.from_secrets(secret,port)
        self.instance_lease=Lease(secret or broker.ca_file.parent,lock_file=lock_file)
        try:
            import paho.mqtt.client as mqtt
            self.registry=Registry(nodes=clients(inventory) if inventory is not None else None)
            self.inventory_path=Path(inventory_path) if inventory_path is not None else None
            self.inventory_text=None
            self.inventory_error=None
            self.condition=threading.Condition()
            self.replies={}
            self.pending={}
            self.connected=threading.Event()
            self.stopped=threading.Event()
            context=BrokerTLSContext(ssl.PROTOCOL_TLS_CLIENT,server_name=broker.endpoint.server_name)
            context.minimum_version=ssl.TLSVersion.TLSv1_2
            context.load_verify_locations(str(broker.ca_file))
            context.load_cert_chain(str(broker.client_cert),str(broker.client_key))
            self.client=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,client_id='controller-001',clean_session=True)
            self.client.tls_set_context(context)
            self.client.on_connect=self.on_connect
            self.client.on_subscribe=self.on_subscribe
            self.client.on_disconnect=self.on_disconnect
            self.client.on_message=self.on_message
            self.client.connect(broker.endpoint.host,broker.endpoint.port,15)
            self.client.loop_start()
            if not self.connected.wait(10):
                self.close()
                raise TimeoutError('Broker authentication/subscription did not complete')
            self.clock_thread=threading.Thread(target=self.clock_loop,daemon=True)
            self.clock_thread.start()
        except BaseException:
            self.instance_lease.close()
            raise
    def refresh_inventory(self):
        path=getattr(self,'inventory_path',None)
        if path is None:return
        try:
            text=path.read_text(encoding='utf-8')
            if text==self.inventory_text:return
            from changan_ugv.nodes.inventory import validate
            allowed=clients(validate(json.loads(text)))
            with self.condition:
                added=self.registry.reconcile(allowed)
                self.inventory_text=text
                self.inventory_error=None
            if added and self.connected.is_set():
                # Recover retained registration sent before the controller saw the new inventory.
                self.client.subscribe([(f'mesh/v1/nodes/{n}/{suffix}',1)
                                       for n in added for suffix in ('presence','capabilities')])
        except (OSError,ValueError) as exc:
            error=str(exc)
            if error!=self.inventory_error:
                logging.getLogger(__name__).warning('Inventory reload rejected; no new authorization: %s',error)
                self.inventory_error=error
    def on_connect(self,client,userdata,flags,reason,properties):
        if not reason.is_failure:
            client.subscribe([(f'mesh/v1/nodes/+/{s}',1) for s in ('presence','capabilities','telemetry','acks')])
    def on_subscribe(self,client,userdata,mid,reasons,properties):
        if reasons and all(not reason.is_failure for reason in reasons):
            self.connected.set()
    def on_disconnect(self,client,userdata,flags,reason,properties):
        self.connected.clear()
        with self.condition:
            self.registry=Registry(nodes=self.registry.allowed)
            self.condition.notify_all()
    def on_message(self,client,userdata,message):
        self.refresh_inventory()
        try:
            if len(message.payload)>2048:
                return
            body=json.loads(message.payload.decode('utf-8'),object_pairs_hook=_unique_object,
                            parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Non-finite JSON')))
            if not isinstance(body,dict):
                return
            with self.condition:
                parts=message.topic.split('/')
                msg_id=body.get('msg_id')
                if len(parts)==5 and parts[:3]==['mesh','v1','nodes'] and parts[4]=='acks':
                    if (not message.retain and body.get('v')==1 and body.get('type')=='ack' and
                        self.pending.get(msg_id)==parts[3]==body.get('node_id')):
                        self.replies[msg_id]=body
                else:
                    self.registry.receive(message.topic,body,message.retain)
                self.condition.notify_all()
        except (ValueError,UnicodeError,TypeError):
            return
    def clock_loop(self):
        while not self.stopped.is_set():
            self.refresh_inventory()
            if self.connected.is_set():
                self.client.publish('mesh/v1/clock',json.dumps({'unix':int(time.time())}),qos=1,retain=True)
            self.stopped.wait(5)
    def command(self,node,op,text=None,timeout=10,msg_id=None,deadline_unix=None):
        if node not in self.registry.nodes or op not in OPERATIONS:
            raise ValueError('Unknown node or operation')
        msg_id=msg_id or uuid.uuid4().hex
        packet={'v':1,'type':'command','target':node,'msg_id':msg_id,'op':op,'deadline_unix':deadline_unix or int(time.time())+20}
        if op=='echo': packet['payload']=text or ''
        payload=json.dumps(packet,ensure_ascii=False,separators=(',',':'))
        if len(payload.encode('utf-8'))>512:
            raise ValueError('Command exceeds 512 UTF-8 bytes')
        with self.condition:
            if not self.connected.is_set() or not self.registry.ready(node):
                raise ValueError('Node is not ready: wait for presence, approved capabilities and fresh telemetry')
            if op not in self.registry.nodes[node]['capabilities']['operations']:
                raise ValueError('Node did not register this operation')
            if msg_id in self.pending:raise ValueError('msg_id is already pending')
            self.pending[msg_id]=node
            try:
                info=self.client.publish(f'mesh/v1/nodes/{node}/commands',payload,qos=1,retain=False)
                if info.rc:
                    raise OSError('MQTT publish failed')
                deadline=time.monotonic()+timeout
                while msg_id not in self.replies:
                    if not self.connected.is_set(): raise ConnectionError('Broker disconnected')
                    remaining=deadline-time.monotonic()
                    if remaining<=0: raise TimeoutError('No application ACK; command is not retried')
                    self.condition.wait(remaining)
                return self.replies.pop(msg_id)
            finally:
                self.pending.pop(msg_id,None)
    def close(self):
        self.stopped.set()
        self.client.disconnect()
        self.client.loop_stop()
        thread=getattr(self,'clock_thread',None)
        if thread: thread.join(timeout=2)
        lease=getattr(self,"instance_lease",None)
        if lease:lease.close()
