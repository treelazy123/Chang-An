"""Reassemble chunked image uploads from nodes and persist them locally.

Each node streams an embedded image over the existing MQTT/TLS session as a
sequence of base64 JSON chunks on ``mesh/v1/nodes/<id>/image``. The sink buffers
chunks keyed by (node, image_id) and writes the concatenated bytes to disk once
the final chunk arrives. Images are untrusted bytes even from an authenticated
node, so filenames are validated and never used to build paths.

Storage is bounded: completed files are pruned oldest-first once the image
directory exceeds ``max_bytes``, and unfinished reassembly buffers are dropped
after ``pending_ttl`` or when their count/bytes exceed the pending caps, so a
stalled or misbehaving node cannot fill the disk or exhaust memory.
"""
import base64
import binascii
import logging
import re
import time
from pathlib import Path

LOG = logging.getLogger(__name__)

_SAFE_NAME = re.compile(r'^[A-Za-z0-9._-]{1,64}$')
MAX_CHUNKS = 100000
MAX_TOTAL_BYTES = 256 * 1024 * 1024
MAX_PENDING = 64
MAX_PENDING_BYTES = 64 * 1024 * 1024
PENDING_TTL_S = 600


class ImageSink:
    def __init__(self, directory, max_bytes=MAX_TOTAL_BYTES, pending_ttl=PENDING_TTL_S,
                 max_pending=MAX_PENDING, max_pending_bytes=MAX_PENDING_BYTES, clock=time.monotonic):
        self.directory = Path(directory)
        self.max_bytes = max_bytes
        self.pending_ttl = pending_ttl
        self.max_pending = max_pending
        self.max_pending_bytes = max_pending_bytes
        self.clock = clock
        self.pending = {}

    def _safe(self, value, fallback):
        return value if isinstance(value, str) and _SAFE_NAME.fullmatch(value) else fallback

    def consume(self, node_id, body, retained=False):
        if retained or not isinstance(body, dict):
            return
        if body.get('v') != 1 or body.get('type') != 'image' or body.get('node_id') != node_id:
            return
        image_id = self._safe(body.get('image_id'), None)
        if image_id is None:
            return
        name = self._safe(body.get('name'), image_id)
        data = body.get('data')
        seq = body.get('seq')
        count = body.get('count')
        if type(seq) is not int or type(count) is not int or not 0 <= seq < count or count > MAX_CHUNKS:
            return
        if not isinstance(data, str) or not data:
            return
        try:
            raw = base64.b64decode(data, validate=True)
        except (binascii.Error, ValueError):
            return
        now = self.clock()
        key = (node_id, image_id)
        entry = self.pending.get(key)
        if entry is None or entry['count'] != count or entry['name'] != name:
            entry = {'count': count, 'name': name, 'chunks': {}, 'bytes': 0, 'ts': now}
            self.pending[key] = entry
        previous = entry['chunks'].get(seq, b'')
        entry['chunks'][seq] = raw
        entry['bytes'] += len(raw) - len(previous)
        entry['ts'] = now
        self._trim(now)
        if len(entry['chunks']) != count:
            return
        self.pending.pop(key, None)
        try:
            blob = b''.join(entry['chunks'][i] for i in range(count))
        except KeyError:
            return
        self._save(node_id, name, blob)

    def _trim(self, now):
        for key, entry in list(self.pending.items()):
            if now - entry['ts'] > self.pending_ttl:
                self.pending.pop(key, None)
        while len(self.pending) > self.max_pending:
            self.pending.pop(min(self.pending, key=lambda k: self.pending[k]['ts']))
        total = sum(entry['bytes'] for entry in self.pending.values())
        while total > self.max_pending_bytes and self.pending:
            key = min(self.pending, key=lambda k: self.pending[k]['ts'])
            total -= self.pending.pop(key)['bytes']

    def _save(self, node_id, name, blob):
        target_dir = self.directory / self._safe(node_id, 'unknown')
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / name
            target.write_bytes(blob)
            LOG.info('Saved image node=%s file=%s bytes=%d', node_id, target.name, len(blob))
        except OSError as exc:
            LOG.warning('Failed to save image node=%s: %s', node_id, exc)
            return
        self._prune(target)

    def _prune(self, keep):
        if self.max_bytes is None or self.max_bytes <= 0:
            return
        files = []
        try:
            node_dirs = [p for p in self.directory.iterdir() if p.is_dir()]
        except OSError:
            return
        for node_dir in node_dirs:
            try:
                files.extend(p for p in node_dir.iterdir() if p.is_file())
            except OSError:
                continue
        entries = []
        total = 0
        for path in files:
            try:
                stat = path.stat()
            except OSError:
                continue
            entries.append((stat.st_mtime, path, stat.st_size))
            total += stat.st_size
        if total <= self.max_bytes:
            return
        for _, path, size in sorted(entries):
            if total <= self.max_bytes:
                break
            if path == keep:
                continue
            try:
                path.unlink()
                total -= size
                LOG.info('Pruned image file=%s bytes=%d', path, size)
            except OSError as exc:
                LOG.warning('Failed to prune image file=%s: %s', path, exc)
