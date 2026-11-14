"""Build one role/topology with the active ESP-IDF Python environment."""
import argparse
import os
from pathlib import Path
import re
import subprocess
import sys


def execute_idf(command, build_dir, env, runner=None):
    """Repair missing CMake-generated bootloader metadata before build/flash.

    Does not remove SDK configuration or create generated files by hand.
    The user-requested action only proceeds if reconfigure succeeds.
    """
    if runner is None:
        runner = subprocess.call
    build_dir = Path(build_dir)
    bootloader_config = build_dir / 'bootloader-prefix' / 'tmp' / 'bootloader-cfgcmd.txt'
    if (command[-1] in ('build', 'flash') and (build_dir / 'build.ninja').is_file()
            and not bootloader_config.is_file()):
        print('Incomplete CMake cache: missing ' + str(bootloader_config), flush=True)
        print('Running reconfigure first; existing sdkconfig is preserved.', flush=True)
        result = runner(command[:-1] + ['reconfigure'], env=env)
        if result:
            return result
    return runner(command, env=env)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--role', required=True, choices=('pc_root', 'ugv', 'uav', 'micro_uav'))
    parser.add_argument('--node-id',help='Unique device identity; isolates build and certificate per board')
    parser.add_argument('--ugv-id',help='UGV service identity (defaults to inventory association)')
    parser.add_argument('--transport', default='legacy', choices=('legacy', 'mqtt_serial'))
    parser.add_argument('--topology', default='chain', choices=('star', 'chain', 'auto'))
    parser.add_argument('--port', help='Actual serial port of the intended board')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('action', nargs='?', default='build',
                        choices=('build', 'menuconfig', 'flash', 'monitor', 'reconfigure'))
    args = parser.parse_args()
    if args.transport=='legacy' and (args.node_id or args.ugv_id):
        parser.error('Per-device --node-id/--ugv-id requires --transport mqtt_serial; legacy uses its original role profiles.')
    if args.action in ('flash','monitor') and not args.port:
        parser.error('Provide --port with the COM port of the intended board.')
    if args.transport=='mqtt_serial' and not args.node_id and not args.dry_run:
        parser.error('MQTT device operations require --node-id. Specify the unique physical-board identity; defaults are not safe for multiple boards.')
    if args.transport == 'mqtt_serial' and args.topology != 'chain':
        parser.error('mqtt_serial currently supports the confirmed chain topology only.')
    project_root = Path(__file__).resolve().parents[1]
    from node_inventory import DEFAULT_IDS, valid_id, load_inventory
    node_id = args.node_id or DEFAULT_IDS[args.role]
    try:
        valid_id(node_id)
        inventory = load_inventory(project_root)
        registered = next((e for e in inventory['nodes'] if e['node_id'].casefold()==node_id.casefold()), None)
        if registered and (registered['node_id']!=node_id or registered['role']!=args.role):
            parser.error('Node ID is already assigned to another role/spelling: '+node_id)
        ugv_id = node_id if args.role=='ugv' else (args.ugv_id or (registered or {}).get('ugv_id','ugv-001'))
        valid_id(ugv_id)
        if args.role=='ugv' and args.ugv_id and args.ugv_id!=node_id:
            parser.error('A UGV must advertise its own --node-id as --ugv-id')
    except (ValueError,OSError) as exc:
        parser.error(str(exc))
    build_dir = project_root / 'build' / 'four-node' / (args.role + '-' + args.topology)
    if args.transport != 'legacy':
        build_dir = project_root / 'build' / args.transport / (args.role + '-' + args.topology)
    if args.node_id:
        build_dir = project_root / 'build' / args.transport / 'nodes' / node_id / (args.role+'-'+args.topology)
    sdkconfig_path = build_dir / 'sdkconfig'
    defaults = [project_root / 'sdkconfig.defaults',
                project_root / 'profiles' / (args.role + '.defaults'),
                project_root / 'topologies' / (args.topology + '.defaults')]
    if args.transport == 'mqtt_serial':
        defaults.append(project_root / 'profiles/mqtt_serial.defaults')
        provisioned = project_root / 'secrets' / node_id / 'clock.defaults'
        if not provisioned.is_file():
            provisioned = project_root / 'secrets/clock.defaults'
        defaults.append(provisioned)
    local_defaults = project_root / 'sdkconfig.local.defaults'
    if local_defaults.is_file():
        defaults.append(local_defaults)
    instance_defaults = None
    if args.node_id or args.ugv_id:
        instance_defaults = project_root / 'secrets' / node_id / 'build' / (args.transport+'-'+args.topology+'.defaults')
        defaults.append(instance_defaults)  # last: an explicit board identity overrides local/default profiles
    if not args.dry_run and args.transport=='mqtt_serial':
        try:
            from identity_env import ensure_identity
            result=ensure_identity(project_root,args.role,node_id,ugv_id,check_only=args.action=='monitor')
            if args.action!='monitor':
                print(('Created' if result['created'] else 'Reused')+' certificate identity: '+node_id,flush=True)
        except (ValueError,OSError) as exc:
            parser.error(str(exc))
        # Enrollment supplies a per-device trusted clock; keep it in this device's cache.
        per_device_clock=project_root/'secrets'/node_id/'clock.defaults'
        if per_device_clock.exists():
            defaults=[per_device_clock if p.name=='clock.defaults' else p for p in defaults]
    if instance_defaults and not args.dry_run:
        instance_defaults.parent.mkdir(parents=True,exist_ok=True)
        content='CONFIG_APP_NODE_ID="'+node_id+'"\nCONFIG_APP_UGV_NODE_ID="'+ugv_id+'"\n'
        content+='CONFIG_APP_ROLE_'+args.role.upper()+'=y\n'
        content+='CONFIG_APP_TOPOLOGY_'+args.topology.upper()+'=y\n'
        content+='CONFIG_APP_TRANSPORT_'+('LEGACY' if args.transport=='legacy' else 'MQTT_SERIAL')+'=y\n'
        instance_defaults.write_text(content,encoding='utf-8')
    for path in defaults:
        if not path.is_file() and not (args.dry_run and (path==instance_defaults or path.name=='clock.defaults')):
            parser.error('Missing config file: ' + str(path))

    idf_args = ['-C', str(project_root), '-B', str(build_dir),
                '-D', 'IDF_TARGET=esp32c6', '-D', 'SDKCONFIG=' + str(sdkconfig_path),
                '-D', 'SDKCONFIG_DEFAULTS=' + ';'.join(str(p) for p in defaults)]
    if args.port:
        idf_args.extend(['-p', args.port])
    idf_args.append(args.action)

    if args.dry_run:
        print('Dry run: no build, download, flash, erase or serial connection.')
        print('Transport: ' + args.transport)
        if args.transport=='mqtt_serial' and not args.node_id:
            print('Compatibility preview only: add --node-id before a real device operation.')
        print('Node ID: ' + node_id + '; UGV ID: ' + ugv_id)
        if args.transport=='mqtt_serial':
            print('Identity: existing certificate is validated/reused; new ID is enrolled only on a non-dry run')
        print('Build directory: ' + str(build_dir))
        for argument in idf_args:
            print('ARG: ' + argument)
        return 0

    from idf_env import prepare_idf_environment
    try:
        build_env, idf_python = prepare_idf_environment(project_root)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    idf_path = build_env.get('IDF_PATH')
    if not idf_path:
        parser.error('IDF_PATH is unset. Activate your installed ESP-IDF 6.1.x environment first.')
    idf_script = Path(idf_path) / 'tools' / 'idf.py'
    if not idf_script.is_file():
        parser.error('Cannot find ' + str(idf_script))
    build_env['IDF_COMPONENT_MANAGER'] = '0'
    version = subprocess.run([idf_python, str(idf_script), '--version'], env=build_env,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             encoding='utf-8', errors='replace')
    if version.returncode:
        parser.error('Cannot run idf.py in the active Python environment:\n' + version.stdout)
    if not re.search(r'ESP-IDF v6\.1(?:\.|\s|$)', version.stdout):
        parser.error('Expected ESP-IDF 6.1.x; got: ' + version.stdout.strip())

    if sdkconfig_path.is_file():
        config = sdkconfig_path.read_text(encoding='utf-8')
        symbols = ('CONFIG_APP_ROLE_' + args.role.upper() + '=y',
                   'CONFIG_APP_TOPOLOGY_' + args.topology.upper() + '=y',
                   'CONFIG_APP_ARCHITECTURE_VERSION=2',
                   'CONFIG_MESH_LITE_MAXIMUM_LEVEL_ALLOWED=4',
                   'CONFIG_APP_NODE_ID="'+node_id+'"')
        if args.transport=='mqtt_serial' or args.node_id or args.ugv_id:
            symbols += ('CONFIG_APP_UGV_NODE_ID="'+ugv_id+'"',)
        if args.transport == 'mqtt_serial':
            symbols += ('CONFIG_APP_TRANSPORT_MQTT_SERIAL=y',)
        elif 'CONFIG_APP_TRANSPORT_MQTT_SERIAL=y' in config:
            parser.error('MQTT cache cannot be used in legacy mode.')
        for symbol in symbols:
            if not re.search(r'^' + re.escape(symbol) + r'\r?$', config, re.MULTILINE):
                parser.error('Cached sdkconfig does not match this device/role/topology/transport. Inspect ' + str(sdkconfig_path))

    print('IDF: ' + version.stdout.strip(), flush=True)
    print('Role: {}; topology: {}; transport: {}; action: {}'.format(
        args.role, args.topology, args.transport, args.action), flush=True)
    print('Node ID: '+node_id+'; UGV ID: '+ugv_id,flush=True)
    print('Build directory: ' + str(build_dir), flush=True)
    return execute_idf([idf_python, str(idf_script)] + idf_args, build_dir, build_env)


if __name__ == '__main__':
    sys.exit(main())
