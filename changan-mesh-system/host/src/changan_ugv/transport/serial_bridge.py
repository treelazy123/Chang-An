"""UGV USB byte tunnel to one fixed local TLS broker. Does not terminate TLS."""
import argparse
import errno
import logging
import select
import socket
import time
from pathlib import Path
from changan_ugv.paths import repository_root
from changan_ugv.nodes.network import NetworkStatusFile, decode_network
from dataclasses import dataclass
from changan_ugv.protocol.tunnel import (Frame, Decoder, RESET, READY, OPEN, OPEN_OK, DATA, ACK,
                             CLOSE, PING, PONG, NETWORK, CHUNK, MAX_CHANNELS)
LOG = logging.getLogger('serial_tcp_bridge')
@dataclass
class Channel:
    sock: socket.socket
    token: int
    deadline: float
    opening: bool = True
    tx_seq: int = 0
    rx_seq: int = 0
    waiting: bool = False
    pending: bytes = b''
class Engine:
    def __init__(self, emit, target=('127.0.0.1', 8883), clock=time.monotonic, on_network=None):
        self.emit, self.target, self.clock = emit, target, clock
        self.channels = {}
        self.epoch = 0
        self.last_seen = clock()
        self.last_reset = -100.0
        self.on_network = on_network or (lambda body, epoch: None)
    def send(self, kind, channel=255, token=0, seq=0, data=b''):
        self.emit(Frame(kind, channel, self.epoch, token, seq, data).encode())
    def drop(self, channel, notify=True):
        c = self.channels.pop(channel, None)
        if c:
            c.sock.close()
            if notify:
                self.send(CLOSE, channel, c.token)
    def reset(self, epoch=0):
        for ch in list(self.channels):
            self.drop(ch, False)
        self.epoch = epoch
        self.on_network(None, epoch)
    def receive(self, f):
        if f.kind == RESET:
            if not f.epoch or f.channel != 255 or f.data:
                raise ValueError('Invalid firmware reset')
            if f.epoch != self.epoch:
                self.reset(f.epoch)
                LOG.info('USB epoch=%s', self.epoch)
            self.last_seen = self.clock()
            self.send(READY, seq=1)
            return
        if not self.epoch or f.epoch != self.epoch:
            return
        self.last_seen = self.clock()
        if f.kind == NETWORK and f.channel == 255 and not f.token and not f.seq:
            try:
                body = decode_network(f.data)
            except (ValueError, UnicodeError):
                LOG.warning('Invalid USB network diagnostic report ignored')
                return
            self.on_network(body, self.epoch)
            return
        if f.kind == PING and f.channel == 255 and not f.data:
            self.send(PONG)
            return
        if not 0 <= f.channel < MAX_CHANNELS:
            raise ValueError('Invalid channel')
        if f.kind == OPEN:
            if f.data or not f.token or f.channel in self.channels:
                raise ValueError('Duplicate/invalid open')
            sock = socket.socket()
            sock.setblocking(False)
            result = sock.connect_ex(self.target)
            pending_errors = {0, errno.EINPROGRESS, errno.EWOULDBLOCK, errno.EALREADY,
                              10035, 10036, 10037}
            if result not in pending_errors:
                sock.close()
                self.send(CLOSE, f.channel, f.token)
                return
            self.channels[f.channel] = Channel(sock, f.token, self.clock() + 10)
            return
        c = self.channels.get(f.channel)
        if not c or c.token != f.token:
            return  # stale frame from a closed connection must never touch a new one
        if f.kind == CLOSE and not f.data:
            self.drop(f.channel, False)
        elif f.kind == ACK and not f.data and c.waiting and f.seq == c.tx_seq:
            c.waiting = False
            c.tx_seq = (c.tx_seq + 1) & 0xffff
        elif f.kind == DATA and not c.opening and f.data and not c.pending and f.seq == c.rx_seq:
            c.pending = f.data
            c.deadline = self.clock() + 15
        else:
            self.drop(f.channel)
    def tick(self):
        now = self.clock()
        if self.epoch and now - self.last_seen > 5:
            self.reset()
        if not self.epoch:
            if now - self.last_reset > 1:
                self.send(RESET)
                self.last_reset = now
            return
        socks = [c.sock for c in self.channels.values()]
        # Winsock rejects select([], [], [], timeout) with WSAEINVAL (10022).
        # An established USB session may legitimately have no TCP channels yet.
        if not socks:
            return
        readers = [c.sock for c in self.channels.values() if not c.opening and not c.waiting]
        writers = [c.sock for c in self.channels.values() if c.opening or c.pending]
        readable, writable, exceptional = select.select(readers, writers, socks, 0)
        for ch, c in list(self.channels.items()):
            try:
                if c.sock in exceptional or ((c.opening or c.waiting or c.pending) and now > c.deadline):
                    self.drop(ch)
                    continue
                if c.opening and c.sock in writable:
                    if c.sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR):
                        self.drop(ch)
                        continue
                    c.opening = False
                    self.send(OPEN_OK, ch, c.token)
                    LOG.info('OPEN channel=%s token=%s', ch, c.token)
                if not c.opening and c.pending and c.sock in writable:
                    count = c.sock.send(c.pending)
                    if not count:
                        self.drop(ch)
                        continue
                    c.pending = c.pending[count:]
                    if not c.pending:
                        self.send(ACK, ch, c.token, c.rx_seq)
                        c.rx_seq = (c.rx_seq + 1) & 0xffff
                if not c.opening and not c.waiting and c.sock in readable:
                    data = c.sock.recv(CHUNK)
                    if not data:
                        self.drop(ch)
                        continue
                    self.send(DATA, ch, c.token, c.tx_seq, data)
                    c.waiting = True
                    c.deadline = now + 15
            except BlockingIOError:
                pass
            except OSError:
                self.drop(ch)
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', required=True, help='UGV C6 native USB COM port')
    parser.add_argument('--broker-port', type=int, default=8883)
    parser.add_argument('--ugv-id', default='ugv-001', help='Expected UGV USB device identity')
    parser.add_argument('--network-status', type=Path, default=repository_root()/'runtime/ugv-network.json')
    args = parser.parse_args()
    import serial
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
    while True:
        try:
            # No DTR/RTS reset; one process owns this COM port.
            link = serial.Serial(port=None, baudrate=115200, timeout=0, write_timeout=0.5)
            link.dtr = link.rts = False
            link.port = args.port
            with link:
                def emit(packet):
                    view = memoryview(packet)
                    while view:
                        count = link.write(view)
                        if not count:
                            raise OSError('Serial write made no progress')
                        view = view[count:]
                network_status = NetworkStatusFile(args.network_status, args.ugv_id)
                network_status(None, 0)
                engine = Engine(emit, ('127.0.0.1', args.broker_port), on_network=network_status)
                decoder = Decoder()
                try:
                    while True:
                        data = link.read(2048)
                        try:
                            for f in decoder.feed(data):
                                engine.receive(f)
                        except ValueError as exc:
                            LOG.warning('%s', exc)
                            engine.reset()
                            decoder = Decoder()
                        engine.tick()
                        time.sleep(0.005)
                finally:
                    engine.reset()
        except (OSError, serial.SerialException) as exc:
            LOG.warning('USB unavailable: %s; retrying in 2s', exc)
            time.sleep(2)
if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
