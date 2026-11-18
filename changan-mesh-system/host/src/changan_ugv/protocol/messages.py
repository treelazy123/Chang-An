"""Bounded JSON control messages for node MQTT/TLS."""
import json
import re
import uuid

MAX_JSON = 1024
MAX_COMMAND = 512
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
    return payload


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
    if len(encode(message)) > MAX_COMMAND:
        raise ValueError('PC request exceeds the 512-byte command limit')
    return message
