"""Render deployment listeners using existing certificates; never issues/replaces keys."""
import argparse
from pathlib import Path
from _bootstrap import bootstrap
bootstrap()
from changan_ugv.deployment import render_broker_config

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--listen-address',action='append',help='Repeat for loopback and USB network addresses')
    p.add_argument('--port',type=int,default=8883)
    p.add_argument('--ca-file',type=Path)
    p.add_argument('--server-cert',type=Path)
    p.add_argument('--server-key',type=Path)
    p.add_argument('--acl-file',type=Path)
    p.add_argument('--output',type=Path)
    args=p.parse_args();root=args.root.resolve()
    values=dict(ca_file=args.ca_file or root/'secrets/ca.pem',server_cert=args.server_cert or root/'secrets/ugv-broker.lab/client.pem',
                server_key=args.server_key or root/'secrets/ugv-broker.lab/client.key',acl_file=args.acl_file or root/'runtime/acl.conf')
    try:
        for path in values.values():
            if not path.is_file():raise ValueError('Missing existing deployment file: '+str(path))
        text=render_broker_config(**values,listeners=[(address,args.port) for address in (args.listen_address or ['127.0.0.1'])])
        output=args.output or root/'runtime/mosquitto.conf';output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(text,encoding='utf-8')
    except (ValueError,OSError) as exc:p.error(str(exc))
    print('Broker configuration written: '+str(output)+'; no service was restarted')
if __name__=='__main__':main()
