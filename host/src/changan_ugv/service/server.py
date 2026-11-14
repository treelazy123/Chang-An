"""Headless UGV manager with persistent generic M1 tasks; no scenario-specific APIs."""
from changan_ugv.paths import repository_root
import argparse
import json
import logging
from pathlib import Path
import queue
import threading
from changan_ugv.nodes.controller import Controller
from changan_ugv.protocol.frames import _unique_object, encode
from changan_ugv.nodes.inventory import load_inventory
from changan_ugv.tasks.store import ACTIONS
from changan_ugv.tasks.runtime import Runtime
from changan_ugv.service.requests import Requests
from changan_ugv.transport.rpc import Server

class ServiceController(Controller):
    def __init__(self,*args,root,ugv_id='ugv-001',database=None,**kwargs):
        self.inbox=queue.Queue(16)
        self.task_inbox=queue.Queue(16)
        self.task_feedback=queue.Queue(128)
        self.tasks=None
        self.requests=Requests(self,root)
        super().__init__(*args,**kwargs)
        try:
            self.tasks=Runtime(self,root,ugv_id,database)
            self.requests=Requests(self,root)
            self.workers=[threading.Thread(target=self.request_loop,args=(inbox,),daemon=True)
                          for inbox in (self.inbox,self.task_inbox)]
            self.workers.append(threading.Thread(target=self.task_loop,daemon=True))
            for worker in self.workers:worker.start()
        except BaseException:
            super().close()
            raise

    def on_connect(self,client,userdata,flags,reason,properties):
        super().on_connect(client,userdata,flags,reason,properties)
        if not reason.is_failure:
            client.subscribe([('mesh/v1/terminals/+/requests',1),('mesh/v1/nodes/+/task_events',1)])

    def respond(self,source,response):
        encode(response)
        info=self.client.publish(f'mesh/v1/terminals/{source}/responses',json.dumps(response,ensure_ascii=False,separators=(',',':'),allow_nan=False),qos=1,retain=False)
        if info.rc:logging.warning('Car response could not be published')

    def on_message(self,client,userdata,message):
        parts=message.topic.split('/')
        terminal=len(parts)==5 and parts[:3]==['mesh','v1','terminals'] and parts[4]=='requests'
        feedback=len(parts)==5 and parts[:3]==['mesh','v1','nodes'] and parts[4]=='task_events'
        if not terminal and not feedback:
            super().on_message(client,userdata,message)
            return
        if message.retain or len(message.payload)>(512 if terminal else 1024):return
        try:
            packet=json.loads(message.payload.decode('utf-8'),object_pairs_hook=_unique_object,
                              parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Non-finite JSON')))
            if not isinstance(packet,dict):return
            if feedback:
                self.task_feedback.put_nowait((parts[3],packet))
            else:
                if not self.requests.allowed(parts[3]):return
                inbox=self.task_inbox if isinstance(packet.get('type'),str) and packet['type'] in ACTIONS else self.inbox
                try:inbox.put_nowait((parts[3],packet))
                except queue.Full:
                    identity=packet.get('msg_id')
                    if isinstance(identity,str) and len(identity)<=64:
                        self.respond(parts[3],dict(v=1,type='error',node_id='ugv-service',msg_id=identity,error='service_busy'))
        except (ValueError,UnicodeError,queue.Full,OSError):
            logging.warning('Malformed or excessive car/task message rejected')

    def request_loop(self,inbox):
        while not self.stopped.is_set():
            try:source,packet=inbox.get(timeout=.2)
            except queue.Empty:continue
            try:
                for response in self.requests.handle(packet,source):self.respond(source,response)
            except Exception:
                logging.exception('Request failed; worker remains available')

    def task_loop(self):
        while not self.stopped.wait(.1):
            try:
                self.refresh_inventory()
                for _ in range(32):
                    try:node,packet=self.task_feedback.get_nowait()
                    except queue.Empty:break
                    self.tasks.receive(node,packet)
                self.tasks.tick()
            except Exception:
                logging.exception('Task tick failed; persistent state retained')

    def close(self):
        super().close()
        for worker in getattr(self,'workers',[]):worker.join(timeout=2)
        if self.tasks:self.tasks.close()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--broker-port',type=int,default=8883)
    p.add_argument('--rpc-port',type=int,default=8787)
    p.add_argument('--secrets',type=Path,default=repository_root()/'secrets')
    p.add_argument('--ugv-id',default='ugv-001')
    p.add_argument('--task-db',type=Path,help='Default: runtime/tasks.sqlite3')
    args=p.parse_args();root=args.secrets.resolve().parent
    inventory=load_inventory(root)
    if not any(e['node_id']==args.ugv_id and e['role']=='ugv' and e.get('enabled',True) for e in inventory['nodes']):
        p.error('--ugv-id must name an enabled UGV in the inventory')
    server=Server(args.rpc_port,None)
    service=None
    try:
        service=ServiceController(args.secrets,args.broker_port,inventory,root/'config/nodes.json',root=root,ugv_id=args.ugv_id,database=args.task_db)
        server.requests=service.requests
        logging.warning('UGV M1 service active; maintenance RPC 127.0.0.1:%s; task database retained on exit',args.rpc_port)
        server.serve_forever(poll_interval=.2)
    finally:
        server.server_close()
        if service:service.close()
if __name__=='__main__':
    try:main()
    except KeyboardInterrupt:pass
