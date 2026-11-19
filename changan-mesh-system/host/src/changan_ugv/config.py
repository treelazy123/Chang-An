"""Explicit deployment configuration. Relative TOML paths are relative to its file."""
from dataclasses import dataclass, replace
from ipaddress import ip_network
from pathlib import Path
import tomllib
from changan_ugv.paths import repository_root

@dataclass(frozen=True)
class BrokerEndpoint:
    host: str = '127.0.0.1'
    port: int = 8883
    server_name: str = 'ugv-broker.lab'
    def __post_init__(self):
        if not isinstance(self.host,str) or not self.host or any(c.isspace() for c in self.host):
            raise ValueError('Invalid Broker connection host')
        if type(self.port) is not int or not 1 <= self.port <= 65535:
            raise ValueError('Invalid Broker port')
        if not isinstance(self.server_name,str) or not self.server_name or any(c.isspace() for c in self.server_name):
            raise ValueError('Invalid TLS service name')

@dataclass(frozen=True)
class BrokerConfig:
    endpoint: BrokerEndpoint
    ca_file: Path
    client_cert: Path
    client_key: Path
    @classmethod
    def from_secrets(cls,secret,port=8883):
        secret=Path(secret)
        return cls(BrokerEndpoint(port=port),secret/'ca.pem',secret/'controller-001/client.pem',secret/'controller-001/client.key')

@dataclass(frozen=True)
class ServicePaths:
    inventory_file: Path
    task_database: Path
    agent_journal: Path
    lock_file: Path
    @classmethod
    def from_root(cls,root):
        root=Path(root)
        return cls(root/'config/nodes.json',root/'runtime/ugv-root/tasks.sqlite3',root/'runtime/ugv-root/agent.json',root/'secrets/.controller.lock')

@dataclass(frozen=True)
class ServiceConfig:
    broker: BrokerConfig
    paths: ServicePaths
    ugv_id: str = 'ugv-root'
    http_port: int = 8080
    http_host: str = '127.0.0.1'
    http_allowed_peers: tuple[str, ...] = ('127.0.0.1', '::1')
    def __post_init__(self):
        if type(self.http_port) is not int or not 0<=self.http_port<=65535:
            raise ValueError('Invalid HTTP port')
        if (not isinstance(self.http_host,str) or not self.http_host
                or any(c.isspace() for c in self.http_host) or self.http_host in ('0.0.0.0','::')):
            raise ValueError('Invalid HTTP bind host; bind one explicit address')
        if not isinstance(self.http_allowed_peers,tuple) or not self.http_allowed_peers:
            raise ValueError('HTTP allowed peers must be a non-empty tuple')
        try:
            self.networks()
        except ValueError as exc:
            raise ValueError('Invalid HTTP allowed peer: '+str(exc)) from exc
    def networks(self):
        return tuple(ip_network(peer,strict=False) for peer in self.http_allowed_peers)
    @classmethod
    def from_root(cls,root=None):
        root=Path(root) if root is not None else repository_root()
        return cls(BrokerConfig.from_secrets(root/'secrets'),ServicePaths.from_root(root))
    @classmethod
    def from_file(cls,file):
        file=Path(file).resolve()
        with file.open('rb') as stream:data=tomllib.load(stream)
        if set(data)-{'broker','paths','service'}:raise ValueError('Unknown service configuration section')
        broker=data.get('broker',{});paths=data.get('paths',{});service=data.get('service',{})
        if set(broker)-{'host','port','server_name','ca_file','client_cert','client_key'}:raise ValueError('Unknown Broker option')
        if set(paths)-{'inventory_file','task_database','agent_journal','lock_file'}:raise ValueError('Unknown path option')
        if set(service)-{'ugv_id','http_port','http_host','http_allowed_peers'}:raise ValueError('Unknown service option')
        if 'http_allowed_peers' in service:
            peers=service['http_allowed_peers']
            if not isinstance(peers,list) or not all(isinstance(p,str) for p in peers):
                raise ValueError('HTTP allowed peers must be a list of addresses or networks')
            service=dict(service,http_allowed_peers=tuple(peers))
        def path(value):return (file.parent/Path(value)).resolve()
        # A file-based deployment is explicit; it never falls back to installed source paths.
        tls={key:path(broker[key]) for key in ('ca_file','client_cert','client_key')}
        state={key:path(paths[key]) for key in ('inventory_file','task_database','agent_journal','lock_file')}
        cfg=cls(BrokerConfig(BrokerEndpoint(**{key:broker[key] for key in ('host','port','server_name') if key in broker}),**tls),ServicePaths(**state),**service)
        from changan_ugv.nodes.inventory import valid_id
        valid_id(cfg.ugv_id)
        return cfg

def service_arguments(parser):
    parser.add_argument('--config',type=Path,help='Explicit deployment TOML; relative paths resolve beside this file')
    parser.add_argument('--broker-host')
    parser.add_argument('--broker-port',type=int)
    parser.add_argument('--server-name')
    parser.add_argument('--inventory',type=Path)

def resolve_arguments(args):
    cfg=ServiceConfig.from_file(args.config) if args.config else ServiceConfig.from_root()
    endpoint=replace(cfg.broker.endpoint,**{key:value for key,value in {'host':args.broker_host,'port':args.broker_port,'server_name':args.server_name}.items() if value is not None})
    paths=replace(cfg.paths,inventory_file=args.inventory.resolve()) if args.inventory else cfg.paths
    return replace(cfg,broker=replace(cfg.broker,endpoint=endpoint),paths=paths)
