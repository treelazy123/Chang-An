"""Compatibility console: uses a running UGV service, or retains standalone MQTT management."""
from changan_ugv.config import service_arguments, resolve_arguments
import argparse
import json
from pathlib import Path
import shlex
import ssl
from changan_ugv.nodes.inventory import load_inventory
from changan_ugv.nodes.controller import Controller,Registry,BrokerTLSContext,OPERATIONS,NODES

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    service_arguments(parser)
    parser.add_argument('--service-port',type=int)
    parser.add_argument('--standalone',action='store_true',help='Legacy combined manager; refuse if the service is already running')
    args=parser.parse_args()
    try:
        cfg=resolve_arguments(args)
        inventory=load_inventory(path=cfg.paths.inventory_file)
        inventory_path=cfg.paths.inventory_file
        from changan_ugv.transport.rpc import LocalController
        controller=LocalController.discover(args.service_port if args.service_port is not None else cfg.rpc_port)
        if controller is not None and args.standalone:
            parser.error('UGV service is running. Use this console through it; do not duplicate controller-001.')
        if controller is None:
            controller=Controller(inventory=inventory,inventory_path=inventory_path,broker=cfg.broker,lock_file=cfg.paths.lock_file)
    except ConnectionRefusedError:
        parser.exit(2, f'Cannot connect to MQTT Broker at {cfg.broker.endpoint.host}:{cfg.broker.endpoint.port}. '
                    'Start Mosquitto with runtime/mosquitto.conf and use the same broker port.\n')
    except ssl.SSLError as exc:
        parser.exit(2, f'Broker TLS authentication failed: {exc}. Check the CA, service name and client certificate.\n')
    except (OSError,TimeoutError,ValueError,KeyError,TypeError) as exc:
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
