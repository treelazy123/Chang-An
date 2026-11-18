"""Host-only checks: framing, flow control, real mTLS through the byte bridge, registry safety."""
from collections import deque
from pathlib import Path
import socket
import ssl
import struct
import sys
import tempfile
import threading
import time
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from tunnel_protocol import Frame,Decoder,RESET,READY,OPEN,OPEN_OK,DATA,ACK,CLOSE,CHUNK
from serial_tcp_bridge import Engine
from provision_mqtt import provision
from changan_ugv.nodes.controller import Registry

class Framing(unittest.TestCase):
    def test_fragmentation_binary_and_coalescing(self):
        source=Frame(DATA,2,0x01020304,42,65535,bytes(range(256))*2)
        wire=source.encode()+Frame(ACK,2,0x01020304,42,65535).encode()
        decoder=Decoder();actual=[]
        for i in range(0,len(wire),7): actual.extend(decoder.feed(wire[i:i+7]))
        self.assertEqual([source,Frame(ACK,2,0x01020304,42,65535)],actual)
        self.assertEqual(b'',decoder.buffer)
    def test_header_and_payload_corruption_fail_closed(self):
        wire=Frame(DATA,0,7,12,0,b'\x00hello').encode()
        for index in (4,5,7,12,15,18,22):
            corrupt=bytearray(wire);corrupt[index]^=1
            with self.assertRaises(ValueError): Decoder().feed(corrupt)
    def test_garbage_is_bounded_and_oversize_is_rejected(self):
        d=Decoder();d.feed(b'x'*100000);self.assertLess(len(d.buffer),4)
        with self.assertRaises(ValueError): Frame(DATA,data=b'x'*513).encode()
        malformed=bytearray(Frame(DATA,data=b'x').encode());malformed[16:18]=struct.pack('!H',513)
        with self.assertRaises(ValueError): Decoder().feed(malformed)

class StreamLifecycle(unittest.TestCase):
    def setUp(self):
        self.output=[];self.now=100.0
        self.listener=socket.socket();self.listener.bind(('127.0.0.1',0));self.listener.listen(3)
        self.engine=Engine(self.output.append,self.listener.getsockname(),lambda:self.now)
        self.engine.receive(Frame(RESET,epoch=12))
    def tearDown(self): self.engine.reset();self.listener.close()
    def connect(self,ch=0,token=1):
        self.engine.receive(Frame(OPEN,ch,12,token))
        for _ in range(100):
            self.engine.tick()
            if self.output and Decoder().feed(self.output[-1])[0].kind==OPEN_OK: break
            time.sleep(.001)
        server,_=self.listener.accept();server.settimeout(2);self.addCleanup(server.close)
        return server
    def test_ready_usb_session_without_tcp_channels_never_calls_select(self):
        from unittest.mock import patch
        with patch('serial_tcp_bridge.select.select', side_effect=OSError(10022, 'empty Winsock select')) as select_mock:
            self.engine.tick()
        select_mock.assert_not_called()
        self.assertEqual(12,self.engine.epoch)

    def test_ack_only_after_socket_accepts_bytes_and_backpressure(self):
        server=self.connect();self.output.clear()
        self.engine.receive(Frame(DATA,0,12,1,0,b'abc'))
        self.assertEqual([],self.output)
        self.engine.tick();self.assertEqual(b'abc',server.recv(3))
        self.assertEqual(ACK,Decoder().feed(self.output[-1])[0].kind)
        server.sendall(b'x'*1200)
        self.engine.tick();count=len(self.output)
        self.engine.tick();self.assertEqual(count,len(self.output))
        first=Decoder().feed(self.output[-1])[0];self.assertEqual(DATA,first.kind)
        self.engine.receive(Frame(ACK,0,12,1,first.seq));self.engine.tick()
        self.assertGreater(len(self.output),count)
    def test_socket_eof_waits_for_last_data_ack(self):
        server=self.connect();self.output.clear();server.sendall(b'last record');server.shutdown(socket.SHUT_WR)
        self.engine.tick();last=Decoder().feed(self.output[-1])[0]
        self.assertEqual(DATA,last.kind);self.engine.tick();self.assertIn(0,self.engine.channels)
        self.engine.receive(Frame(ACK,0,12,1,last.seq));self.engine.tick()
        self.assertNotIn(0,self.engine.channels)
        self.assertEqual(CLOSE,Decoder().feed(self.output[-1])[0].kind)
    def test_eighth_host_channel_is_supported_and_ninth_is_rejected(self):
        self.connect(ch=7,token=7)
        self.assertIn(7,self.engine.channels)
        with self.assertRaises(ValueError):self.engine.receive(Frame(OPEN,8,12,8))
    def test_stale_token_and_epoch_do_not_close_new_connection(self):
        self.connect();self.engine.receive(Frame(CLOSE,0,12,999));self.engine.receive(Frame(CLOSE,0,11,1))
        self.assertIn(0,self.engine.channels)
        self.engine.receive(Frame(RESET,epoch=13));self.assertEqual({},self.engine.channels)
    def test_bad_sequence_closes_and_heartbeat_expiry_resets(self):
        self.connect();self.engine.receive(Frame(DATA,0,12,1,9,b'bad'))
        self.assertNotIn(0,self.engine.channels)
        self.now+=6;self.engine.tick();self.assertEqual(0,self.engine.epoch)
    def test_missing_ack_closes_bounded_stream(self):
        server=self.connect();server.sendall(b'test');self.engine.tick()
        self.now+=16;self.engine.last_seen=self.now;self.engine.tick()
        self.assertNotIn(0,self.engine.channels)

class RealTLS(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.root=Path(cls.temp.name);provision(cls.root)
        from node_identity import enroll
        enroll(cls.root,'micro_uav','micro-002')
    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()
    def run_tls(self,identities,nocert=False,server_name='ugv-broker.lab',wrong_ca=False):
        secret=self.root/'secrets';received=[];errors=[];output=deque()
        listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(3);listener.settimeout(5)
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version=ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(str(secret/'ugv-broker.lab/client.pem'),str(secret/'ugv-broker.lab/client.key'))
        context.load_verify_locations(str(secret/'ca.pem'));context.verify_mode=ssl.CERT_REQUIRED
        workers=[]
        def serve(sock):
            try:
                sock.settimeout(5)
                with context.wrap_socket(sock,server_side=True) as tls:
                    data=b''
                    while len(data)<4096:
                        part=tls.recv(4096-len(data))
                        if not part: break
                        data+=part
                    received.append((tls.getpeercert()['subject'][0][0][1],data))
                    tls.sendall(data[::-1])
            except (OSError,ssl.SSLError) as exc: errors.append(exc)
        def accept():
            try:
                for _ in identities:
                    sock,_=listener.accept();t=threading.Thread(target=serve,args=(sock,));workers.append(t);t.start()
            except OSError: pass
        accept_thread=threading.Thread(target=accept);accept_thread.start()
        engine=Engine(output.append,listener.getsockname());engine.receive(Frame(RESET,epoch=88))
        peers=[]
        for i,identity in enumerate(identities):
            if wrong_ca: c=ssl.create_default_context()
            else: c=ssl.create_default_context(cafile=str(secret/'ca.pem'))
            if not nocert: c.load_cert_chain(str(secret/identity/'client.pem'),str(secret/identity/'client.key'))
            incoming,outgoing=ssl.MemoryBIO(),ssl.MemoryBIO()
            obj=c.wrap_bio(incoming,outgoing,server_side=False,server_hostname=server_name)
            peers.append(dict(obj=obj,incoming=incoming,outgoing=outgoing,opened=False,waiting=False,
                              seq=0,handshake=False,sent=False,answer=b'',failure=None))
            engine.receive(Frame(OPEN,i,88,i+1))
        deadline=time.monotonic()+8
        try:
            while time.monotonic()<deadline:
                engine.last_seen=time.monotonic();engine.tick()
                while output:
                    wire=output.popleft();d=Decoder();frames=[]
                    for k in range(0,len(wire),11): frames+=d.feed(wire[k:k+11])
                    for f in frames:
                        if f.channel>=len(peers): continue
                        p=peers[f.channel]
                        if f.kind==OPEN_OK: p['opened']=True
                        elif f.kind==ACK: p['waiting']=False;p['seq']=(p['seq']+1)&65535
                        elif f.kind==DATA:
                            p['incoming'].write(f.data)
                            engine.receive(Frame(ACK,f.channel,88,f.token,f.seq))
                        elif f.kind==CLOSE:
                            p['incoming'].write_eof()  # TCP FIN follows accepted bytes; drain TLS records before EOF
                for i,p in enumerate(peers):
                    if not p['opened'] or p['failure']: continue
                    try:
                        if not p['handshake']:
                            p['obj'].do_handshake();p['handshake']=True
                        if p['handshake'] and not p['sent']:
                            p['obj'].write(bytes(range(256))*16);p['sent']=True
                        if p['sent'] and len(p['answer'])<4096:
                            p['answer']+=p['obj'].read(4096-len(p['answer']))
                    except (ssl.SSLWantReadError,ssl.SSLWantWriteError): pass
                    except ssl.SSLError as exc: p['failure']=exc
                    if not p['waiting'] and p['outgoing'].pending:
                        payload=p['outgoing'].read(CHUNK);p['waiting']=True
                        engine.receive(Frame(DATA,i,88,i+1,p['seq'],payload))
                if all(len(p['answer'])==4096 or p['failure'] for p in peers): break
                time.sleep(.001)
        finally:
            engine.reset();listener.close();accept_thread.join(6)
            for t in workers: t.join(6)
        return peers,received,errors
    def test_three_distinct_mutual_tls_identities_and_binary_streams(self):
        ids=['ugv-001','uav-001','micro-001'];peers,received,errors=self.run_tls(ids)
        self.assertEqual([],errors)
        self.assertEqual(set(ids),{x[0] for x in received})
        for p in peers:
            self.assertIsNone(p['failure'])
            self.assertEqual((bytes(range(256))*16)[::-1],p['answer'])
    def test_four_distinct_tls_clients_share_one_bridge(self):
        ids=['ugv-001','uav-001','micro-001','micro-002'];peers,received,errors=self.run_tls(ids)
        self.assertEqual([],errors)
        self.assertEqual(set(ids),{x[0] for x in received})
        for p in peers:
            self.assertIsNone(p['failure'])
            self.assertEqual((bytes(range(256))*16)[::-1],p['answer'])
    def test_wrong_server_identity_is_rejected(self):
        p,received,_=self.run_tls(['uav-001'],server_name='wrong.lab')
        self.assertIsInstance(p[0]['failure'],ssl.SSLCertVerificationError);self.assertEqual([],received)
    def test_unknown_ca_is_rejected(self):
        p,received,_=self.run_tls(['uav-001'],wrong_ca=True)
        self.assertIsInstance(p[0]['failure'],ssl.SSLCertVerificationError);self.assertEqual([],received)
    def test_missing_client_certificate_is_rejected(self):
        p,received,errors=self.run_tls(['uav-001'],nocert=True)
        self.assertTrue(p[0]['failure']);self.assertEqual([],received);self.assertTrue(errors)
    def test_keys_are_not_overwritten(self):
        with self.assertRaises(ValueError): provision(self.root)

class RegistrySafety(unittest.TestCase):
    def setUp(self): self.now=0;self.r=Registry(lambda:self.now)
    def msg(self,suffix,body,retained=False,node='uav-001'):
        return self.r.receive('mesh/v1/nodes/'+node+'/'+suffix,dict(v=1,node_id=node,**body),retained)
    def test_retained_records_do_not_make_a_device_ready(self):
        self.msg('presence',dict(type='presence',online=True,boot_id='a'),True)
        self.msg('capabilities',dict(type='capabilities',operations=['ping'],boot_id='a'),True)
        self.msg('telemetry',dict(type='telemetry',boot_id='a'),True)
        self.assertFalse(self.r.ready('uav-001'))
        self.msg('telemetry',dict(type='telemetry',boot_id='a'))
        self.assertTrue(self.r.ready('uav-001'))
        self.now=21;self.assertFalse(self.r.ready('uav-001'))
    def test_identity_capability_and_boot_mismatch_are_rejected(self):
        self.assertFalse(self.r.receive('mesh/v1/nodes/uav-001/presence',dict(v=1,node_id='micro-001',type='presence',online=True)))
        self.assertFalse(self.msg('capabilities',dict(type='capabilities',operations=['actuate'])))
        self.msg('presence',dict(type='presence',online=True,boot_id='a'))
        self.msg('capabilities',dict(type='capabilities',operations=['ping'],boot_id='b'))
        self.msg('telemetry',dict(type='telemetry',boot_id='a'))
        self.assertFalse(self.r.ready('uav-001'))


class ControllerTransactions(unittest.TestCase):
    def make_controller(self):
        from changan_ugv.nodes.controller import Controller
        controller=Controller.__new__(Controller)
        controller.condition=threading.Condition();controller.pending={};controller.replies={}
        controller.connected=threading.Event();controller.connected.set();controller.registry=Registry()
        n='uav-001'
        for kind,extra in [('presence',dict(online=True)),('capabilities',dict(operations=['ping'])),('telemetry',dict(payload={}))]:
            controller.registry.receive(f'mesh/v1/nodes/{n}/{kind}',dict(v=1,node_id=n,type=kind,boot_id='a',**extra))
        return controller
    def test_ack_correlation_ignores_wrong_identity_and_retained_ack(self):
        from types import SimpleNamespace
        c=self.make_controller()
        class Client:
            def publish(_,topic,payload,**kwargs):
                body=__import__('json').loads(payload)
                for node,retained in [('micro-001',False),('uav-001',True),('uav-001',False)]:
                    ack=dict(v=1,type='ack',node_id=node,msg_id=body['msg_id'],ok=True)
                    msg=SimpleNamespace(topic=f'mesh/v1/nodes/{node}/acks',payload=__import__('json').dumps(ack).encode(),retain=retained)
                    c.on_message(None,None,msg)
                return SimpleNamespace(rc=0)
        c.client=Client();reply=c.command('uav-001','ping')
        self.assertEqual('uav-001',reply['node_id']);self.assertFalse(c.pending)
    def test_timeout_does_not_republish_and_unready_target_is_rejected(self):
        from types import SimpleNamespace
        c=self.make_controller();calls=[]
        c.client=SimpleNamespace(publish=lambda *a,**kw:(calls.append(a) or SimpleNamespace(rc=0)))
        with self.assertRaises(TimeoutError): c.command('uav-001','ping',timeout=.01)
        self.assertEqual(1,len(calls));self.assertFalse(c.pending)
        with self.assertRaises(ValueError): c.command('micro-001','ping')

class NewBuildMode(unittest.TestCase):
    def test_four_current_role_dry_runs_are_isolated(self):
        import subprocess
        for role in ('ugv_root','ugv','uav','micro_uav'):
            result=subprocess.run([sys.executable,str(ROOT/'tools/lab.py'),'--role',role,
                                   '--transport','mqtt_serial','--dry-run'],capture_output=True,text=True)
            self.assertEqual(0,result.returncode,result.stderr)
            self.assertIn(str(ROOT/'build/mqtt_serial/nodes'/dict(ugv_root='ugv-root',ugv='ugv-001',uav='uav-001',micro_uav='micro-001')[role]/(role+'-chain')),result.stdout)
        invalid=subprocess.run([sys.executable,str(ROOT/'tools/lab.py'),'--role','uav','--transport','mqtt_serial',
                                '--topology','star','--dry-run'],capture_output=True,text=True)
        self.assertNotEqual(0,invalid.returncode)

if __name__=='__main__': unittest.main()

