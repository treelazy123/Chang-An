"""Read existing application images and their compiled partition tables. Never builds or opens a serial port."""
import argparse
import json
from pathlib import Path
import struct
ENTRY=struct.Struct('<HBBII16sI')
ROLES=('ugv_root','ugv','uav','micro_uav')
def inspect(directory):
    directory=Path(directory)
    image=directory/'mesh_lite_node.bin'
    table=directory/'partition_table/partition-table.bin'
    missing=[str(p) for p in (image,table) if not p.is_file()]
    if missing: return {'directory':str(directory),'status':'MISSING','missing':missing}
    raw=table.read_bytes();factory=None
    for offset in range(0,len(raw)-ENTRY.size+1,ENTRY.size):
        magic,kind,subtype,start,size,label,flags=ENTRY.unpack_from(raw,offset)
        if magic in (0xffff,0xebeb): break
        if magic!=0x50aa: raise ValueError('Invalid partition-table entry in '+str(table))
        if kind==0 and subtype==0:
            factory=(start,size,label.split(b'\0')[0].decode('ascii'))
    if factory is None: raise ValueError('No factory application partition in '+str(table))
    offset,capacity,label=factory
    used=image.stat().st_size
    return {'directory':str(directory),'status':'PASS' if used<=capacity else 'FAIL',
            'image_bytes':used,'partition':label,'partition_offset':offset,
            'partition_bytes':capacity,'free_app_bytes':capacity-used,
            'used_percent':round(100*used/capacity,2)}
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-dir',type=Path,help='Check one existing role build directory')
    parser.add_argument('--json',action='store_true')
    parser.add_argument('--node-id',help='Check the isolated build of one enrolled device')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    from node_inventory import load_inventory, DEFAULT_IDS
    if args.build_dir and args.node_id:parser.error('Use --build-dir or --node-id, not both')
    nodes=[e for e in load_inventory(root)['nodes'] if e.get('enabled',True)]
    if args.node_id:
        nodes=[e for e in nodes if e['node_id']==args.node_id]
        if not nodes:parser.error('Unknown or disabled node ID')
    directories=[]
    if args.build_dir:directories=[args.build_dir]
    else:
        for node in nodes:
            directory=root/'build/mqtt_serial/nodes'/node['node_id']/(node['role']+'-chain')
            directories.append(directory)
    try: rows=[inspect(p) for p in directories]
    except (ValueError,OSError) as exc: parser.exit(2,str(exc)+'\n')
    if args.json: print(json.dumps(rows,ensure_ascii=False,indent=2))
    else:
        for row in rows:
            if row['status']=='MISSING': print(row['directory']+': MISSING existing build artifacts')
            else:
                print('{}: {} image={} / app={} bytes, free={} bytes, used={}%'.format(
                    Path(row['directory']).name,row['status'],row['image_bytes'],row['partition_bytes'],
                    row['free_app_bytes'],row['used_percent']))
    return 0 if all(row['status']=='PASS' for row in rows) else 2
if __name__=='__main__': raise SystemExit(main())
