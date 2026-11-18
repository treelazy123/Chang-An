"""Verify all registered role declarations; compile only with explicit --build."""
import argparse
from pathlib import Path
import subprocess
import sys
from _bootstrap import bootstrap
bootstrap()
from changan_ugv.nodes.inventory import load_inventory
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build',action='store_true',help='Actually invoke IDF builds (user-operated only)')
    args=p.parse_args();root=Path(__file__).resolve().parents[1]
    for node in load_inventory(root)['nodes']:
        if not node.get('enabled',True):continue
        command=[sys.executable,str(root/'tools/lab.py'),'--role',node['role'],'--node-id',node['node_id']]
        command+=['build'] if args.build else ['--dry-run']
        result=subprocess.run(command,cwd=root)
        if result.returncode:return result.returncode
    return 0
if __name__=='__main__':raise SystemExit(main())
