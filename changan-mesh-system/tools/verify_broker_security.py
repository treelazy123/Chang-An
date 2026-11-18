"""Manual actual-broker mTLS/ACL acceptance. Exit UGV Service and power off Micro before running."""
import argparse
import json
from pathlib import Path
import socket
import ssl
import struct
import tempfile
import time
import uuid
from changan_ugv.nodes.controller import BrokerTLSContext

def varint(value):
    out=bytearray()
    while True:
        byte=value%128;value//=128;out.append(byte|(128 if value else 0))
        if not value:return bytes(out)
def text(value):
    data=value.encode('utf-8');return struct.pack('!H',len(data))+data
def context(secret,identity=None,pair=None):
    result=BrokerTLSContext(ssl.PROTOCOL_TLS_CLIENT)
    result.minimum_version=ssl.TLSVersion.TLSv1_2
    result.load_verify_locations(str(secret/'ca.pem'))
    if identity:
        result.load_cert_chain(str(secret/identity/'client.pem'),str(secret/identity/'client.key'))
    elif pair:result.load_cert_chain(str(pair[0]),str(pair[1]))
    return result
class Peer:
    def __init__(self,secret,identity,port):
        self.sock=None
        raw=socket.create_connection(('127.0.0.1',port),timeout=5)
        try:self.sock=context(secret,identity).wrap_socket(raw,server_hostname='ugv-broker.lab')
        except BaseException:raw.close();raise
        self.sock.settimeout(.2);self.buffer=bytearray();self.messages=[];self.next_id=0
        self.send(0x10,b'\x00\x04MQTT\x05\x02\x00\x0f\x00'+text(identity))
        _,body=self.wait_packet(0x20)
        if len(body)<3 or body[1]!=0:raise RuntimeError('MQTT5 CONNECT rejected: '+body.hex())
    def send(self,header,body):self.sock.sendall(bytes([header])+varint(len(body))+body)
    def packet(self,timeout):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            if len(self.buffer)>=2:
                size=0;multiplier=1;end=None
                for index in range(1,min(len(self.buffer),5)):
                    byte=self.buffer[index];size+=(byte&127)*multiplier;multiplier*=128
                    if not byte&128:end=index+1;break
                if end is not None and len(self.buffer)>=end+size:
                    header=self.buffer[0];body=bytes(self.buffer[end:end+size]);del self.buffer[:end+size]
                    if header&0xf0==0x30:
                        length=int.from_bytes(body[:2],'big');topic=body[2:2+length].decode();pos=2+length
                        qos=(header>>1)&3
                        if qos:
                            mid=body[pos:pos+2];pos+=2
                            self.send(0x40,mid)
                        props=0;multiplier=1
                        while True:
                            byte=body[pos];pos+=1;props+=(byte&127)*multiplier;multiplier*=128
                            if not byte&128:break
                        self.messages.append((topic,body[pos+props:]))
                        continue
                    return header,body
            try:chunk=self.sock.recv(4096)
            except socket.timeout:continue
            if not chunk:raise ConnectionError('Broker closed the test connection')
            self.buffer.extend(chunk)
        return None
    def wait_packet(self,kind,mid=None,timeout=5):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            packet=self.packet(max(.01,deadline-time.monotonic()))
            if packet and packet[0]&0xf0==kind and (mid is None or packet[1][:2]==struct.pack('!H',mid)):
                return packet
        raise TimeoutError('No expected MQTT5 acknowledgement')
    def subscribe(self,topic):
        self.next_id+=1;mid=self.next_id
        self.send(0x82,struct.pack('!H',mid)+b'\x00'+text(topic)+b'\x01')
        _,body=self.wait_packet(0x90,mid)
        if len(body)<4 or body[2]!=0:raise RuntimeError('Unexpected SUBACK properties')
        return body[3]
    def publish(self,topic,payload):
        self.next_id+=1;mid=self.next_id
        self.send(0x32,text(topic)+struct.pack('!H',mid)+b'\x00'+payload)
        _,body=self.wait_packet(0x40,mid)
        return body[2] if len(body)>2 else 0
    def received(self,topic,payload,seconds=1.5):
        deadline=time.monotonic()+seconds
        while True:
            if (topic,payload) in self.messages:return True
            if time.monotonic()>=deadline:return False
            self.packet(max(.01,deadline-time.monotonic()))
    def close(self):
        if self.sock:
            try:self.send(0xe0,b'')
            except OSError:pass
            self.sock.close();self.sock=None

def must(condition,message):
    if not condition:raise RuntimeError('FAIL: '+message)
    print('PASS:',message)
def rejected_tls(secret,port,pair=None):
    raw=socket.create_connection(('127.0.0.1',port),timeout=5)
    try:
        with context(secret,pair=pair).wrap_socket(raw,server_hostname='ugv-broker.lab') as tls:
            tls.settimeout(3)
            # TLS 1.3 alerts can arrive after wrap_socket returned; require an actual read.
            body=b'\x00\x04MQTT\x05\x02\x00\x0f\x00'+text('rejected-probe')
            tls.sendall(b'\x10'+varint(len(body))+body)
            return not tls.recv(1)
    except (ssl.SSLError,ConnectionResetError):return True
    finally:raw.close()
def run(secret,port):
    observer=node=None
    try:
        # These identities replace same-identity sessions because broker binds client ID to certificate CN.
        observer=Peer(secret,'controller-001',port)
        node=Peer(secret,'micro-001',port)
        must(observer.subscribe('mesh/v1/nodes/+/acks')<128,'controller can observe application ACK topics')
        must(node.subscribe('mesh/v1/nodes/micro-001/commands')<128,'Micro can subscribe to its own commands')
        nonce=uuid.uuid4().hex
        payload=json.dumps({'v':1,'type':'acceptance_probe','nonce':nonce},separators=(',',':')).encode()
        own='mesh/v1/nodes/micro-001/acks';cross='mesh/v1/nodes/uav-001/acks'
        must(node.publish(own,payload)<128 and observer.received(own,payload),'Micro can publish its own ACK topic')
        must(node.publish(cross,payload)>=128,'Micro cross-node publish rejected by MQTT5 PUBACK')
        must(not observer.received(cross,payload),'forbidden cross-node publication was not delivered')
        own_command='mesh/v1/nodes/micro-001/commands';cross_command='mesh/v1/nodes/uav-001/commands'
        node.subscribe(cross_command)
        must(observer.publish(own_command,payload)<128 and node.received(own_command,payload),
             'positive control: Micro receives its own command topic probe')
        must(observer.publish(cross_command,payload)<128,'controller can publish the cross-read probe')
        must(not node.received(cross_command,payload),'Micro cannot receive UAV commands even if SUBACK grants the filter')
        must(rejected_tls(secret,port),'missing client certificate is rejected by actual Broker')
        with tempfile.TemporaryDirectory() as directory:
            from cryptography import x509
            from cryptography.hazmat.primitives import hashes,serialization
            from cryptography.hazmat.primitives.asymmetric import ec
            from cryptography.x509.oid import NameOID,ExtendedKeyUsageOID
            from datetime import datetime,timedelta,timezone
            key=ec.generate_private_key(ec.SECP256R1());name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'untrusted-client')])
            now=datetime.now(timezone.utc)
            cert=(x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
                  .serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(minutes=5))
                  .not_valid_after(now+timedelta(hours=1))
                  .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH]),critical=False)
                  .sign(key,hashes.SHA256()))
            cert_path=Path(directory)/'untrusted.pem';key_path=Path(directory)/'untrusted.key'
            cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
            key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
            must(rejected_tls(secret,port,(cert_path,key_path)),'untrusted client certificate is rejected by actual Broker')
    finally:
        if node:node.close()
        if observer:observer.close()
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--broker-port',type=int,default=8883)
    parser.add_argument('--secrets',type=Path,default=Path(__file__).resolve().parents[1]/'secrets')
    parser.add_argument('--clients-stopped',action='store_true',help='UGV Service exited and Micro powered off before this test')
    args=parser.parse_args()
    if not args.clients_stopped:
        parser.error('Exit UGV Service and power off Micro first; this test reuses their certificate identities. Then pass --clients-stopped.')
    try:run(args.secrets,args.broker_port)
    except (OSError,ValueError,RuntimeError,TimeoutError) as exc:parser.exit(1,str(exc)+'\n')
    print('Actual-broker mTLS/ACL acceptance passed. Restart UGV Service, power on Micro, then wait for fresh ready.')
if __name__=='__main__':main()
