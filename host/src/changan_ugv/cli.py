"""Compatibility console: uses a running UGV service, or retains standalone MQTT management."""
from changan_ugv.paths import repository_root
import argparse
import json
from pathlib import Path
import shlex
import ssl
from changan_ugv.nodes.inventory import load_inventory
from changan_ugv.nodes.controller import Controller,Registry,BrokerTLSContext,OPERATIONS,NODES

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--secrets',type=Path,default=repository_root()/'secrets')
    parser.add_argument('--broker-port',type=int,default=8883)
    parser.add_argument('--inventory',type=Path,help='Explicit administrator-controlled nodes.json')
    parser.add_argument('--service-port',type=int,default=8787)
    parser.add_argument('--standalone',action='store_true',help='Legacy combined manager; refuse if the service is already running')
    args=parser.parse_args()
    try:
        inventory=load_inventory(args.secrets.resolve().parent)
        if args.inventory:
            from changan_ugv.nodes.inventory import validate
            inventory=validate(json.loads(args.inventory.read_text(encoding='utf-8')))
        inventory_path=args.inventory or args.secrets.resolve().parent/'config/nodes.json'
        from changan_ugv.transport.rpc import LocalController
        controller=LocalController.discover(args.service_port)
        if controller is not None and args.standalone:
            parser.error('UGV service is running. Use this console through it; do not duplicate controller-001.')
        if controller is None:
            controller=Controller(args.secrets,args.broker_port,inventory,inventory_path)
    except ConnectionRefusedError:
        parser.exit(2, f'Cannot connect to MQTT Broker at 127.0.0.1:{args.broker_port}. '
                    'Start Mosquitto with runtime/mosquitto.conf and use the same broker port.\n')
    except ssl.SSLError as exc:
        parser.exit(2, f'Broker TLS authentication failed: {exc}. Check the CA, service name and client certificate.\n')
    except (OSError,TimeoutError) as exc:
        parser.exit(2,'UGV service or Broker unavailable: '+str(exc)+'\n')
    print('UGV console connected. Commands: list | ping NODE | status NODE | echo NODE TEXT | quit')
    try:
        while True:
            try:
                parts=shlex.split(input('mqtt> '))
                if not parts: continue
                if parts==['quit']: break
                if parts==['list']:
                    with controller.condition: result=controller.registry.snapshot()
                elif len(parts)>=2 and parts[0] in OPERATIONS:
                    result=controller.command(parts[1],parts[0],' '.join(parts[2:]))
                else: raise ValueError('Expected list, ping NODE, status NODE, echo NODE TEXT, quit')
                print(json.dumps(result,ensure_ascii=False))
            except (ValueError,OSError,TimeoutError) as exc:
                print('Error:',exc)
    finally:
        controller.close()
if __name__=='__main__':
    try: main()
    except (KeyboardInterrupt,EOFError): pass
