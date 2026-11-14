"""Independent car USB framed transport, with paginated replies and target/message correlation."""
import argparse
from dataclasses import dataclass, field
import json
import queue
import threading
import time
from .protocol import Decoder, HEADER, MAX_COMMAND, command, encode


@dataclass
class Pending:
    target: str | None
    done: threading.Event = field(default_factory=threading.Event)
    result: dict | None = None
    nodes: list = field(default_factory=list)


class RootLink:
    """Serial transport with independent RX and correlation of replies by msg_id."""
    def __init__(self, serial_port, on_message=None):
        self.serial = serial_port
        self.on_message = on_message or (lambda message: None)
        self.decoder = Decoder()
        self._pending = {}
        self._lock = threading.Lock()
        self._write_lock = threading.Lock()
        self._stop = threading.Event()
        self._error = None
        self._reader = threading.Thread(target=self._read, name='mesh-pc-rx', daemon=True)

    def start(self):
        self._reader.start()
        return self

    def _read(self):
        last_data = time.monotonic()
        try:
            while not self._stop.is_set():
                data = self.serial.read(256)
                if not data:
                    if time.monotonic() - last_data > 1:
                        self.decoder.reset()
                    continue
                last_data = time.monotonic()
                for message in self.decoder.feed(data):
                    identity = message.get('msg_id')
                    with self._lock:
                        pending = self._pending.get(identity) if isinstance(identity, str) else None
                        if pending and message['type'] in ('ack', 'nodes', 'error', 'task.reply'):
                            # A target's ACK, not an unrelated node's ACK, completes a command.
                            if message['type'] != 'ack' or message.get('node_id') == pending.target:
                                if message['type']=='nodes':
                                    pending.nodes.extend(message.get('nodes',[]))
                                    if len(pending.nodes)>512:raise ValueError('Too many list entries')
                                    if message.get('more',False):continue
                                    message=dict(message,nodes=pending.nodes)
                                pending.result = message
                                pending.done.set()
                    self.on_message(message)
        except (OSError, ValueError) as exc:
            self._error = exc
            with self._lock:
                for pending in self._pending.values():
                    pending.done.set()

    def request(self, message, timeout=5.0):
        frame = encode(message)
        if len(frame) - HEADER.size > MAX_COMMAND:
            raise ValueError('PC requests are limited to 512 UTF-8 bytes')
        identity = message.get('msg_id')
        if not isinstance(identity, str) or not 1 <= len(identity) <= 64:
            raise ValueError('Request requires msg_id (1-64 characters)')
        pending = Pending(message.get('target'))
        with self._lock:
            if self._stop.is_set() or self._error:
                raise ConnectionError('Serial connection is closed')
            if identity in self._pending:
                raise ValueError('msg_id is already pending')
            self._pending[identity] = pending
        try:
            with self._write_lock:
                sent = 0
                while sent < len(frame):
                    size = self.serial.write(frame[sent:])
                    if not size:
                        raise ConnectionError('Serial write made no progress')
                    sent += size
            if not pending.done.wait(timeout):
                raise TimeoutError('No reply for ' + identity + '; command was not automatically retried')
            if pending.result is None:
                raise ConnectionError('Serial connection closed while waiting for a reply') from self._error
            return pending.result
        finally:
            with self._lock:
                self._pending.pop(identity, None)

    def close(self):
        self._stop.set()
        with self._lock:
            for pending in self._pending.values():
                pending.done.set()
        self.serial.close()
        if self._reader.is_alive():
            self._reader.join(timeout=1)

