"""UGV host diagnostics executor, runs on the PC now and Jetson later."""
import json
from pathlib import Path
import time
import uuid
from task_store import TERMINAL,dumps

class HostDiagnostics:
    """Actual host/service sampling, not simulated C6 or navigation telemetry."""
    def __init__(self, path, node, emit, snapshot, monotonic=time.monotonic):
        self.path, self.node, self.emit, self.snapshot = Path(path), node, emit, snapshot
        self.monotonic = monotonic
        self.boot = uuid.uuid4().hex[:16]
        self.row = json.loads(self.path.read_text()) if self.path.exists() else None
        if self.row and self.row['state'] not in TERMINAL:
            self.row['state'] = 'UNKNOWN'
        if self.row:
            self.row['seq'] = 0
        self.sequence=0
        self.last = monotonic()
        self.sample_at = self.last
        self.report_at = self.last

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix('.tmp')
        temp.write_text(dumps(self.row), encoding='utf-8')
        temp.replace(self.path)

    def report(self, msg_id=None, task_id=None, revision=1):
        self.sequence+=1
        if self.row is None or (task_id is not None and task_id != self.row['task_id']):
            self.emit(dict(v=1, type='task.event', node_id=self.node, task_id=task_id,
                           msg_id=msg_id, revision=revision, boot_id=self.boot, seq=self.sequence,
                           state='NOT_FOUND', progress=0, error='agent_task_not_found'))
            return
        row = self.row
        row['seq'] = self.sequence
        self.emit(dict(v=1, type='task.event', node_id=self.node, task_id=row['task_id'],
                       msg_id=msg_id or row['command_id'], revision=row['revision'], boot_id=self.boot,
                       seq=row['seq'], state=row['state'], progress=min(100,int(row['elapsed']*100/(row['config']['duration_s']*1000))),
                       result=dict(source='ugv_host', samples=row['samples'], ready_nodes=row.get('ready_nodes',0))))

    def handle(self, packet):
        op = packet['op']
        if op == 'query':
            self.report(packet['msg_id'], packet['task_id'], packet['revision'])
            return
        sequence=packet.get('op_seq')
        if type(sequence) is not int or sequence<1:return
        if self.row and self.row['task_id']==packet['task_id'] and sequence<=self.row.get('op_seq',0):
            self.report(packet['msg_id'],packet['task_id'],packet['revision'])
            return
        if self.row and self.row['command_id'] == packet['msg_id']:
            self.report()
            return
        if op == 'start':
            if self.row and (self.row['state'] not in TERMINAL or self.row['task_id']==packet['task_id']):
                self.report(packet['msg_id'],packet['task_id'],packet['revision'])
                return
            self.row = dict(task_id=packet['task_id'], command_id=packet['msg_id'], revision=packet['revision'],
                            config=packet['config'], op_seq=sequence, state='ACCEPTED', elapsed=0, samples=0, seq=0)
            self.save()
            self.report()
            self.row['state'] = 'RUNNING'
            self.last = self.monotonic()
            self.sample_at = self.last
        elif op=='cancel' and (not self.row or (self.row['state'] in TERMINAL and self.row['task_id']!=packet['task_id'])):
            self.row=dict(task_id=packet['task_id'],command_id=packet['msg_id'],revision=packet['revision'],
                          config=dict(duration_s=1,period_ms=1000),state='CANCELLED',elapsed=0,samples=0,seq=0)
        elif self.row and self.row['task_id'] == packet['task_id']:
            row = self.row
            if op == 'pause' and row['state'] == 'RUNNING':
                row['state'] = 'PAUSED'
            elif op == 'resume' and row['state'] == 'PAUSED':
                row['state'] = 'RUNNING'
                self.last = self.monotonic()
            elif op == 'cancel' and row['state'] not in TERMINAL:
                row['state'] = 'CANCELLED'
            else:
                self.report(packet['msg_id'])
                return
            row['command_id'] = packet['msg_id']
        else:
            self.report(packet['msg_id'], packet['task_id'], packet['revision'])
            return
        self.row['op_seq']=sequence
        self.save()
        self.report()

    def tick(self, connected):
        now = self.monotonic()
        delta = max(0, now-self.last)*1000
        self.last = now
        row = self.row
        if not row:
            return
        if row['state'] == 'RUNNING':
            row['elapsed'] += delta
            if not connected:
                row['state'] = 'PAUSED'
                self.save()
            else:
                if now >= self.sample_at:
                    row['samples'] += 1
                    row['ready_nodes'] = self.snapshot()
                    self.sample_at = now+row['config']['period_ms']/1000
                if row['elapsed'] >= row['config']['duration_s']*1000:
                    row['state'] = 'SUCCEEDED'
                    self.save()
        if now >= self.report_at:
            self.report()
            self.report_at = now+1

