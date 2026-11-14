"""Wire protocol shared by the PC terminal and firmware: MLT1 + !HH + UTF-8 JSON."""
import binascii
import json
import re
import struct
import uuid

MAGIC = b'MLT1'
MAX_JSON = 1024
MAX_COMMAND = 512
HEADER = struct.Struct('!4sHH')
NODE_ID = re.compile(r'^[A-Za-z0-9_-]{1,32}$')


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key: ' + key)
        result[key] = value
    return result


def validate(message):
    if not isinstance(message, dict) or type(message.get('v')) is not int or message['v'] != 1:
        raise ValueError('Expected an object with protocol v=1')
    kind = message.get('type')
    if not isinstance(kind, str) or not 1 <= len(kind) <= 24:
        raise ValueError('Invalid message type')
    return message


def encode(message):
    validate(message)
    payload = json.dumps(message, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')
    if not 2 <= len(payload) <= MAX_JSON:
        raise ValueError('Message exceeds 1024 UTF-8 bytes')
    return HEADER.pack(MAGIC, len(payload), binascii.crc_hqx(payload, 0xffff)) + payload


class Decoder:
    """Bounded streaming decoder; recovers after garbage, bad length, or CRC failure."""
    def __init__(self):
        self.buffer = bytearray()
        self.discarded = 0
        self.bad_frames = 0

    def reset(self):
        self.buffer.clear()

    def feed(self, data):
        messages = []
        # Processing one byte at a time also bounds memory for arbitrarily large input chunks.
        for byte in data:
            self.buffer.append(byte)
            while len(self.buffer) >= len(MAGIC):
                if not self.buffer.startswith(MAGIC):
                    del self.buffer[0]
                    self.discarded += 1
                    continue
                if len(self.buffer) < HEADER.size:
                    break
                _, size, crc = HEADER.unpack_from(self.buffer)
                if not 2 <= size <= MAX_JSON:
                    del self.buffer[0]
                    self.bad_frames += 1
                    continue
                total = HEADER.size + size
                if len(self.buffer) < total:
                    break
                payload = bytes(self.buffer[HEADER.size:total])
                if binascii.crc_hqx(payload, 0xffff) != crc:
                    del self.buffer[0]
                    self.bad_frames += 1
                    continue
                del self.buffer[:total]
                try:
                    message = json.loads(payload.decode('utf-8'), object_pairs_hook=_unique_object,
                                         parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
                    messages.append(validate(message))
                except (ValueError, UnicodeError):
                    self.bad_frames += 1
        return messages


def command(line, msg_id=None):
    parts = line.strip().split(maxsplit=2)
    if not parts:
        raise ValueError('Enter list, ping NODE, status NODE, echo NODE TEXT, or quit')
    kind = parts[0].lower()
    identity = msg_id or uuid.uuid4().hex
    if not isinstance(identity, str) or not 1 <= len(identity) <= 64:
        raise ValueError('msg_id must contain 1-64 characters')
    if kind == 'list':
        if len(parts) != 1:
            raise ValueError('Usage: list')
        message = {'v': 1, 'type': 'list', 'msg_id': identity}
    elif kind in ('ping', 'status', 'echo'):
        if len(parts) < 2 or not NODE_ID.fullmatch(parts[1]):
            raise ValueError('Usage: ' + kind + ' NODE' + (' TEXT' if kind == 'echo' else ''))
        if kind != 'echo' and len(parts) != 2:
            raise ValueError('Unexpected extra arguments')
        message = {'v': 1, 'type': 'command', 'target': parts[1], 'msg_id': identity, 'op': kind}
        if kind == 'echo':
            if len(parts) != 3:
                raise ValueError('Usage: echo NODE TEXT')
            message['payload'] = parts[2]
    else:
        raise ValueError('Supported commands: list, ping, status, echo')
    if len(encode(message)) - HEADER.size > MAX_COMMAND:
        raise ValueError('PC request exceeds the 512-byte command limit')
    return message
