"""Direct MQTT over an OS IP interface (including a future S31 USB NIC)."""
import json
import ssl
import threading
import time
from ..protocol import MAX_COMMAND,validate,_unique_object,NODE_ID
class MQTTClient:
    def __init__(self,host,port,node_id,cert_dir,server_name='ugv-broker.lab'):
        import paho.mqtt.client as mqtt
        class NamedContext(ssl.SSLContext):
            def wrap_socket(self,*args,server_hostname=None,**kwargs):
                return super().wrap_socket(*args,server_hostname=server_name,**kwargs)
        context=NamedContext(ssl.PROTOCOL_TLS_CLIENT);context.minimum_version=ssl.TLSVersion.TLSv1_2
        context.load_verify_locations(str(cert_dir/'ca.pem'));context.load_cert_chain(str(cert_dir/'client.pem'),str(cert_dir/'client.key'))
        if not NODE_ID.fullmatch(node_id):raise ValueError('Invalid car node ID')
        self.target=None
        self.node_id=node_id;self.pending=None;self.rows=[];self.result=None;self.lock=threading.Condition();self.ready=threading.Event()
        self.events=f'mesh/v1/terminals/{node_id}/events'
        self.on_event=lambda body:None
        self.requests=f'mesh/v1/terminals/{node_id}/requests';self.responses=f'mesh/v1/terminals/{node_id}/responses'
        self.client=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,client_id=node_id,clean_session=True)
        self.client.tls_set_context(context)
        def connect(client,userdata,flags,reason,properties):
            if not reason.is_failure:client.subscribe([(self.responses,1),(self.events,1)])
        def subscribed(client,userdata,mid,reasons,properties):
            if reasons and all(not r.is_failure for r in reasons):self.ready.set()
        def disconnected(*args):
            self.ready.clear()
            with self.lock:self.lock.notify_all()
        def received(client,userdata,msg):
            if msg.retain or msg.topic not in (self.responses,self.events) or len(msg.payload)>1024:return
            try:body=validate(json.loads(msg.payload.decode('utf-8'),object_pairs_hook=_unique_object,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('nonfinite'))))
            except (ValueError,UnicodeError):return
            if msg.topic==self.events:
                if body.get('type')=='task.event':self.on_event(body)
                return
            with self.lock:
                if not self.pending or body.get('msg_id')!=self.pending:return
                if body.get('type')=='ack' and body.get('node_id')!=self.target:return
                if body.get('type')=='nodes':
                    self.rows.extend(body.get('nodes',[]))
                    if len(self.rows)>512:self.result={'type':'error','error':'too_many_nodes'}
                    elif not body.get('more',False):self.result=dict(body,nodes=list(self.rows))
                else:self.result=body
                self.lock.notify_all()
        self.client.on_connect=connect;self.client.on_subscribe=subscribed;self.client.on_disconnect=disconnected;self.client.on_message=received
        self.client.connect(host,port,15);self.client.loop_start()
        if not self.ready.wait(10):self.close();raise TimeoutError('Car MQTT subscription did not complete')
    def request(self,packet):
        with self.lock:
            if not self.ready.is_set():raise ConnectionError('Broker disconnected')
            if self.pending:raise ValueError('A request is already pending')
            packet=dict(packet,node_id=self.node_id)
            body=json.dumps(packet,ensure_ascii=False,separators=(',',':'))
            if len(body.encode('utf-8'))>MAX_COMMAND:raise ValueError('Request too large')
            self.pending=packet['msg_id'];self.target=packet.get('target');self.rows=[];self.result=None
            try:
                if self.client.publish(self.requests,body,qos=1,retain=False).rc:raise OSError('Publish failed')
                end=time.monotonic()+15
                while self.result is None:
                    remaining=end-time.monotonic()
                    if not self.ready.is_set():raise ConnectionError('Broker disconnected')
                    if remaining<=0:raise TimeoutError('UGV did not reply; request was not retried')
                    self.lock.wait(remaining)
                return self.result
            finally:self.pending=None
    def close(self):self.client.disconnect();self.client.loop_stop()
