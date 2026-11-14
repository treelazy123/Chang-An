"""Loopback-only compatibility RPC. Network car access uses authenticated MQTT terminal topics."""
import socket
import socketserver
import threading
import time
import uuid
from changan_ugv.protocol.frames import Decoder,encode
class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address=True
    daemon_threads=True
    def __init__(self,port,requests):
        self.requests=requests
        super().__init__(('127.0.0.1',port),Handler)
class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        self.request.settimeout(25);decoder=Decoder()
        try:
            while True:
                data=self.request.recv(1024)
                if not data:return
                for packet in decoder.feed(data):
                    if packet.get('type')=='service_info':
                        rows=[dict(v=1,type='service_info',service='changan-ugv-v1',msg_id=packet.get('msg_id'))]
                    else:rows=self.server.requests.handle(packet)
                    for row in rows:self.request.sendall(encode(row))
        except (OSError,ValueError):return
class LocalController:
    def __init__(self,port):self.port=port;self.condition=threading.Condition();self.registry=self
    def exchange(self,packet,timeout=15,connection=None):
        with connection if connection is not None else socket.create_connection(('127.0.0.1',self.port),timeout=2) as sock:
            sock.settimeout(timeout);sock.sendall(encode(packet));decoder=Decoder();nodes=[]
            while True:
                data=sock.recv(1024)
                if not data:raise ConnectionError('UGV service closed the connection')
                for row in decoder.feed(data):
                    if row.get('msg_id')!=packet['msg_id']:continue
                    if row['type']=='nodes':
                        nodes.extend(row['nodes'])
                        if not row.get('more',False):return nodes
                    elif row['type']=='error':raise ValueError(row.get('error','UGV request failed'))
                    else:return row
    @classmethod
    def discover(cls,port):
        obj=cls(port)
        try:connection=socket.create_connection(('127.0.0.1',port),timeout=.5)
        except (ConnectionRefusedError,TimeoutError):return None
        info=obj.exchange(dict(v=1,type='service_info',msg_id=uuid.uuid4().hex),timeout=2,connection=connection)
        if info.get('service')!='changan-ugv-v1':raise ConnectionError('Unexpected service at local RPC port')
        return obj
    def snapshot(self):return self.exchange(dict(v=1,type='list',msg_id=uuid.uuid4().hex,deadline_unix=int(time.time())+20))
    def command(self,node,op,text=None):
        packet=dict(v=1,type='command',target=node,op=op,msg_id=uuid.uuid4().hex,deadline_unix=int(time.time())+20)
        if op=='echo':packet['payload']=text or ''
        return self.exchange(packet)
    def close(self):pass  # Closing UI never stops the UGV backend or its clock.
