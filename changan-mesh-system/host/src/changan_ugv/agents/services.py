"""Host-only network probes and task monitoring; no device firmware changes."""
from concurrent.futures import ThreadPoolExecutor
import time
import uuid

from changan_ugv.agents.ugv import HostDiagnostics
from changan_ugv.tasks.store import HOST_KINDS


class SamplingService(HostDiagnostics):
    def __init__(self, *args, kind, sample, **kwargs):
        super().__init__(*args, **kwargs)
        self.kind, self.sample = kind, sample
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='network-probe') if kind == 'network_diagnostics' else None
        self.pending = None

    def report(self, msg_id=None, task_id=None, revision=1):
        if self.row is None or (task_id is not None and task_id != self.row['task_id']):
            return super().report(msg_id, task_id, revision)
        self.sequence += 1
        row = self.row
        self.emit(dict(v=1, type='task.event', node_id=self.node, task_id=row['task_id'],
                       msg_id=msg_id or row['command_id'], revision=row['revision'], boot_id=self.boot,
                       seq=self.sequence, state=row['state'],
                       progress=min(100, int(row['elapsed'] * 100 / (row['config']['duration_s'] * 1000))),
                       result=self.result()))

    def result(self):
        row = self.row
        if self.kind == 'task_monitor':
            return row.get('metrics', dict(task_id=row['config']['watch_task_id'], health='waiting'))
        m = row.get('metrics', {})
        ok = m.get('ok', 0)
        return dict(node_id=row['config']['probe_node'], samples=row['samples'], ok=ok,
                    failed=m.get('failed', 0), last_ms=m.get('last_ms'),
                    avg_ms=round(m.get('total_ms', 0) / ok, 2) if ok else None,
                    max_ms=m.get('max_ms'), ready=m.get('ready'), error=m.get('error'))

    def collect(self, value):
        row = self.row
        row['samples'] += 1
        if self.kind == 'task_monitor':
            row['metrics'] = value
        else:
            m = row.setdefault('metrics', dict(ok=0, failed=0, total_ms=0))
            m.update(ready=value['ready'], error=value.get('error'), last_ms=value.get('rtt_ms'))
            if value.get('rtt_ms') is not None:
                m['ok'] += 1
                m['total_ms'] += value['rtt_ms']
                m['max_ms'] = max(m.get('max_ms', 0), value['rtt_ms'])
            else:
                m['failed'] += 1
        self.save()

    def tick(self, connected):
        now = self.monotonic()
        delta = max(0, now - self.last) * 1000
        self.last = now
        row = self.row
        if self.pending is not None and self.pending[0].done():
            future, task_id = self.pending
            self.pending = None
            # Never apply a late probe to a cancelled/replaced task.
            if row and row['task_id'] == task_id and row['state'] in ('RUNNING', 'PAUSED'):
                self.collect(future.result())
        if row is None:
            return
        if row['state'] == 'RUNNING':
            row['elapsed'] += delta
            if not connected:
                row['state'] = 'PAUSED'
                self.save()
            elif row['elapsed'] >= row['config']['duration_s'] * 1000:
                # Include the final in-flight probe before reporting completion.
                if self.pending is None:
                    row['state'] = 'SUCCEEDED'
                    self.save()
            elif now >= self.sample_at and self.pending is None:
                if self.pool:
                    self.pending = (self.pool.submit(self.sample, dict(row['config'])), row['task_id'])
                else:
                    self.collect(self.sample(dict(row['config'])))
                self.sample_at = now + row['config']['period_ms'] / 1000
        if now >= self.report_at:
            self.report()
            self.report_at = now + 1

    def close(self):
        if self.pool:
            self.pool.shutdown(wait=True, cancel_futures=True)


class HostServices:
    concurrent_kinds = HOST_KINDS

    def __init__(self, path, node, emit, snapshot, *, probe, network_snapshot, monotonic=time.monotonic, probe_clock=time.perf_counter):
        self.boot = uuid.uuid4().hex[:16]
        self.monotonic = monotonic
        self.probe_clock = probe_clock
        self.probe, self.network_snapshot = probe, network_snapshot
        self.monitor = None
        self.actors = {'diagnostics': HostDiagnostics(path, node, emit, snapshot, monotonic)}
        for kind in HOST_KINDS:
            sample = self.network_sample if kind == 'network_diagnostics' else self.monitor_sample
            self.actors[kind] = SamplingService(str(path) + '.' + kind, node, emit, snapshot,
                                               monotonic=monotonic, kind=kind, sample=sample)
        for actor in self.actors.values():
            actor.boot = self.boot

    def bind_runtime(self, runtime):
        self.monitor = runtime.monitor_snapshot

    def network_sample(self, config):
        node = config['probe_node']
        snapshot = self.network_snapshot(node)
        if snapshot is None:
            return dict(ready=False, error='node_not_authorized')
        if not snapshot['ready']:
            return dict(ready=False, error='node_not_ready')
        started = self.probe_clock()
        try:
            reply = self.probe(node, 'ping', timeout=4)
            if reply.get('ok') is not True:
                return dict(ready=True, error='negative_ack')
            return dict(ready=True, rtt_ms=round((self.probe_clock() - started) * 1000, 2))
        except TimeoutError:
            return dict(ready=True, error='probe_timeout')
        except (OSError, ValueError):
            return dict(ready=True, error='probe_failed')

    def monitor_sample(self, config):
        return self.monitor(config['watch_task_id'], config['stale_after_s'])

    def handle(self, packet):
        if packet['op'] == 'start':
            actor = self.actors.get(packet.get('kind'))
        else:
            actor = next((a for a in self.actors.values() if a.row and a.row['task_id'] == packet['task_id']), None)
        if actor is None:
            # Emit NOT_FOUND for reconciliation rather than replaying a start.
            actor = self.actors['diagnostics']
        actor.handle(packet)

    def tick(self, connected):
        for actor in self.actors.values():
            actor.tick(connected)

    def close(self):
        for actor in self.actors.values():
            actor.close()
