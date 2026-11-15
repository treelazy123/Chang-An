"""Read-only UGV USB network diagnostics; never grants node or MQTT authorization."""
import json
import logging
from pathlib import Path
import time

from changan_ugv.paths import repository_root
from changan_ugv.protocol.frames import NODE_ID, _unique_object


def decode_network(data):
    body = json.loads(data, object_pairs_hook=_unique_object,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Non-finite network status')))
    if (not isinstance(body, dict) or type(body.get('v')) is not int or body['v'] != 1 or
        body.get('type') != 'network' or not NODE_ID.fullmatch(str(body.get('node_id', ''))) or
        not isinstance(body.get('payload'), dict) or body['payload'].get('role') != 'ugv'):
        raise ValueError('Invalid UGV network report')
    if any(not isinstance(value, (str, int, float, bool, type(None))) for value in body['payload'].values()):
        raise ValueError('Invalid network status value')
    return body


class NetworkStatusFile:
    def __init__(self, path, node_id='ugv-001', clock=time.monotonic):
        self.path, self.node_id, self.clock = Path(path), node_id, clock

    def __call__(self, body, epoch):
        try:
            if body is None:
                self.path.unlink(missing_ok=True)
                return
            if body['node_id'] != self.node_id:
                return
            record = dict(body, bridge_epoch=epoch, seen_monotonic=self.clock())
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix('.tmp')
            temporary.write_text(json.dumps(record, separators=(',', ':')), encoding='utf-8')
            temporary.replace(self.path)
        except OSError as exc:
            logging.getLogger(__name__).warning('Network snapshot unavailable: %s', exc)


def read_network_status(node_id, root=None, *, clock=time.monotonic):
    path = (Path(root) if root is not None else repository_root())/'runtime/ugv-network.json'
    try:
        with path.open(encoding='utf-8') as source:
            raw = source.read(2049)
        if len(raw) > 2048:
            return None
        record = decode_network(raw)
        if record['node_id'] != node_id or type(record.get('bridge_epoch')) is not int or not record['bridge_epoch']:
            return None
        seen = record.get('seen_monotonic')
        if type(seen) not in (int, float):
            return None
        age = clock() - seen
        if age < 0:
            return None  # Stale monotonic timestamp from a previous OS boot.
        return dict(status=record['payload'], age_s=round(age, 1), fresh=age < 12)
    except (OSError, ValueError, TypeError):
        return None
