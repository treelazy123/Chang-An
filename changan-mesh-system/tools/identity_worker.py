"""JSON-only certificate worker for tools/lab.py; never invokes IDF or serial tools."""
import argparse
import json
from pathlib import Path
from identity_env import apply_identity

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',required=True,type=Path)
    parser.add_argument('--role',required=True,choices=('pc_root','ugv','uav','micro_uav'))
    parser.add_argument('--node-id',required=True)
    parser.add_argument('--ugv-id')
    parser.add_argument('--check-only',action='store_true')
    args=parser.parse_args()
    try:result=apply_identity(args.root,args.role,args.node_id,args.ugv_id,args.check_only)
    except ImportError:
        parser.exit(2,'Host Python dependencies are missing. Run uv sync --locked in the project directory.\n')
    except (ValueError,OSError) as exc:
        parser.exit(2,str(exc)+'\n')
    print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
