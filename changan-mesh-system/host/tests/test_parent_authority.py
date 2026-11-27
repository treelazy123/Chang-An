"""Adversarial online parent grants, enrollment preservation and USB negotiation."""
import base64
import contextlib
import hashlib
import io
import json
from pathlib import Path
import secrets
import sys
import tempfile
from types import SimpleNamespace
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from cryptography.hazmat.primitives.asymmetric import ec
from changan_ugv.nodes.admission import AdmissionManager
from changan_ugv.nodes.inventory import load_inventory, write_inventory
from changan_ugv.nodes.parent_authority import (ParentAuthority, REQUEST, REQUEST_SIZE, GRANT_SIZE,
    field, private_key, public_bytes, sign, validate_grant)
from changan_ugv.protocol.tunnel import Frame, Decoder, RESET, READY, PARENT_REQUEST, PARENT_GRANT
from changan_ugv.transport.serial_bridge import Engine
from provision_mqtt import provision as provision_tls
from provision_parent_auth import provision


class ParentAuthorityTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        with contextlib.redirect_stdout(io.StringIO()):provision_tls(self.root)
        self.inventory=load_inventory(self.root)
        self.old={p:p.read_bytes() for p in (self.root/'secrets').rglob('*') if p.is_file()}
        provision(self.root)
        self.directory=self.root/'secrets/parent-auth'
        self.public=(self.directory/'authority.pub').read_bytes()
        verifier=SimpleNamespace(ca_file=self.root/'secrets/ca.pem',identities_dir=self.root/'secrets')
        self.authority=ParentAuthority(self.directory,lambda:self.inventory,'ugv-root',
            certificate=lambda node:AdmissionManager.certificate(verifier,node))
        self.ap=bytes.fromhex('021122334455');self.child=bytes.fromhex('0266778899aa')

    def request(self,node='uav-001',root='ugv-root',purpose=1,nonce=None,ap=None,child=None):
        key=private_key((self.directory/'nodes'/node/'auth.key').read_bytes())
        body=REQUEST.pack(b'PAR1',purpose,field(node),field(root),b'b'*16,ap or self.ap,
                          nonce or secrets.token_bytes(16),child or self.child)
        return body+sign(key,body)

    def test_incremental_enrollment_is_idempotent_and_never_modifies_tls_credentials(self):
        for p,value in self.old.items():self.assertEqual(value,p.read_bytes())
        before={p:p.read_bytes() for p in self.directory.rglob('*') if p.is_file()}
        provision(self.root)
        self.assertEqual(before,{p:p.read_bytes() for p in self.directory.rglob('*') if p.is_file()})

    def test_missing_enrolled_key_is_not_regenerated(self):
        path=self.directory/'nodes/uav-001/auth.key';path.unlink()
        with self.assertRaisesRegex(ValueError,'Missing enrolled node key'):provision(self.root)
        self.assertFalse(path.exists())

    def test_issuer_private_key_cannot_be_used_as_a_device_signing_key(self):
        node=self.directory/'nodes/uav-001'
        (node/'auth.key').write_bytes((self.directory/'authority.key').read_bytes())
        (node/'auth.pub').write_bytes(self.public)
        path=self.directory/'bindings.json';record=json.loads(path.read_text())
        record['nodes']['uav-001']['public_key']=self.public.hex();path.write_text(json.dumps(record))
        before={p:p.read_bytes() for p in self.directory.rglob('*') if p.is_file()}
        with self.assertRaisesRegex(ValueError,'shared with authority'):provision(self.root)
        self.assertEqual(before,{p:p.read_bytes() for p in self.directory.rglob('*') if p.is_file()})

    def test_fresh_parent_proof_is_bound_to_nonce_child_bssid_root_and_level(self):
        request=self.request();grant=self.authority.issue(request,'uav-001')
        self.assertEqual(177,REQUEST_SIZE);self.assertEqual(312,len(grant));self.assertEqual(312,GRANT_SIZE)
        expected=dict(node='uav-001',root='ugv-root',purpose=1,nonce=request[91:107],child=self.child,ap=self.ap)
        validate_grant(grant,self.public,expected,3)
        for name,value in [('nonce',b'x'*16),('child',b'y'*6),('ap',b'z'*6),('root','other-root')]:
            with self.subTest(name=name),self.assertRaises(ValueError):
                validate_grant(grant,self.public,dict(expected,**{name:value}),3)
        with self.assertRaises(ValueError):validate_grant(grant,self.public,expected,2)

    def test_forgery_corruption_truncation_and_wrong_authority_fail(self):
        request=self.request();grant=self.authority.issue(request,'uav-001')
        for at in (0,4,70,100,115,180,242,243,247,280):
            corrupt=bytearray(grant);corrupt[at]^=1
            with self.subTest(at=at),self.assertRaises(ValueError):validate_grant(bytes(corrupt),self.public,{},3)
        with self.assertRaises(ValueError):validate_grant(grant[:-1],self.public,{},3)
        other=ec.generate_private_key(ec.SECP256R1())
        with self.assertRaises(ValueError):validate_grant(grant,public_bytes(other.public_key()),{},3)

    def test_topic_identity_root_and_private_key_possession_cannot_be_forged(self):
        request=self.request()
        with self.assertRaises(ValueError):self.authority.issue(request,'ugv-001')
        with self.assertRaises(ValueError):self.authority.issue(self.request(root='foreign-root'),'uav-001')
        attacker=private_key((self.directory/'nodes/micro-001/auth.key').read_bytes())
        forged=request[:-64]+sign(attacker,request[:-64])
        with self.assertRaises(ValueError):self.authority.issue(forged,'uav-001')

    def test_revocation_disable_role_and_certificate_changes_prevent_renewal_without_acl_reload(self):
        request=self.request()
        entry=next(e for e in self.inventory['nodes'] if e['node_id']=='uav-001')
        for field_name,value in [('trust_status','revoked'),('enabled',False),('role','micro_uav'),('root_id','foreign')]:
            original=dict(entry);entry[field_name]=value
            with self.subTest(name=field_name),self.assertRaises(ValueError):self.authority.issue(request,'uav-001')
            entry.clear();entry.update(original)
        with self.assertRaises(ValueError):self.authority.issue(self.request(node='micro-001'),'micro-001')
        self.authority.certificate=lambda node:'wrong-fingerprint'
        with self.assertRaises(ValueError):self.authority.issue(request,'uav-001')

    def test_root_requires_selected_usb_transport_and_matching_offline_key(self):
        request=self.request(node='ugv-root',purpose=0)
        with self.assertRaises(ValueError):self.authority.issue(request,'ugv-root')
        grant=self.authority.issue(request,'ugv-root',usb=True)
        validate_grant(grant,self.public,dict(node='ugv-root',purpose=0),1)
        with self.assertRaises(ValueError):self.authority.issue(self.request(),'uav-001',usb=True)

    def test_mqtt_envelopes_fit_existing_command_limit_and_reject_extra_fields(self):
        request=self.request()
        packet=dict(v=1,type='parent.auth.request',proof=base64.b64encode(request).decode())
        reply=self.authority.mqtt_reply('uav-001',packet)
        self.assertLessEqual(len(reply.encode()),512)
        grant=base64.b64decode(json.loads(reply)['proof'],validate=True)
        validate_grant(grant,self.public,dict(node='uav-001'),3)
        with self.assertRaises(ValueError):self.authority.mqtt_reply('uav-001',dict(packet,ready=True))

    def test_default_enrollment_skips_untrusted_template_without_creating_tls_credentials(self):
        self.inventory['nodes'].append(dict(node_id='ugv-pending',role='ugv',root_id='ugv-root',
                                            ap_subnet=7,trust_status='pending'))
        write_inventory(self.root,self.inventory)
        result=provision(self.root)
        self.assertIn('ugv-pending',result['skipped'])
        self.assertFalse((self.directory/'nodes/ugv-pending').exists())
        self.assertFalse((self.root/'secrets/ugv-pending').exists())

    def test_usb_epoch_and_identity_protect_root_grant_channel(self):
        output=[]
        engine=Engine(output.append,on_parent_auth=lambda proof:self.authority.issue(proof,'ugv-root',usb=True))
        engine.receive(Frame(RESET,epoch=123))
        self.assertEqual(2,Decoder().feed(output[-1])[0].seq)
        request=self.request(node='ugv-root',purpose=0)
        engine.receive(Frame(PARENT_REQUEST,epoch=122,data=request))
        self.assertEqual(1,len(output))
        engine.receive(Frame(PARENT_REQUEST,epoch=123,data=request))
        reply=Decoder().feed(output[-1])[0]
        self.assertEqual(PARENT_GRANT,reply.kind)
        validate_grant(reply.data,self.public,dict(node='ugv-root'),1)
        before=len(output)
        engine.receive(Frame(PARENT_REQUEST,epoch=123,data=self.request()))
        self.assertEqual(before,len(output))
        legacy=[];Engine(legacy.append).receive(Frame(RESET,epoch=1))
        self.assertEqual(1,Decoder().feed(legacy[0])[0].seq)


class ParentBrokerIntegration(unittest.TestCase):
    setUp=ParentAuthorityTests.setUp
    request=ParentAuthorityTests.request

    def test_actual_mtls_broker_routes_grants_and_revocation_stops_renewals_without_acl_reload(self):
        import os,queue,shutil,socket,ssl,subprocess,time
        import paho.mqtt.client as mqtt
        from changan_ugv.deployment import render_broker_config
        from changan_ugv.nodes.inventory import write_acl
        from changan_ugv.nodes.controller import BrokerTLSContext
        from changan_ugv.service.server import ServiceController
        broker=shutil.which('mosquitto') or r'D:\Program Files (x86)\Mosquitto\mosquitto.exe'
        if not Path(broker).is_file():self.skipTest('Requires isolated Mosquitto')
        write_acl(self.root,self.inventory)
        with socket.socket() as listener:
            listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
        text=render_broker_config(ca_file=self.root/'secrets/ca.pem',
            server_cert=self.root/'secrets/ugv-broker.lab/client.pem',server_key=self.root/'secrets/ugv-broker.lab/client.key',
            acl_file=self.root/'runtime/ugv-root/acl.conf',listeners=[('127.0.0.1',port)])
        config=self.root/'test-broker.conf';config.write_text(text,encoding='utf-8')
        log=(self.root/'broker.log').open('w')
        process=subprocess.Popen([broker,'-c',str(config)],stdout=log,stderr=log,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        service=client=None
        try:
            deadline=time.monotonic()+5
            while True:
                try:
                    with socket.create_connection(('127.0.0.1',port),timeout=.1):break
                except OSError:
                    if process.poll() is not None or time.monotonic()>deadline:self.fail('Isolated Broker failed')
                    time.sleep(.05)
            service=ServiceController(self.root/'secrets',port,self.inventory,self.root/'config/nodes.json',root=self.root)
            self.assertTrue(service.connected.wait(5))
            received=queue.Queue();subscribed=__import__('threading').Event()
            client=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,client_id='uav-001',protocol=mqtt.MQTTv311)
            context=BrokerTLSContext(ssl.PROTOCOL_TLS_CLIENT)
            context.load_verify_locations(str(self.root/'secrets/ca.pem'))
            context.load_cert_chain(str(self.root/'secrets/uav-001/client.pem'),str(self.root/'secrets/uav-001/client.key'))
            client.tls_set_context(context)
            client.on_connect=lambda c,u,f,r,p:c.subscribe('mesh/v1/nodes/uav-001/commands',1)
            client.on_subscribe=lambda *args:subscribed.set()
            client.on_message=lambda c,u,m:received.put(json.loads(m.payload))
            client.connect('127.0.0.1',port,15);client.loop_start()
            self.assertTrue(subscribed.wait(5))
            def publish(request,retain=False):
                packet=dict(v=1,type='parent.auth.request',proof=base64.b64encode(request).decode())
                client.publish('mesh/v1/nodes/uav-001/telemetry',json.dumps(packet),qos=1,retain=retain).wait_for_publish(2)
            request=self.request();publish(request)
            reply=received.get(timeout=5)
            self.assertEqual('parent.auth.grant',reply['type'])
            validate_grant(base64.b64decode(reply['proof']),self.public,dict(nonce=request[91:107]),3)
            publish(self.request(),retain=True)
            # MQTT 3.1.1 clears RETAIN on live forwarding; test the stored replay
            # delivered on subscription, whose RETAIN flag really is set.
            self.assertEqual('parent.auth.grant',received.get(timeout=5)['type'])
            service.client.subscribe('mesh/v1/nodes/uav-001/telemetry',1)
            with self.assertRaises(queue.Empty):received.get(timeout=.4)
            publish(self.request(node='ugv-001'))
            with self.assertRaises(queue.Empty):received.get(timeout=.4)
            entry=next(e for e in self.inventory['nodes'] if e['node_id']=='uav-001')
            entry['trust_status']='revoked';write_inventory(self.root,self.inventory)
            publish(self.request())
            with self.assertRaises(queue.Empty):received.get(timeout=.6)
        finally:
            if client:client.disconnect();client.loop_stop()
            if service:service.close()
            process.terminate()
            try:process.wait(5)
            except subprocess.TimeoutExpired:process.kill();process.wait(5)
            log.close()


if __name__=='__main__':unittest.main()
