"""Reassemble chunked image uploads from nodes and persist them locally.

Each node streams an embedded image over the existing MQTT/TLS session as a
sequence of base64 JSON chunks on ``mesh/v1/nodes/<id>/image``. The sink buffers
chunks keyed by (node, image_id) and writes the concatenated bytes to disk once
the final chunk arrives. Images are untrusted bytes even from an authenticated
node, so filenames are validated and never used to build paths.
"""
import base64
import binascii
import logging
import re
from pathlib import Path

LOG = logging.getLogger(__name__)

_SAFE_NAME = re.compile(r'^[A-Za-z0-9._-]{1,64}$')
MAX_CHUNKS = 100000


class ImageSink:
    def __init__(self, directory):
        self.directory = Path(directory)
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
        key = (node_id, image_id)
        entry = self.pending.get(key)
        if entry is None or entry['count'] != count or entry['name'] != name:
            entry = {'count': count, 'name': name, 'chunks': {}}
            self.pending[key] = entry
        entry['chunks'][seq] = raw
        if len(entry['chunks']) != count:
            return
        self.pending.pop(key, None)
        try:
            blob = b''.join(entry['chunks'][i] for i in range(count))
        except KeyError:
            return
        self._save(node_id, name, blob)

    def _save(self, node_id, name, blob):
        target_dir = self.directory / self._safe(node_id, 'unknown')
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / name
            target.write_bytes(blob)
            LOG.info('Saved image node=%s file=%s bytes=%d', node_id, target.name, len(blob))
        except OSError as exc:
            LOG.warning('Failed to save image node=%s: %s', node_id, exc)
