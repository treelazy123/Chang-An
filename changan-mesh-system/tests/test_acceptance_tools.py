"""Offline acceptance-tool checks. Never accesses the production broker or serial ports."""
from pathlib import Path
import contextlib
import io
import socket
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from check_firmware_size import inspect, ENTRY
import verify_broker_security as security
class FirmwareSizing(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
    def fixture(self,size):
        table=self.root/'partition_table';table.mkdir()
        (table/'partition-table.bin').write_bytes(ENTRY.pack(0x50aa,0,0,0x10000,1024,b'factory',0)+b'\xff'*32)
        (self.root/'mesh_lite_node.bin').write_bytes(b'x'*size)
    def test_uses_compiled_partition_and_detects_overflow(self):
        self.fixture(512);result=inspect(self.root)
        self.assertEqual('PASS',result['status']);self.assertEqual(512,result['free_app_bytes'])
        (self.root/'mesh_lite_node.bin').write_bytes(b'x'*1025)
        self.assertEqual('FAIL',inspect(self.root)['status'])
    def test_missing_and_invalid_artifacts_do_not_report_pass(self):
        self.assertEqual('MISSING',inspect(self.root)['status'])
        self.fixture(1);(self.root/'partition_table/partition-table.bin').write_bytes(b'x'*32)
        with self.assertRaises(ValueError):inspect(self.root)
class BrokerTool(unittest.TestCase):
    def test_requires_declared_client_isolation_before_network_access(self):
        with patch.object(sys,'argv',['verify_broker_security.py']),patch.object(security,'run') as run,contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as result:security.main()
        self.assertEqual(2,result.exception.code);run.assert_not_called()
    def test_mqtt5_coalesced_fragmented_payloads_and_acks(self):
        client,server=socket.socketpair();self.addCleanup(client.close);self.addCleanup(server.close)
        client.settimeout(.02);server.settimeout(.2)
        peer=security.Peer.__new__(security.Peer);peer.sock=client;peer.buffer=bytearray();peer.messages=[]
        topic='mesh/v1/nodes/micro-001/commands';payload=b'probe'*100
        body=security.text(topic)+b'\x00\x07\x00'+payload
        packet=b'\x32'+security.varint(len(body))+body
        server.sendall(packet+b'\x40\x02\x00\x09')
        header,ack=peer.wait_packet(0x40,9,timeout=1)
        self.assertEqual((topic,payload),peer.messages[0]);self.assertEqual(b'\x00\x09',ack)
        self.assertEqual(b'\x40\x02\x00\x07',server.recv(4))
    def test_valid_ack_timeout_is_not_treated_as_authorization_denial(self):
        client,server=socket.socketpair();self.addCleanup(client.close);self.addCleanup(server.close)
        client.settimeout(.01)
        peer=security.Peer.__new__(security.Peer);peer.sock=client;peer.buffer=bytearray();peer.messages=[]
        with self.assertRaises(TimeoutError):peer.wait_packet(0x40,1,timeout=.02)
if __name__=='__main__':unittest.main()
