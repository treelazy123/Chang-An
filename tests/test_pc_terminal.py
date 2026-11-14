"""Host-only framing and serial transaction tests; no firmware build or COM port."""
import binascii
import json
from pathlib import Path
import queue
import struct
import sys
import threading
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from mesh_protocol import Decoder, MAGIC, HEADER, MAX_JSON, command, encode
from pc_terminal import RootLink, ConsoleInbox


class FramingTests(unittest.TestCase):
    def test_crc_known_vector(self):
        self.assertEqual(0x29b1, binascii.crc_hqx(b'123456789', 0xffff))

    def test_fragmented_and_coalesced_unicode_messages(self):
        messages = [command('ping micro-001', 'a'), command('echo uav-001 飞行测试', 'b')]
        wire = b''.join(encode(item) for item in messages)
        decoder = Decoder()
        result = []
        for index in range(0, len(wire), 3):
            result.extend(decoder.feed(wire[index:index+3]))
        self.assertEqual(messages, result)
        self.assertFalse(decoder.buffer)

    def test_recovers_after_bad_crc_and_oversized_header(self):
        message = command('list', 'ok')
        corrupt = bytearray(encode(command('ping ugv-001', 'bad')))
        corrupt[-1] ^= 1
        garbage = b'boot log\r\n' + HEADER.pack(MAGIC, MAX_JSON+1, 0)
        decoder = Decoder()
        self.assertEqual([message], decoder.feed(garbage + corrupt + encode(message)))
        self.assertGreaterEqual(decoder.bad_frames, 2)

    def test_large_input_is_bounded(self):
        decoder = Decoder()
        self.assertEqual([], decoder.feed(b'x'*100000))
        self.assertLess(len(decoder.buffer), len(MAGIC))

    def test_invalid_json_version_duplicates_and_utf8_are_rejected(self):
        payloads = [b'{"v":2,"type":"event"}', b'{"v":1,"v":2,"type":"event"}',
                    b'{"v":1,"type":"event","x":NaN}', b'{"v":1,"type":"event","x":"\xff"}']
        decoder = Decoder()
        for payload in payloads:
            frame = HEADER.pack(MAGIC, len(payload), binascii.crc_hqx(payload, 0xffff)) + payload
            self.assertEqual([], decoder.feed(frame))
        self.assertEqual(len(payloads), decoder.bad_frames)

    def test_partial_frame_can_be_reset_after_idle(self):
        decoder = Decoder()
        decoder.feed(encode(command('list', 'lost'))[:12])
        decoder.reset()
        valid = command('list', 'new')
        self.assertEqual([valid], decoder.feed(encode(valid)))

    def test_commands_reject_invalid_target_or_oversize(self):
        for text in ('ping bad/id', 'echo uav-001', 'list extra', 'ping uav-001 extra', 'reboot ugv-001'):
            with self.assertRaises(ValueError):
                command(text)
        with self.assertRaises(ValueError):
            command('echo micro-001 ' + '中'*300)


class ConsoleOutputTests(unittest.TestCase):
    def test_interactive_inbox_does_not_print_or_queue_telemetry(self):
        from unittest.mock import patch
        inbox = ConsoleInbox()
        with patch('builtins.print') as output:
            inbox({'v':1, 'type':'telemetry', 'node_id':'pc-root-001'})
            inbox({'v':1, 'type':'event', 'event':'online', 'peer_id':'ugv-001'})
            output.assert_not_called()
        self.assertEqual(['event'], [item['type'] for item in inbox.drain()])

    def test_monitor_retains_telemetry_without_duplicate_replies(self):
        inbox = ConsoleInbox(include_telemetry=True)
        inbox({'v':1, 'type':'telemetry', 'node_id':'ugv-001'})
        inbox({'v':1, 'type':'ack', 'node_id':'ugv-001', 'msg_id':'test'})
        self.assertEqual(['telemetry'], [item['type'] for item in inbox.drain()])

    def test_console_queue_is_bounded(self):
        inbox = ConsoleInbox(include_telemetry=True, capacity=2)
        for _ in range(20):
            inbox({'v':1, 'type':'telemetry', 'node_id':'ugv-001'})
        self.assertEqual(2, len(inbox.drain()))
        self.assertEqual(18, inbox.dropped)


class FakeSerial:
    def __init__(self, responder=None, short_writes=False):
        self.responder = responder
        self.short_writes = short_writes
        self.incoming = queue.Queue()
        self.decoder = Decoder()
        self.closed = False

    def read(self, size):
        if self.closed:
            return b''
        try:
            return self.incoming.get(timeout=0.02)
        except queue.Empty:
            return b''

    def write(self, data):
        if self.closed:
            raise OSError('closed')
        chunk = data[:5] if self.short_writes else data
        for message in self.decoder.feed(chunk):
            if self.responder:
                self.responder(message, self)
        return len(chunk)

    def inject(self, message):
        wire = encode(message)
        for index in range(0, len(wire), 7):
            self.incoming.put(wire[index:index+7])

    def close(self):
        self.closed = True


class TransactionTests(unittest.TestCase):
    def test_matches_target_and_id_with_telemetry_interleaved(self):
        def respond(request, port):
            port.inject({'v':1, 'type':'telemetry', 'node_id':'ugv-001'})
            port.inject({'v':1, 'type':'ack', 'node_id':'wrong-node', 'msg_id':request['msg_id'], 'ok':True})
            port.inject({'v':1, 'type':'ack', 'node_id':request['target'], 'msg_id':request['msg_id'], 'ok':True})
        received = []
        link = RootLink(FakeSerial(respond, short_writes=True), received.append).start()
        try:
            reply = link.request(command('ping micro-001', 'test'), timeout=1)
            self.assertEqual('micro-001', reply['node_id'])
            self.assertTrue(any(item['type']=='telemetry' for item in received))
        finally:
            link.close()

    def test_reports_gateway_error_without_fabricating_success(self):
        def respond(request, port):
            port.inject({'v':1, 'type':'error', 'node_id':'ugv-001', 'msg_id':request['msg_id'], 'error':'node_offline'})
        link = RootLink(FakeSerial(respond)).start()
        try:
            reply = link.request(command('status micro-001'), timeout=1)
            self.assertEqual('node_offline', reply['error'])
        finally:
            link.close()

    def test_timeout_does_not_retry(self):
        requests = []
        link = RootLink(FakeSerial(lambda message, _: requests.append(message))).start()
        try:
            with self.assertRaises(TimeoutError):
                link.request(command('ping ugv-001'), timeout=0.03)
            self.assertEqual(1, len(requests))
        finally:
            link.close()

    def test_close_wakes_a_waiting_request(self):
        link = RootLink(FakeSerial()).start()
        result = []
        def request():
            try:
                link.request(command('list'), timeout=5)
            except ConnectionError:
                result.append('closed')
        worker = threading.Thread(target=request)
        worker.start()
        deadline = time.monotonic()+1
        while not link._pending and time.monotonic()<deadline:
            time.sleep(0.001)
        link.close()
        worker.join(timeout=1)
        self.assertEqual(['closed'], result)


if __name__ == '__main__':
    unittest.main()
