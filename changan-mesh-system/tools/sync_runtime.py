"""Copy stopped UGV runtime into this repository, preserving keys and making a backup.

No process is stopped, no COM port is opened, and no certificate is issued.
"""
import argparse
from contextlib import ExitStack, contextmanager, closing
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import sqlite3
from _bootstrap import bootstrap
bootstrap()
from changan_ugv.nodes.inventory import validate, write_inventory, write_acl

@contextmanager
def stopped_service(root):
    path=Path(root)/'secrets/.controller.lock'
    # Same byte-range lock as the actual Controller. Keep it held throughout sync.
    with path.open('a+b') as stream:
        stream.seek(0,2)
        if not stream.tell():stream.write(b'0');stream.flush()
        stream.seek(0)
        try:
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError as exc:
            raise ValueError('UGV controller is running in '+str(root)+'; stop it before syncing') from exc
        yield

def backup_database(source,destination):
    destination.parent.mkdir(parents=True,exist_ok=True)
    with closing(sqlite3.connect(source.as_uri()+'?mode=ro',uri=True)) as src:
        # Handle the target through SQLite too; never replace an SQLite main file
        # while leaving old -wal/-shm files alongside it.
        dst=sqlite3.connect(destination)
        try:
            src.backup(dst)
            if dst.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
                raise ValueError('Database integrity check failed')
        finally:dst.close()

def sync_runtime(source,target):
    source,target=Path(source).resolve(),Path(target).resolve()
    if source==target or source in target.parents or target in source.parents:
        raise ValueError('Source and target must be separate repositories')
    source_runtime=source/'runtime/ugv-root'
    inventory_path=source/'config/nodes.json'
    inventory=validate(json.loads(inventory_path.read_text(encoding='utf-8')))
    for root in (source,target):
        if not (root/'secrets/ca.pem').is_file():raise ValueError('Missing existing CA in '+str(root))
    if (source/'secrets/ca.pem').read_bytes()!=(target/'secrets/ca.pem').read_bytes():
        raise ValueError('CA differs; refusing to mix identities')
    with ExitStack() as locks:
        for root in sorted((source,target),key=str):locks.enter_context(stopped_service(root))
        copies=[]
        for path in (source/'secrets').rglob('*'):
            rel=path.relative_to(source/'secrets')
            if not path.is_file() or path.name.endswith('.lock') or 'build' in rel.parts:continue
            dest=target/'secrets'/rel
            if dest.exists() and path.name in ('ca.pem','ca.key','client.pem','client.key') and dest.read_bytes()!=path.read_bytes():
                raise ValueError('Existing key/certificate differs: '+str(rel))
            copies.append((path,dest))
        database=source_runtime/'tasks.sqlite3'
        if not database.is_file():raise ValueError('Missing source task database')
        # Validate source before touching the destination.
        with closing(sqlite3.connect(database.as_uri()+'?mode=ro',uri=True)) as db:
            if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Invalid source database')
        runtime=target/'runtime/ugv-root';runtime.mkdir(parents=True,exist_ok=True)
        backup=runtime/'backups'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
        backup.mkdir(parents=True)
        if (runtime/'tasks.sqlite3').exists():backup_database(runtime/'tasks.sqlite3',backup/'tasks.sqlite3')
        for name in ('agent.json','mosquitto.conf','acl.conf'):
            if (runtime/name).exists():shutil.copy2(runtime/name,backup/name)
        if (target/'config/nodes.json').exists():shutil.copy2(target/'config/nodes.json',backup/'nodes.json')
        for path,dest in copies:
            dest.parent.mkdir(parents=True,exist_ok=True)
            if not dest.exists():shutil.copy2(path,dest)
            elif path.name=='clock.defaults':shutil.copy2(path,dest)
        backup_database(database,runtime/'tasks.sqlite3')
        journal=source_runtime/'agent.json'
        if journal.exists():shutil.copy2(journal,runtime/journal.name)
        elif (runtime/journal.name).exists():(runtime/journal.name).rename(backup/'stale-agent.json')
        write_inventory(target,inventory);write_acl(target,inventory)
        config=(source_runtime/'mosquitto.conf').read_text(encoding='utf-8')
        config=config.replace(source.as_posix(),target.as_posix()).replace(str(source),str(target))
        (runtime/'mosquitto.conf').write_text(config,encoding='utf-8')
        return backup

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True,type=Path)
    args=parser.parse_args()
    try:backup=sync_runtime(args.source,Path(__file__).resolve().parents[1])
    except (OSError,ValueError,sqlite3.Error) as exc:parser.exit(2,str(exc)+'\n')
    print('Runtime synchronized; prior target state backed up at '+str(backup))
if __name__=='__main__':main()
