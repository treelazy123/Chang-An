"""MUX1 binary protocol. CRC protects type, channel, epoch, token, seq, length and data."""
import binascii
from dataclasses import dataclass
import struct
RESET, READY, OPEN, OPEN_OK, DATA, ACK, CLOSE, PING, PONG = range(1, 10)
NETWORK = 10  # Optional channel-255 report, negotiated by READY seq=1.
CHUNK = 512
MAX_CHANNELS = 8
HEADER = struct.Struct('!4sBBIIHHH')
@dataclass(frozen=True)
class Frame:
    kind: int
    channel: int = 255
    epoch: int = 0
    token: int = 0
    seq: int = 0
    data: bytes = b''
    def encode(self):
        if not 1 <= self.kind <= NETWORK or len(self.data) > CHUNK:
            raise ValueError('Invalid tunnel frame')
        head = HEADER.pack(b'MUX1', self.kind, self.channel, self.epoch, self.token,
                           self.seq, len(self.data), 0)
        crc = binascii.crc_hqx(head[4:18] + self.data, 0xffff)
        return head[:18] + struct.pack('!H', crc) + self.data
class Decoder:
    def __init__(self):
        self.buffer = bytearray()
    def feed(self, data):
        result = []
        for byte in data:
            self.buffer.append(byte)
            while len(self.buffer) >= 4 and self.buffer[:4] != b'MUX1':
                del self.buffer[0]
            if len(self.buffer) < HEADER.size:
                continue
            _, kind, ch, epoch, token, seq, size, crc = HEADER.unpack(self.buffer[:20])
            if size > CHUNK or not 1 <= kind <= NETWORK:
                self.buffer.clear()
                raise ValueError('Invalid tunnel header; reset all streams')
            if len(self.buffer) < 20 + size:
                continue
            payload = bytes(self.buffer[20:])
            computed = binascii.crc_hqx(bytes(self.buffer[4:18]) + payload, 0xffff)
            self.buffer.clear()
            if computed != crc:
                raise ValueError('Tunnel CRC error; reset all streams')
            result.append(Frame(kind, ch, epoch, token, seq, payload))
        return result
