"""Keep certificate dependencies in the uv host environment, separate from IDF Python."""
import json
import os
from pathlib import Path
import subprocess

def crypto_available():
    try:
        from cryptography import x509  # noqa: F401
        return True
    except ImportError:
        return False

def apply_identity(root,role,node_id,ugv_id=None,check_only=False):
    from node_inventory import load_inventory
    from node_identity import check_identity,enroll
    if not check_only:
        return enroll(root,role,node_id,ugv_id)
    entry=next((e for e in load_inventory(root)['nodes'] if e['node_id']==node_id),None)
    if not entry or entry['role']!=role or not entry.get('enabled',True):
        raise ValueError('Device must be enrolled with this role and enabled before monitor')
    return dict(entry,created=False,certificate_sha256=check_identity(root,node_id))

def ensure_identity(root,role,node_id,ugv_id=None,check_only=False,host_python=None):
    root=Path(root).resolve()
    if crypto_available():
        return apply_identity(root,role,node_id,ugv_id,check_only)
    executable=Path(host_python) if host_python else root/'.venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    if not executable.is_file():
        raise ValueError('Certificate operations require the uv host environment. Run uv sync --locked in the project directory; do not install cryptography into IDF Python.')
    worker=Path(__file__).with_name('identity_worker.py')
    command=[str(executable),'-X','utf8',str(worker),'--root',str(root),'--role',role,'--node-id',node_id]
    if ugv_id:command+=['--ugv-id',ugv_id]
    if check_only:command+=['--check-only']
    env=dict(os.environ)
    for name in ('PYTHONHOME','PYTHONPATH'):
        env.pop(name,None)
    env.update(PYTHONUTF8='1',PYTHONNOUSERSITE='1')
    options={'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {}
    try:
        result=subprocess.run(command,cwd=root,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                              encoding='utf-8',errors='replace',timeout=60,**options)
    except subprocess.TimeoutExpired as exc:
        raise ValueError('Host certificate operation timed out; IDF was not started') from exc
    if result.returncode:
        raise ValueError('Host certificate operation failed: '+(result.stderr.strip() or result.stdout.strip() or str(result.returncode)))
    try:record=json.loads(result.stdout)
    except ValueError as exc:raise ValueError('Invalid response from host certificate worker') from exc
    if (not isinstance(record,dict) or record.get('node_id')!=node_id or record.get('role')!=role
            or type(record.get('created')) is not bool or not record.get('certificate_sha256')):
        raise ValueError('Host certificate worker returned a different device identity')
    print('Certificate operations: project uv .venv (IDF Python unchanged)',flush=True)
    return record
