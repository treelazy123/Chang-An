"""Headless UGV manager with persistent generic M1 tasks; no scenario-specific APIs."""
from changan_ugv.paths import repository_root
import argparse
import json
import logging
from pathlib import Path
import queue
import threading
import time
from concurrent.futures import Future
from dataclasses import dataclass
from changan_ugv.nodes.catalog import NodeCatalog
from changan_ugv.nodes.admission import AdmissionManager
from changan_ugv.nodes.parent_policy import ParentPolicies
from changan_ugv.nodes.parent_authority import ParentAuthority
from changan_ugv.nodes.capability_measurements import CapabilityMeasurements
from changan_ugv.nodes.inventory import root_of
from changan_ugv.nodes.controller import Controller
from changan_ugv.protocol.messages import _unique_object, encode
from changan_ugv.nodes.inventory import load_inventory
from changan_ugv.tasks.store import ACTIONS
from changan_ugv.tasks.runtime import Runtime
from changan_ugv.config import ServicePaths, service_arguments, resolve_arguments
from changan_ugv.agents.services import HostServices
from changan_ugv.transport.node_channel import MQTTNodeChannel
from changan_ugv.service.requests import Requests

@dataclass
class LocalCall:
    packet: dict
    result: Future

class ServiceController(Controller):
    def __init__(self,*args,root=None,paths=None,ugv_id='ugv-root',database=None,executor_factory=None,channel_factory=MQTTNodeChannel,**kwargs):
        paths=paths or ServicePaths.from_root(root)
        inventory_loader=lambda:load_inventory(path=paths.inventory_file)
        self.inbox=queue.Queue(16)
        self.task_inbox=queue.Queue(16)
        self.task_feedback=queue.Queue(128)
        self.parent_auth_inbox=queue.Queue(32)
        self.parent_auth_denied_at={}
        self.capability_inbox=queue.Queue(256)
        self.tasks=None
        self.requests=Requests(self,inventory_loader=inventory_loader)
        from changan_ugv.nodes.image_sink import ImageSink
        super().__init__(*args,managed_root_id=ugv_id,image_sink=ImageSink(paths.image_dir),**kwargs)
        try:
            factory=executor_factory or (lambda emit,snapshot:HostServices(
                paths.agent_journal,ugv_id,emit,snapshot,probe=self.command,network_snapshot=self.network_snapshot))
            self.tasks=Runtime(channel_factory(self),database=database or paths.task_database,
                               executor_factory=factory,inventory_loader=inventory_loader,ugv_id=ugv_id,operators=('http-local',))
            self.catalog=NodeCatalog(self.tasks.store)
            self.capability_measurements=CapabilityMeasurements(self.tasks.store,self.capability_node_info,self.send_capability_packet)
            self.parents=ParentPolicies(self.tasks.store,self,inventory_loader,ugv_id)
            self.admission=AdmissionManager(self.tasks.store,paths.inventory_file,ugv_id,
                self.broker_config.ca_file,self.broker_config.ca_file.parent,
                paths.task_database.parent/'acl.pending.conf')
            self.parent_authority=ParentAuthority(self.broker_config.ca_file.parent/'parent-auth',
                inventory_loader,ugv_id,certificate=self.admission.certificate)
            self.requests=Requests(self,inventory_loader=inventory_loader)
            self.workers=[threading.Thread(target=self.request_loop,args=(inbox,),daemon=True)
                          for inbox in (self.inbox,self.task_inbox)]
            self.workers.append(threading.Thread(target=self.task_loop,daemon=True))
            self.workers.append(threading.Thread(target=self.parent_auth_loop,daemon=True))
            for worker in self.workers:worker.start()
        except BaseException:
            super().close()
            if self.tasks:self.tasks.close()
            raise

    def on_connect(self,client,userdata,flags,reason,properties):
        super().on_connect(client,userdata,flags,reason,properties)
        if not reason.is_failure:
            client.subscribe([('mesh/v1/nodes/+/task_events',1)])

    def network_snapshot(self, node):
        with self.condition:
            if node not in self.registry.nodes:
                return None
            return dict(ready=self.registry.ready(node))

    def on_message(self,client,userdata,message):
        parts=message.topic.split('/')
        if (len(parts)==5 and parts[:3]==['mesh','v1','nodes'] and parts[4]=='telemetry'
                and not message.retain and len(message.payload)<=512):
            try:
                packet=json.loads(message.payload.decode('utf-8'),object_pairs_hook=_unique_object,
                    parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Non-finite JSON')))
                if isinstance(packet,dict) and packet.get('type')=='cap.result':
                    self.capability_inbox.put_nowait(('result',parts[3],packet,False,time.time(),None))
                    return
                if isinstance(packet,dict) and packet.get('type')=='parent.auth.request':
                    self.parent_auth_inbox.put_nowait((time.monotonic(),parts[3],packet))
                    return
            except (ValueError,UnicodeError,queue.Full):return
        if len(parts)!=5 or parts[:3]!=['mesh','v1','nodes'] or parts[4]!='task_events':
            return super().on_message(client,userdata,message)
        if message.retain or len(message.payload)>1024:return
        try:
            packet=json.loads(message.payload.decode('utf-8'),object_pairs_hook=_unique_object,
                parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Non-finite JSON')))
            if isinstance(packet,dict):self.task_feedback.put_nowait((parts[3],packet))
        except (ValueError,UnicodeError,queue.Full):logging.warning('Invalid task feedback rejected')

    def accepted_capability(self,node,body,retained,wire):
        if body.get('cap_measure_v')!=1:return
        try:self.capability_inbox.put_nowait(('announcement',node,body,retained,time.time(),wire))
        except queue.Full:logging.warning('Capability measurement queue full; no receipt issued')

    def capability_node_info(self,node):
        entry=next((e for e in self.tasks.inventory_loader()['nodes'] if e['node_id']==node),None)
        if not entry or node==self.tasks.ugv_id or root_of(entry)!=self.tasks.ugv_id or not entry.get('enabled',True) or entry.get('trust_status','trusted')!='trusted':return None
        with self.condition:
            observation=self.registry.nodes.get(node,{})
            cap=observation.get('capabilities',{})
            return dict(role=entry['role'],boot_id=observation.get('presence',{}).get('boot_id'),
                        ready=self.connected.is_set() and self.registry.ready(node),supported=cap.get('cap_measure_v')==1)

    def send_capability_packet(self,node,packet):
        if not self.connected.is_set():return False
        payload=encode(packet)
        with self.condition:
            if len(payload)>self.registry.command_limit(node):
                raise ValueError('capability_command_too_large')
        return self.client.publish(f'mesh/v1/nodes/{node}/commands',payload,qos=1,retain=False).rc==0

    def parent_auth_loop(self):
        while not self.stopped.is_set():
            try:received,node,packet=self.parent_auth_inbox.get(timeout=.2)
            except queue.Empty:continue
            if time.monotonic()-received>2 or not self.connected.is_set():continue
            try:
                reply=self.parent_authority.mqtt_reply(node,packet)
                self.client.publish(f'mesh/v1/nodes/{node}/commands',reply,qos=1,retain=False)
            except (ValueError,OSError,KeyError,TypeError) as exc:
                now=time.monotonic()
                if now-self.parent_auth_denied_at.get(node,-100)>10:
                    self.parent_auth_denied_at[node]=now
                    logging.getLogger(__name__).warning('PARENT_AUTH_DENIED node=%s reason=%s',node,exc)

    def request_loop(self,inbox):
        while not self.stopped.is_set():
            try:item=inbox.get(timeout=.2)
            except queue.Empty:continue
            try:
                item.result.set_result(self.requests.handle(item.packet))
            except Exception as exc:
                if isinstance(item,LocalCall):item.result.set_exception(exc)
                logging.exception('Request failed; worker remains available')

    def submit_local(self,packet):
        if self.stopped.is_set():raise ConnectionError('Service stopped')
        result=Future()
        kind=packet.get('type')
        inbox=self.task_inbox if isinstance(kind,str) and kind in (ACTIONS|{'node.admission'}) else self.inbox
        try:inbox.put_nowait(LocalCall(packet,result))
        except queue.Full:
            return [self.requests.error(packet,'service_busy')]
        try:return result.result(timeout=12)
        except TimeoutError:
            return [self.requests.error(packet,'request_timeout_query_state')]

    def task_loop(self):
        catalog_at=0
        while not self.stopped.wait(.1):
            try:
                self.refresh_inventory()
                for _ in range(64):
                    try:kind,node,body,retained,received,wire=self.capability_inbox.get_nowait()
                    except queue.Empty:break
                    if kind=='announcement':self.capability_measurements.announcement(node,body,retained,received,wire=wire)
                    else:self.capability_measurements.result(node,body,retained)
                self.capability_measurements.tick()
                for _ in range(32):
                    try:node,packet=self.task_feedback.get_nowait()
                    except queue.Empty:break
                    self.tasks.receive(node,packet)
                self.tasks.tick()
                if time.monotonic()-catalog_at>=5:
                    with self.condition:snapshot=self.registry.snapshot()
                    entries=[e for e in self.tasks.inventory_loader()['nodes'] if root_of(e)==self.tasks.ugv_id]
                    self.catalog.update(entries,snapshot)
                    catalog_at=time.monotonic()
            except Exception:
                logging.exception('Task tick failed; persistent state retained')

    def close(self):
        super().close()
        for worker in getattr(self,'workers',[]):worker.join(timeout=2)
        if self.tasks:self.tasks.close()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    service_arguments(p)
    p.add_argument('--ugv-id')
    p.add_argument('--task-db',type=Path)
    p.add_argument('--http-port',type=int,help='HTTP/WS port; 0 disables it')
    p.add_argument('--http-host',help='Explicit bind address; peers are limited by config')
    args=p.parse_args()
    try:
        cfg=resolve_arguments(args)
        ugv_id=args.ugv_id or cfg.ugv_id
        inventory=load_inventory(path=cfg.paths.inventory_file)
        roles=('ugv_root',)
        if not any(e['node_id']==ugv_id and e['role'] in roles and e.get('enabled',True) for e in inventory['nodes']):
            raise ValueError('--ugv-id must name an enabled UGV in the inventory')
    except (ValueError,OSError,KeyError,TypeError) as exc:p.error(str(exc))
    service=None
    api=None
    try:
        service=ServiceController(inventory=inventory,inventory_path=cfg.paths.inventory_file,broker=cfg.broker,
                                  lock_file=cfg.paths.lock_file,paths=cfg.paths,ugv_id=ugv_id,database=args.task_db)
        http_port=args.http_port if args.http_port is not None else cfg.http_port
        http_host=args.http_host or cfg.http_host
        if not 0<=http_port<=65535:raise ValueError('Invalid HTTP port')
        if http_port:
            from changan_ugv.api.server import LocalAPI
            api=LocalAPI(service,http_port,http_host,cfg.http_allowed_peers)
            api.start()
            logging.warning('Terminal HTTP/WS: http://%s:%s/api/v1',http_host,http_port)
        logging.warning('UGV root service active; task database retained on exit')
        while not service.stopped.wait(1):pass
    finally:
        if api:api.close()
        if service:service.close()
if __name__=='__main__':
    try:main()
    except KeyboardInterrupt:pass
