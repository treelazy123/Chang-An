"""Persist registered node observations using the task store's connection and lock.

Administrator inventory managed by UGV Service plus broker mTLS are the trust authority.
Stored observations are diagnostic history and never grant permissions.
"""
import json
import time
from changan_ugv.nodes.inventory import root_of

class NodeCatalog:
    def __init__(self, store):
        self.store=store
        with store.lock,store.db:
            store.db.execute('''CREATE TABLE IF NOT EXISTS node_catalog (
                node_id TEXT PRIMARY KEY, root_id TEXT NOT NULL, registration TEXT NOT NULL,
                observation TEXT, observed_at REAL, registered INTEGER NOT NULL)''')

    def update(self, entries, snapshots):
        observed={e['node_id']:e for e in snapshots}
        with self.store.lock,self.store.db:
            self.store.db.execute('UPDATE node_catalog SET registered=0')
            for entry in entries:
                snapshot=observed.get(entry['node_id'])
                self.store.db.execute('''INSERT INTO node_catalog VALUES(?,?,?,?,?,1)
                    ON CONFLICT(node_id) DO UPDATE SET root_id=excluded.root_id,
                    registration=excluded.registration, observation=excluded.observation,
                    observed_at=excluded.observed_at, registered=1''',
                    (entry['node_id'],root_of(entry),json.dumps(entry),
                     json.dumps(snapshot) if snapshot is not None else None,
                     time.time() if snapshot is not None else None))

    def records(self):
        with self.store.lock:
            rows=self.store.db.execute('SELECT * FROM node_catalog ORDER BY node_id').fetchall()
            return [dict(node_id=r['node_id'],root_id=r['root_id'],registered=bool(r['registered']),
                         registration=json.loads(r['registration']),
                         last_observation=json.loads(r['observation']) if r['observation'] else None,
                         observed_at=r['observed_at']) for r in rows]
