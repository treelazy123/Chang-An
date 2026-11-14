"""PC terminal for the native USB Serial/JTAG port on the pc_root C6.

Examples:
  python tools/pc_terminal.py --list-ports
  python tools/pc_terminal.py --port COM7
  python tools/pc_terminal.py --port COM7 --command "ping micro-001"
"""
import argparse
from dataclasses import dataclass, field
import json
import queue
import threading
import time
from mesh_protocol import Decoder, HEADER, MAX_COMMAND, command, encode


@dataclass
class Pending:
    target: str | None
    done: threading.Event = field(default_factory=threading.Event)
    result: dict | None = None


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
                        if pending and message['type'] in ('ack', 'nodes', 'error'):
                            # A target's ACK, not an unrelated node's ACK, completes a command.
                            if message['type'] != 'ack' or message.get('node_id') == pending.target:
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


class ConsoleInbox:
    """The RX thread queues output; only the foreground thread writes the console."""
    def __init__(self, include_telemetry=False, capacity=64):
        self.messages = queue.Queue(maxsize=capacity)
        self.include_telemetry = include_telemetry
        self.dropped = 0

    def __call__(self, message):
        if message['type'] in ('ack', 'nodes', 'error'):
            return
        if message['type'] == 'telemetry' and not self.include_telemetry:
            return
        try:
            self.messages.put_nowait(message)
        except queue.Full:
            self.dropped += 1

    def drain(self):
        messages = []
        while True:
            try:
                messages.append(self.messages.get_nowait())
            except queue.Empty:
                return messages


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', help='Native USB Serial/JTAG COM port of the pc_root board')
    parser.add_argument('--baud', type=int, default=115200, help='Serial API baud value; native USB does not use UART baud')
    parser.add_argument('--timeout', type=float, default=5.0)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--command', help='Run one command and exit; otherwise open an interactive terminal')
    modes.add_argument('--monitor', action='store_true', help='Receive and print telemetry only; Ctrl+C exits')
    parser.add_argument('--list-ports', action='store_true')
    args = parser.parse_args()
    try:
        import serial
    except ImportError:
        parser.error('Install pyserial: python -m pip install -r tools/requirements-pc.txt')
    if args.list_ports:
        from serial.tools import list_ports
        for item in list_ports.comports():
            print(item.device + '  ' + item.description)
        return 0
    if not args.port:
        parser.error('Provide --port with the native USB port of the pc_root board')
    if args.timeout <= 0:
        parser.error('--timeout must be positive')
    inbox = ConsoleInbox(include_telemetry=args.monitor)

    def show_events():
        for message in inbox.drain():
            print(json.dumps(message, ensure_ascii=False), flush=True)

    link = None
    try:
        # Leave modem-control lines deasserted; do not intentionally reset the board.
        device = serial.Serial(port=None, baudrate=args.baud, timeout=0.1, write_timeout=1)
        device.dtr = False
        device.rts = False
        device.port = args.port
        device.open()
        link = RootLink(device, inbox).start()
        if args.monitor:
            print('Monitoring telemetry. Ctrl+C exits; use interactive mode for commands.')
            while True:
                try:
                    message = inbox.messages.get(timeout=0.2)
                except queue.Empty:
                    if link._error:
                        raise ConnectionError('Serial receiver stopped') from link._error
                    continue
                print(json.dumps(message, ensure_ascii=False), flush=True)
        if args.command:
            reply = link.request(command(args.command), args.timeout)
            print(json.dumps(reply, ensure_ascii=False))
            return 1 if reply['type'] == 'error' or reply.get('ok') is False else 0
        print('Connected. Commands: list | ping NODE | status NODE | echo NODE TEXT | quit')
        while True:
            show_events()
            try:
                line = input('mesh> ').strip()
            except EOFError:
                break
            show_events()
            if line.lower() in ('quit', 'exit'):
                break
            if not line:
                continue
            try:
                reply = link.request(command(line), args.timeout)
                show_events()
                print(json.dumps(reply, ensure_ascii=False))
            except (ValueError, TimeoutError) as exc:
                print(str(exc))
        return 0
    except KeyboardInterrupt:
        return 130
    except (OSError, ConnectionError, TimeoutError, ValueError) as exc:
        print('Terminal error: ' + str(exc))
        return 1
    finally:
        if link:
            link.close()


if __name__ == '__main__':
    raise SystemExit(main())
