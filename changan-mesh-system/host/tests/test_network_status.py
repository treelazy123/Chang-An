"""Network list metadata and frame budget, without serial or production services."""
import json
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest

from changan_ugv.nodes.controller import Registry
from changan_ugv.protocol.messages import encode
from changan_ugv.protocol.tunnel import Frame, Decoder, RESET, READY, NETWORK
from changan_ugv.transport.serial_bridge import Engine
from changan_ugv.nodes.network import NetworkStatusFile, read_network_status
from changan_ugv.service.requests import Requests


class NetworkStatusTests(unittest.TestCase):
    def setUp(self):
        self.now = 10.0
        self.node = 'micro-002'
        self.registry = Registry(clock=lambda: self.now, nodes=[self.node])

    def receive(self, kind, **fields):
        return self.registry.receive(f'mesh/v1/nodes/{self.node}/{kind}',
            dict(v=1, type=kind, node_id=self.node, **fields))

    def test_list_keeps_network_payload_and_exposes_freshness(self):
        payload = dict(role='micro_uav', level=3, sta_ip='192.168.5.2', ap_ip='192.168.6.1',
                       gateway='192.168.5.1', parent_bssid='12:34:56:78:90:ab', rssi=-62)
        self.receive('presence', online=True, boot_id='boot')
        self.receive('capabilities', boot_id='boot', operations=['ping', 'status'])
        self.receive('telemetry', boot_id='boot', payload=payload)
        self.now += 1.5
        row = self.registry.snapshot()[0]
        self.assertEqual(payload, row['status'])
        self.assertTrue(row['ready'])
        self.assertTrue(row['online'])
        self.assertTrue(row['status_current_boot'])
        self.assertEqual(1.5, row['status_age_s'])
        self.now += 20
        row = self.registry.snapshot()[0]
        self.assertFalse(row['ready'])
        self.assertTrue(row['online'])  # Presence alone is not fresh readiness.
        self.assertEqual(payload, row['status'])

    def test_current_parent_capability_restores_readiness_after_firmware_upgrade(self):
        self.receive('presence', online=True, boot_id='old')
        self.receive('capabilities', boot_id='old', operations=['ping','status','echo'])
        self.receive('presence', online=True, boot_id='new')
        self.receive('telemetry', boot_id='new', payload=dict(role='micro_uav',level=4,
            ap_enabled=False,parent_connected=True,gateway='192.168.8.1'))
        row = self.registry.snapshot()[0]
        self.assertTrue(row['online'])
        self.assertTrue(row['status_current_boot'])
        self.assertEqual(0, row['status_age_s'])
        self.assertFalse(row['ready'])
        self.assertTrue(self.receive('capabilities', boot_id='new', operations=['ping','status','echo','parent']))
        row = self.registry.snapshot()[0]
        self.assertTrue(row['ready'])
        self.assertIn('parent', row['operations'])

    def test_reboot_and_offline_keep_history_explicit(self):
        self.receive('presence', online=True, boot_id='old')
        self.receive('telemetry', boot_id='old', payload=dict(level=2, sta_ip='192.168.4.2'))
        self.receive('presence', online=True, boot_id='new')
        row = self.registry.snapshot()[0]
        self.assertFalse(row['status_current_boot'])
        self.assertFalse(row['ready'])
        self.receive('presence', online=False)
        self.assertFalse(self.registry.snapshot()[0]['online'])

    def test_unreported_telemetry_remains_unknown(self):
        row = self.registry.snapshot()[0]
        self.assertIsNone(row['status'])
        self.assertIsNone(row['status_age_s'])
        self.assertIsNone(row['online'])
        self.assertFalse(row['status_current_boot'])

    def test_full_network_status_fits_one_node_list_and_ack_frames(self):
        payload = dict(role='micro_uav', topology='chain', level=4, heap=4294967295,
            heap_min=4294967295, uptime_ms=999999999999, sta_ip='255.255.255.254',
            ap_ip='255.255.255.254', gateway='255.255.255.254', netmask='255.255.255.255',
            sta_mac='aa:bb:cc:dd:ee:ff', ap_mac='aa:bb:cc:dd:ee:ff',
            parent_connected=True, parent_bssid='aa:bb:cc:dd:ee:ff', rssi=-127,
            channel=14, associated_children=10)
        row = dict(node_id='n'*32, ready=True, online=True, status_age_s=999999.9,
                   status_current_boot=True, operations=['ping','status','echo'],
                   task_types=['diagnostics'], status=payload)
        for packet in [dict(v=1, type='nodes', node_id='ugv-service', msg_id='m'*64,
                            nodes=[row], more=True),
                       dict(v=1, type='ack', node_id='n'*32, msg_id='m'*64,
                            op='status', ok=True, payload=payload)]:
            self.assertLessEqual(len(encode(packet)), 1032)
            self.assertEqual(payload, json.loads(encode(packet)).get('payload', payload))


class UGVNetworkTunnelTests(unittest.TestCase):
    def report(self, node='ugv-root'):
        return dict(v=1, type='network', node_id=node, payload=dict(role='ugv_root', level=1,
            sta_ip='192.168.1.10', ap_ip='192.168.4.1', gateway='192.168.1.1',
            netmask='255.255.255.0', sta_mac='aa:bb:cc:00:00:01', ap_mac='aa:bb:cc:00:00:02',
            parent_connected=True, parent_bssid='aa:bb:cc:00:00:03', rssi=-45,
            channel=6, associated_children=3))

    def test_negotiated_diagnostic_frame_is_crc_checked_and_epoch_bound(self):
        emitted, reports = [], []
        engine = Engine(emitted.append, on_network=lambda body, epoch: reports.append((body,epoch)))
        engine.receive(Frame(RESET, epoch=7))
        handshake = Decoder().feed(emitted[-1])[0]
        self.assertEqual(READY, handshake.kind)
        self.assertEqual(1, handshake.seq)
        body = self.report()
        packet = Frame(NETWORK, epoch=7, data=json.dumps(body,separators=(',',':')).encode())
        self.assertLessEqual(len(packet.data), 512)
        reports.clear()
        engine.receive(Frame(NETWORK, epoch=6, data=packet.data))
        self.assertEqual([], reports)
        decoder = Decoder()
        wire = packet.encode()
        frames = []
        for i in range(0,len(wire),7):frames.extend(decoder.feed(wire[i:i+7]))
        engine.receive(frames[0])
        self.assertEqual([(body,7)], reports)
        self.assertEqual({}, engine.channels)  # Reports never open a TCP/MQTT channel.
        engine.receive(Frame(NETWORK, epoch=7, data=b'{"v":1,"v":1}'))
        self.assertEqual(7,engine.epoch)
        self.assertEqual(1,len(reports))
        corrupted=bytearray(wire);corrupted[-1]^=1
        with self.assertRaises(ValueError):Decoder().feed(corrupted)

    def test_network_snapshot_expires_and_reset_removes_it(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);path=root/'runtime/ugv-network.json'
            sink=NetworkStatusFile(path,'ugv-root',clock=lambda:100)
            sink(self.report(),7)
            self.assertTrue(read_network_status('ugv-root',root,clock=lambda:101)['fresh'])
            stale=read_network_status('ugv-root',root,clock=lambda:113)
            self.assertFalse(stale['fresh'])
            self.assertEqual(13,stale['age_s'])
            self.assertIsNone(read_network_status('other',root,clock=lambda:101))
            self.assertIsNone(read_network_status('ugv-root',root,clock=lambda:99))
            sink(None,0)
            self.assertFalse(path.exists())
            sink(self.report('other'),8)
            self.assertFalse(path.exists())

    def test_list_carries_usb_status_without_changing_local_task_readiness(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            NetworkStatusFile(root/'runtime/ugv-network.json')(self.report(),7)
            connected=threading.Event();connected.set()
            controller=SimpleNamespace(connected=connected,condition=threading.RLock(),
                registry=Registry(nodes=[]),tasks=SimpleNamespace(ugv_id='ugv-root'),refresh_inventory=lambda:None)
            requests=Requests(controller,root=root,clock=lambda:100)
            result=requests.handle(dict(v=1,type='list',msg_id='network-list',deadline_unix=110))
            row=next(n for page in result for n in page.get('nodes',[]) if n['node_id']=='ugv-root')
            self.assertTrue(row['ready'])
            self.assertEqual('local',row['status']['execution_host'])
            self.assertEqual('192.168.4.1',row['status']['network_status']['status']['ap_ip'])
            self.assertTrue(row['status']['network_status']['fresh'])
            self.assertLessEqual(len(encode(result[0])),1032)
