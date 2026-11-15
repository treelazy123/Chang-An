"""Render Broker network listeners independently of certificate issuance."""
from ipaddress import ip_address
from pathlib import Path

def render_broker_config(*, ca_file,server_cert,server_key,acl_file,listeners=(("127.0.0.1",8883),)):
    if not listeners:raise ValueError('At least one listener is required')
    paths=[]
    for name,path in [('cafile',ca_file),('certfile',server_cert),('keyfile',server_key),('acl_file',acl_file)]:
        path=Path(path).resolve().as_posix()
        if '\n' in path or '\r' in path:raise ValueError('Invalid configuration path')
        paths.append(name+' '+path)
    rows=['per_listener_settings true'];seen=set()
    for address,port in listeners:
        address=str(ip_address(address))
        if type(port) is not int or not 1<=port<=65535:raise ValueError('Invalid listener port')
        if (address,port) in seen:raise ValueError('Duplicate listener')
        seen.add((address,port));rows.append(f'listener {port} {address}')
        # TLS material and authentication are listener-specific, including loopback.
        rows += ['allow_anonymous false','require_certificate true','use_identity_as_username true',
                 'use_username_as_clientid true','tls_version tlsv1.2',*paths]
    rows += ['max_packet_size 2048','persistence false','log_type error','log_type warning','log_type notice']
    return '\n'.join(rows)+'\n'
