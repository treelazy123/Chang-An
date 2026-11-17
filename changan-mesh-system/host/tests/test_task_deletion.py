"""Terminal history deletion, replay safety and incremental cursors."""
import json
from pathlib import Path
import tempfile
import unittest

from changan_ugv.tasks.store import Store, TERMINAL
from changan_ugv.protocol.frames import encode


class TaskDeletion(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'tasks.db'
        self.store=Store(self.path,clock=lambda:1000)
        self.addCleanup(lambda:self.store.close())
        self.index=0
        self.targets={'micro-001','ugv-001'}

    def packet(self, message_type, **fields):
        self.index+=1
        return dict(v=1,type=message_type,msg_id=str(self.index),deadline_unix=1020,**fields)

    def call(self, message_type, owner='car', **fields):
        return self.store.request(self.packet(message_type,**fields),owner,self.targets)

    def create(self, task='history'):
        p=self.packet('task.create',task_id=task,target='micro-001',kind='diagnostics')
        self.store.request(p,'car',self.targets)
        return p

    def finish(self, task='history', state='CANCELLED'):
        with self.store.lock,self.store.db:self.store._change(task,state=state)

    def delete(self, task='history', **fields):
        return self.call('task.control',task_id=task,op='delete',expected_revision=1,**fields)

    def test_terminal_delete_cleans_payloads_and_notifies_other_clients(self):
        create=self.create()
        self.call('task.control',task_id='history',op='start',expected_revision=1)
        self.finish()
        before=self.call('task.events',cursor=0)['cursor']
        reply=self.delete()
        self.assertTrue(reply['deleted'])
        encode(reply)
        for table in ('tasks','operations'):
            self.assertEqual(0,self.store.db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0])
        events=self.call('task.events',cursor=before)['items']
        self.assertEqual(['DELETED'],[e['state'] for e in events])
        self.assertEqual([],self.call('task.list')['items'])
        with self.assertRaisesRegex(ValueError,'task_not_found'):
            self.call('task.get',task_id='history')
        replay=self.store.request(create,'car',self.targets)
        self.assertTrue(replay['deleted'])
        self.assertNotIn('task',replay)
        self.assertFalse(self.store.receive('micro-001',dict(v=1,type='task.event',node_id='micro-001',
            task_id='history',msg_id='late',boot_id='boot',revision=1,seq=99,state='RUNNING',progress=0)))

    def test_active_created_queued_and_unknown_cannot_be_deleted(self):
        self.create()
        for state in ('CREATED','QUEUED','DISPATCHING','RUNNING','PAUSED','RECONCILING','UNKNOWN'):
            self.finish(state=state)
            with self.assertRaisesRegex(ValueError,'delete_requires_terminal'):self.delete()
        self.assertEqual(1,self.store.db.execute('SELECT COUNT(*) FROM tasks').fetchone()[0])

    def test_all_terminal_states_are_deletable(self):
        for state in TERMINAL:
            self.create(state)
            self.finish(state,state)
            self.assertTrue(self.delete(state)['deleted'])

    def test_ownership_revision_and_deleted_id_reuse(self):
        self.create();self.finish()
        with self.assertRaisesRegex(ValueError,'task_not_found'):self.delete(owner='another-car')
        with self.assertRaisesRegex(ValueError,'revision_conflict'):
            self.call('task.control',task_id='history',op='delete',expected_revision=True)
        self.assertTrue(self.delete()['deleted'])
        with self.assertRaisesRegex(ValueError,'task_not_found'):self.delete(owner='another-car')
        with self.assertRaisesRegex(ValueError,'task_id_deleted'):self.create()

    def test_delete_is_durable_idempotent_and_does_not_remove_other_tasks(self):
        self.create();self.finish();self.create('other')
        packet=self.packet('task.control',task_id='history',op='delete',expected_revision=1)
        reply=self.store.request(packet,'car',self.targets)
        self.assertEqual(reply,self.store.request(packet,'car',self.targets))
        self.assertTrue(self.delete()['deleted'])
        self.assertEqual(1,self.store.db.execute('SELECT COUNT(*) FROM task_events WHERE task_id=?',('history',)).fetchone()[0])
        self.store.close();self.store=Store(self.path)
        self.assertEqual(reply,self.store.request(packet,'car',self.targets))
        self.assertEqual('other',self.call('task.list')['items'][0]['task_id'])
        with self.assertRaisesRegex(ValueError,'msg_id_conflict'):
            self.store.request(dict(packet,expected_revision=2),'car',self.targets)

    def test_running_or_waiting_monitor_prevents_deletion(self):
        self.create();self.finish()
        self.call('task.create',task_id='monitor',target='ugv-001',kind='task_monitor',config=dict(watch_task_id='history'))
        with self.assertRaisesRegex(ValueError,'task_in_use_by_monitor'):self.delete()
        self.finish('monitor')
        self.assertTrue(self.delete()['deleted'])
        # The completed monitor's historical summary is retained.
        self.assertEqual('monitor',self.call('task.get',task_id='monitor')['task']['task_id'])

    def test_deleting_highest_task_never_reuses_list_cursor(self):
        self.create();cursor=self.call('task.list')['cursor']
        self.finish();self.delete();self.create('new')
        page=self.call('task.list',cursor=cursor)
        self.assertGreater(page['cursor'],cursor)
        self.assertEqual('new',page['items'][0]['task_id'])

    def test_failed_reply_encoding_rolls_back_entire_deletion(self):
        from unittest.mock import patch
        self.create();self.finish()
        with patch('changan_ugv.protocol.frames.encode',side_effect=ValueError('encoding')):
            with self.assertRaisesRegex(ValueError,'encoding'):self.delete()
        self.assertEqual('history',self.call('task.get',task_id='history')['task']['task_id'])
        self.assertEqual(0,self.store.db.execute('SELECT COUNT(*) FROM deleted_tasks').fetchone()[0])


if __name__=='__main__':unittest.main()
