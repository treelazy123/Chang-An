"""Service regressions without production brokers, serial ports or firmware."""
from concurrent.futures import Future
import json
from pathlib import Path
import tempfile
import threading
import unittest

from changan_ugv.agents.services import HostServices
from changan_ugv.nodes.inventory import defaults
from changan_ugv.protocol.frames import encode
from changan_ugv.service.requests import Requests
from changan_ugv.tasks.ports import NodeSnapshot, SendReceipt
from changan_ugv.tasks.runtime import Runtime


class Channel:
    def __init__(self):
        self.online = True
        self.ready = True
        self.sent = []
    def is_connected(self):return self.online
    def ready_count(self):return int(self.ready)
    def snapshot(self, node):return NodeSnapshot(self.ready, 'device-boot', ('diagnostics',))
    def send(self, node, packet):self.sent.append(packet);return SendReceipt(True)
    def notify(self, owner, packet):encode(packet);return SendReceipt(True)


class HostServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.now = 1000.
        self.index = 0
        self.channel = Channel()
        self.inventory = defaults()
        self.probes = []
        self.probe_error = None
        def probe(node, op, **kwargs):
            self.probes.append((node,op,kwargs))
            if self.probe_error:raise self.probe_error
            self.now += .012
            return dict(ok=True)
        self.root = Path(self.temp.name)
        self.runtime = Runtime(self.channel, database=self.root/'tasks.db',
            executor_factory=lambda emit,snapshot:HostServices(self.root/'journal.json','ugv-001',emit,snapshot,
                probe=probe, network_snapshot=lambda node:dict(ready=self.channel.ready), monotonic=lambda:self.now,probe_clock=lambda:self.now),
            inventory_loader=lambda:self.inventory)
        self.runtime.store.clock = lambda:self.now
        self.addCleanup(self.runtime.close)

    def call(self, message_type, owner='pc-root-001', **fields):
        self.index += 1
        reply = self.runtime.handle(dict(v=1,type=message_type,msg_id=str(self.index),**fields),owner)
        encode(reply)
        return reply

    def create(self, task, kind, **config):
        return self.call('task.create',task_id=task,target='ugv-001',kind=kind,
                         config=dict(duration_s=10,period_ms=200,**config))

    def control(self, task, op):
        self.call('task.control',task_id=task,op=op,expected_revision=1)
        self.runtime.tick()

    def row(self, task):return self.call('task.get',task_id=task)['task']

    def test_real_probe_outcomes_and_rtt_excludes_car(self):
        actor = self.runtime.local
        config = dict(probe_node='micro-001')
        success = actor.network_sample(config)
        self.assertEqual(12,success['rtt_ms'])
        self.assertEqual([('micro-001','ping',dict(timeout=1))],self.probes)
        self.probe_error = TimeoutError()
        self.assertEqual('probe_timeout',actor.network_sample(config)['error'])
        self.probe_error = OSError()
        self.assertEqual('probe_failed',actor.network_sample(config)['error'])
        self.channel.ready = False
        self.assertEqual('node_not_ready',actor.network_sample(config)['error'])
        self.assertEqual(3,len(self.probes))

    def test_probe_does_not_block_pause_or_monitor_and_late_cancel_is_ignored(self):
        entered,release = threading.Event(),threading.Event()
        def blocking(*args,**kwargs):
            entered.set()
            release.wait(2)
            return dict(ok=True)
        self.runtime.local.probe = blocking
        self.create('net','network_diagnostics',probe_node='micro-001')
        self.control('net','start')
        self.runtime.tick()
        self.assertTrue(entered.wait(1))
        try:
            self.create('watch','task_monitor',watch_task_id='net',stale_after_s=2)
            self.control('watch','start')
            self.runtime.tick()
            self.assertEqual('RUNNING',self.row('net')['state'])
            self.assertEqual('RUNNING',self.row('watch')['state'])
            self.control('net','pause')
            self.assertEqual('PAUSED',self.row('net')['state'])
            self.control('net','resume')
            self.control('net','cancel')
            self.assertEqual('CANCELLED',self.row('net')['state'])
        finally:release.set()
        service = self.runtime.local.actors['network_diagnostics']
        service.pending[0].result(timeout=2)
        self.runtime.tick()
        self.assertEqual(0,service.row['samples'])

    def test_monitor_uses_feedback_age_not_manager_update_and_sees_terminal_failure(self):
        self.call('task.create',task_id='remote',target='micro-001',kind='diagnostics')
        self.assertEqual('waiting',self.runtime.monitor_snapshot('remote',2)['health'])
        self.control('remote','start')
        p = self.channel.sent[-1]
        event = dict(v=1,type='task.event',node_id='micro-001',task_id='remote',msg_id=p['msg_id'],
                     boot_id='device-boot',revision=1,state='RUNNING',seq=1,progress=35)
        self.assertTrue(self.runtime.receive('micro-001',event))
        self.assertEqual('reporting',self.runtime.monitor_snapshot('remote',2)['health'])
        self.now += 3
        with self.runtime.store.lock,self.runtime.store.db:
            self.runtime.store._change('remote',error='manager_change_only')
        self.assertEqual('feedback_stale',self.runtime.monitor_snapshot('remote',2)['health'])
        self.assertEqual(3,self.runtime.monitor_snapshot('remote',2)['age_s'])
        sample = self.runtime.monitor_snapshot('remote',2)
        self.assertEqual(('feedback_stale',35,3),(sample['health'],sample['progress'],sample['age_s']))
        self.channel.ready = False
        self.assertEqual('node_not_ready',self.runtime.monitor_snapshot('remote',2)['health'])
        self.channel.ready = True
        self.assertTrue(self.runtime.receive('micro-001',dict(event,seq=2,state='FAILED',error='test_failure')))
        result = self.runtime.monitor_snapshot('remote',2)
        self.assertEqual(('finished','FAILED','test_failure'),(result['health'],result['state'],result['error']))

    def test_permissions_config_update_and_target_separation(self):
        for target in ('micro-001','missing'):
            with self.assertRaisesRegex(ValueError,'host_service_requires_ugv'):
                self.call('task.create',task_id='bad',target=target,kind='network_diagnostics',config=dict(probe_node='micro-001'))
        with self.assertRaisesRegex(ValueError,'probe_node_not_authorized'):
            self.create('bad','network_diagnostics',probe_node='stranger')
        with self.assertRaisesRegex(ValueError,'probe_requires_remote_node'):
            self.create('bad','network_diagnostics',probe_node='ugv-001')
        with self.assertRaises(ValueError):
            self.call('task.create',task_id='bad',target='ugv-001',kind='network_diagnostics',config=[])
        self.call('task.create',task_id='private',target='micro-001',kind='diagnostics',owner='local-console')
        with self.assertRaisesRegex(ValueError,'task_not_found'):
            self.create('bad','task_monitor',watch_task_id='private')
        self.create('net','network_diagnostics',probe_node='micro-001')
        self.call('task.update',task_id='net',expected_revision=1,config=dict(probe_node='uav-001',duration_s=20))
        self.assertEqual('uav-001',self.row('net')['config']['probe_node'])
        self.create('watch','task_monitor',watch_task_id='net',stale_after_s=2)
        with self.assertRaisesRegex(ValueError,'cannot_monitor_monitor'):
            self.create('recursive','task_monitor',watch_task_id='watch')
        self.inventory['nodes'] = [n for n in self.inventory['nodes'] if n['node_id'] != 'ugv-001']
        self.assertEqual('not_authorized',self.runtime.monitor_snapshot('net',2)['health'])

    def test_service_discovery_live_status_and_same_kind_queue(self):
        services = self.runtime.service_snapshot('pc-root-001')
        self.assertEqual({'network_diagnostics','task_monitor','patrol','anomaly_review'},{s['service_type'] for s in services})
        self.create('net','network_diagnostics',probe_node='micro-001')
        self.control('net','start')
        self.create('queued','network_diagnostics',probe_node='uav-001')
        self.control('queued','start')
        self.assertEqual('QUEUED',self.row('queued')['state'])
        self.assertEqual('busy',self.runtime.service_snapshot('pc-root-001')[0]['availability'])
        self.channel.online = False
        self.assertEqual('unavailable',self.runtime.service_snapshot('pc-root-001')[0]['availability'])
        # Existing list framing transports service rows without a new firmware request type.
        class Controller:
            def refresh_inventory(self):pass
        c = Controller()
        c.connected = threading.Event();c.connected.set()
        c.condition = threading.RLock()
        c.registry = type('Registry',(),{'snapshot':lambda self:[]})()
        c.tasks = self.runtime
        request = Requests(c,clock=lambda:1000,inventory_loader=lambda:self.inventory)
        replies = request.handle(dict(v=1,type='list',scope='services',msg_id='a',node_id='pc-root-001',deadline_unix=1020),'pc-root-001')
        self.assertEqual(len(services)+1,len(replies))
        for reply in replies:encode(reply)

    def test_results_events_and_worst_case_frames_fit_and_restart_never_replays(self):
        self.create('net','network_diagnostics',probe_node='micro-001')
        self.control('net','start')
        actor = self.runtime.local.actors['network_diagnostics']
        actor.collect(dict(ready=True,rtt_ms=12))
        actor.collect(dict(ready=True,error='probe_timeout'))
        actor.report()
        result = self.row('net')['result']
        self.assertEqual((2,1,1,12),(result['samples'],result['ok'],result['failed'],result['avg_ms']))
        history=self.call('task.events',cursor=0)
        while history['more']:
            history=self.call('task.events',cursor=history['cursor'])
        self.assertEqual(result,history['items'][0]['result'])
        # Persisted journals recover as UNKNOWN and never launch a probe automatically.
        calls=len(self.probes)
        restored=HostServices(self.root/'journal.json','ugv-001',lambda _:None,lambda:0,
            probe=lambda *a,**k:self.fail('Restart replayed a probe'),network_snapshot=lambda _:dict(ready=True))
        try:
            self.assertEqual('UNKNOWN',restored.actors['network_diagnostics'].row['state'])
            restored.tick(True)
        finally:restored.close()
        self.assertEqual(calls,len(self.probes))
        # Exercise long identifiers and maximum-size task errors within the serial budget.
        task='t'*32
        self.call('task.create',task_id=task,target='micro-001',kind='diagnostics')
        with self.runtime.store.lock,self.runtime.store.db:
            self.runtime.store._change(task,state='FAILED',error='错'*64)
        monitor='m'*32
        self.create(monitor,'task_monitor',watch_task_id=task,stale_after_s=3600)
        self.control(monitor,'start')
        self.runtime.tick()
        self.assertEqual('finished',self.runtime.local.actors['task_monitor'].result()['health'])
        row=self.row(monitor)
        self.assertLessEqual(len(encode(dict(v=1,type='task.reply',msg_id='x'*64,node_id='ugv-service',ok=True,task=row))),1032)


if __name__ == '__main__':unittest.main()
