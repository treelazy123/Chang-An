import argparse
import json
from pathlib import Path
from .client import SerialClient,MQTTClient,request_line
from .tasks import HELP,TaskClient
import shlex

def main():
    p=argparse.ArgumentParser(description='Car UI: list | ping NODE | status NODE | echo NODE TEXT | quit')
    p.add_argument('--transport',choices=('serial','mqtt'),default='serial')
    p.add_argument('--port',help='root/car C6 COM port (not UGV COM port)')
    p.add_argument('--host',help='UGV Broker reachable IP/domain when using an S31 IP NIC')
    p.add_argument('--broker-port',type=int,default=8883)
    p.add_argument('--node-id',default='pc-root-001')
    p.add_argument('--cert-dir',type=Path)
    p.add_argument('--server-name',default='ugv-broker.lab')
    p.add_argument('--command',help='One command, then exit')
    args=p.parse_args()
    if args.transport=='serial' and not args.port:p.error('Provide --port for the root C6, e.g. COM7')
    if args.transport=='mqtt' and (not args.host or not args.cert_dir):p.error('MQTT requires --host and --cert-dir')
    try:
        client=SerialClient(args.port) if args.transport=='serial' else MQTTClient(args.host,args.broker_port,args.node_id,args.cert_dir,args.server_name)
        try:
            if args.command:print(json.dumps(request_line(client,args.command),ensure_ascii=False));return
            print('Car terminal connected. '+HELP)
            while True:
                try:
                    line=input('car> ').strip()
                    if line=='quit':break
                    if line.startswith('watch'):
                        parts=shlex.split(line)
                        if parts[0]!='watch' or len(parts)>3:raise ValueError('Usage: watch [TASK_ID] [CURSOR]')
                        try:
                            for event in TaskClient(client).watch(parts[1] if len(parts)>1 else None,int(parts[2]) if len(parts)>2 else 0):
                                print(json.dumps(event,ensure_ascii=False),flush=True)
                        except KeyboardInterrupt:print('Watch stopped; tasks continue on UGV.')
                        continue
                    if line=='help':print(HELP);continue
                    if line:print(json.dumps(request_line(client,line),ensure_ascii=False))
                except (ValueError,OSError,TimeoutError) as exc:print('Error:',exc)
        finally:client.close()
    except (OSError,ValueError,TimeoutError) as exc:p.exit(1,str(exc)+'\n')
if __name__=='__main__':
    try:main()
    except (KeyboardInterrupt,EOFError):pass
