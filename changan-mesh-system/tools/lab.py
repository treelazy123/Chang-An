"""Build one role/topology with the active ESP-IDF Python environment."""
import argparse
import os
from pathlib import Path
import re
import subprocess
import sys
from datetime import datetime, timezone


def expected_config(role, node_id, root_id, ap_subnet=None):
    expected={'CONFIG_APP_ROLE_'+role.upper():'y',
            'CONFIG_APP_TOPOLOGY_CHAIN':'y',
            'CONFIG_APP_ARCHITECTURE_VERSION':'3',
            'CONFIG_MESH_LITE_MAXIMUM_LEVEL_ALLOWED':'4',
            'CONFIG_APP_NODE_ID':'"'+node_id+'"',
            'CONFIG_APP_UGV_NODE_ID':'"'+root_id+'"',
            'CONFIG_APP_TRANSPORT_MQTT_SERIAL':'y'}
    if role=='micro_uav':expected['CONFIG_APP_SOFTAP_SUBNET']='0'
    elif ap_subnet is not None:expected['CONFIG_APP_SOFTAP_SUBNET']=str(ap_subnet)
    return expected


def read_config(path):
    if not Path(path).is_file():return {}
    return dict(re.findall(r'^(CONFIG_\w+)=(.*)$',Path(path).read_text(encoding='utf-8'),re.MULTILINE))


def config_mismatches(path, expected):
    actual=read_config(path)
    return [f'{key}: cached={actual.get(key,"<unset>")}, expected={value}'
            for key,value in expected.items() if actual.get(key)!=value]


def backup_config(path, project_root, role, node_id):
    """Archive only sdkconfig, never credentials, NVS or the whole build tree."""
    path=Path(path)
    if not path.resolve().is_relative_to(Path(project_root).resolve()/'build'):
        raise ValueError('Refusing to reset configuration outside this project build directory')
    actual=read_config(path)
    if actual.get('CONFIG_APP_NODE_ID')!='"'+node_id+'"' or actual.get('CONFIG_APP_ROLE_'+role.upper())!='y':
        raise ValueError('Cached device identity/role differs; --reset-config cannot bypass this check')
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    backup=path.with_name('sdkconfig.before-reset-'+stamp)
    path.rename(backup)
    return backup


def execute_idf(command, build_dir, env, runner=None, *, force_reconfigure=False, verify_config=None):
    """Repair missing CMake-generated bootloader metadata before build/flash.

    Does not remove SDK configuration or create generated files by hand.
    The user-requested action only proceeds if reconfigure succeeds.
    """
    if runner is None:
        runner = subprocess.call
    build_dir = Path(build_dir)
    bootloader_config = build_dir / 'bootloader-prefix' / 'tmp' / 'bootloader-cfgcmd.txt'
    if command[-1] in ('build', 'flash') and (force_reconfigure or (
            (build_dir / 'build.ninja').is_file() and not bootloader_config.is_file())):
        if force_reconfigure:print('Regenerating sdkconfig from current role/device defaults.',flush=True)
        else:print('Incomplete CMake cache: missing ' + str(bootloader_config), flush=True)
        print('Running reconfigure before the requested action.', flush=True)
        result = runner(command[:-1] + ['reconfigure'], env=env)
        if result:
            return result
        if verify_config:verify_config()
    result=runner(command, env=env)
    if not result and command[-1] in ('reconfigure','menuconfig') and verify_config:verify_config()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--role', required=True, choices=('ugv_root', 'ugv', 'uav', 'micro_uav'))
    parser.add_argument('--inventory',type=Path,help='Explicit topology inventory; existing credentials are only validated')
    parser.add_argument('--tls-test-untrusted-client',action='store_true',help='UAV-only negative TLS test; separate credentials and build directory')
    parser.add_argument('--node-id',help='Unique device identity; isolates build and certificate per board')
    parser.add_argument('--ugv-id',help='UGV service identity (defaults to inventory association)')
    parser.add_argument('--transport', default='mqtt_serial', choices=('mqtt_serial',))
    parser.add_argument('--topology', default='chain', choices=('chain',))
    parser.add_argument('--port', help='Actual serial port of the intended board')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--reset-config',action='store_true',help='Back up a matching device sdkconfig and regenerate current defaults; never bypass identity checks')
    parser.add_argument('action', nargs='?', default='build',
                        choices=('build', 'menuconfig', 'flash', 'monitor', 'reconfigure'))
    args = parser.parse_args()
    if args.reset_config and args.action=='monitor':parser.error('--reset-config is not valid for monitor')
    if args.tls_test_untrusted_client and (args.transport!='mqtt_serial' or args.role!='uav' or not args.node_id):
        parser.error('--tls-test-untrusted-client requires --transport mqtt_serial --role uav --node-id ID')
    if args.action in ('flash','monitor') and not args.port:
        parser.error('Provide --port with the COM port of the intended board.')
    if args.transport=='mqtt_serial' and not args.node_id and not args.dry_run:
        parser.error('MQTT device operations require --node-id. Specify the unique physical-board identity; defaults are not safe for multiple boards.')
    if args.transport == 'mqtt_serial' and args.topology != 'chain':
        parser.error('mqtt_serial currently supports the confirmed chain topology only.')
    project_root = Path(__file__).resolve().parents[1]
    from node_inventory import DEFAULT_IDS, valid_id, load_inventory, root_of
    node_id = args.node_id or DEFAULT_IDS[args.role]
    try:
        valid_id(node_id)
        inventory = load_inventory(project_root,path=args.inventory) if args.inventory else load_inventory(project_root)
        registered = next((e for e in inventory['nodes'] if e['node_id'].casefold()==node_id.casefold()), None)
        if registered and (registered['node_id']!=node_id or registered['role']!=args.role):
            parser.error('Node ID is already assigned to another role/spelling: '+node_id)
        ugv_id=args.ugv_id or root_of(registered or {})
        if args.role=='ugv_root':ugv_id=node_id
        valid_id(ugv_id)
        if registered and ugv_id!=root_of(registered):parser.error('Root ID conflicts with inventory')
        if not args.dry_run and (not registered or not registered.get('enabled',True)):
            parser.error('Enroll and enable this device before a build or monitor operation')
        ap_subnet=(registered or {}).get('ap_subnet')
        if ap_subnet is None and args.role!='micro_uav' and not args.dry_run:
            parser.error('No reserved AP subnet. Run tools/provision_mqtt.py --role '+args.role+
                         ' --node-id '+node_id+' to reserve one while reusing existing credentials.')
    except (ValueError,OSError) as exc:
        parser.error(str(exc))
    firmware_root = project_root / 'firmware'
    build_dir = project_root / 'build' / 'mqtt_serial' / 'nodes' / node_id / (args.role+'-chain')
    if args.node_id:
        build_dir = project_root / 'build' / args.transport / 'nodes' / node_id / (args.role+'-'+args.topology)
    negative_identity = project_root / 'runtime/tls-negative' / node_id
    if args.tls_test_untrusted_client:
        build_dir = project_root / 'build/mqtt_serial/tls-negative' / node_id / (args.role+'-'+args.topology)
    sdkconfig_path = build_dir / 'sdkconfig'
    expected=expected_config(args.role,node_id,ugv_id,ap_subnet)
    cached=read_config(sdkconfig_path)
    mismatches=config_mismatches(sdkconfig_path,expected) if sdkconfig_path.is_file() else []
    if sdkconfig_path.is_file():
        if args.reset_config:
            if cached.get('CONFIG_APP_NODE_ID')!='"'+node_id+'"' or cached.get('CONFIG_APP_ROLE_'+args.role.upper())!='y':
                parser.error('Cached device identity/role differs; --reset-config cannot bypass this check. Inspect '+str(sdkconfig_path))
        elif mismatches and not args.dry_run:
            parser.error('Cached sdkconfig differs from current configuration:\n  '+'\n  '.join(mismatches)+
                '\nRerun the same command with --reset-config to back up sdkconfig and regenerate defaults. Inspect '+str(sdkconfig_path))
    defaults = [firmware_root / 'sdkconfig.defaults',
                firmware_root / 'configs/profiles' / (args.role + '.defaults'),
                firmware_root / 'configs/topologies' / (args.topology + '.defaults')]
    if args.transport == 'mqtt_serial':
        defaults.append(firmware_root / 'configs/profiles/mqtt_serial.defaults')
        provisioned = project_root / 'secrets' / node_id / 'clock.defaults'
        if not provisioned.is_file():
            provisioned = project_root / 'secrets/clock.defaults'
        defaults.append(provisioned)
    local_defaults = firmware_root / 'sdkconfig.local.defaults'
    if local_defaults.is_file():
        defaults.append(local_defaults)
    instance_defaults = None
    if args.node_id or args.ugv_id:
        instance_defaults = project_root / 'secrets' / node_id / 'build' / (args.transport+'-'+args.topology+'.defaults')
        defaults.append(instance_defaults)  # last: an explicit board identity overrides local/default profiles
    if not args.dry_run and args.transport=='mqtt_serial':
        try:
            from identity_env import ensure_identity
            options={'inventory_path':args.inventory or project_root/'config/nodes.json'}
            result=ensure_identity(project_root,args.role,node_id,ugv_id,check_only=True,**options)
            if args.action!='monitor':
                if args.role=='ugv_root':print('Validated root gateway: '+node_id+' (no MQTT client certificate required)',flush=True)
                else:print('Reused certificate identity: '+node_id,flush=True)
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
        content+='CONFIG_APP_TRANSPORT_MQTT_SERIAL=y\n'
        if ap_subnet is not None:content+='CONFIG_APP_SOFTAP_SUBNET='+str(ap_subnet)+'\n'
        elif args.role=='micro_uav':content+='CONFIG_APP_SOFTAP_SUBNET=0\n'
        instance_defaults.write_text(content,encoding='utf-8')
    for path in defaults:
        if not path.is_file() and not (args.dry_run and (path==instance_defaults or path.name=='clock.defaults')):
            parser.error('Missing config file: ' + str(path))

    if args.tls_test_untrusted_client and not args.dry_run:
        from identity_env import crypto_available
        host_python = Path(sys.executable) if crypto_available() else project_root / '.venv' / ('Scripts/python.exe' if os.name=='nt' else 'bin/python')
        if not host_python.is_file():
            parser.error('Prepare the uv host environment with uv sync --locked first')
        worker_env = dict(os.environ)
        for name in ('PYTHONHOME','PYTHONPATH'):
            worker_env.pop(name,None)
        worker_env.update(PYTHONUTF8='1',PYTHONNOUSERSITE='1')
        result = subprocess.run([str(host_python),'-X','utf8',str(project_root/'tools/tls_negative_identity.py'),
                                 '--root',str(project_root),'--node-id',node_id],cwd=project_root,env=worker_env,
                                 stdout=subprocess.PIPE,stderr=subprocess.PIPE,encoding='utf-8',timeout=60)
        if result.returncode:
            parser.error('Negative-test identity preparation failed: '+result.stderr.strip())
        print('NEGATIVE TLS TEST: untrusted client CA; enrolled credentials remain unchanged.',flush=True)

    idf_args = ['-C', str(firmware_root), '-B', str(build_dir),
                '-D', 'IDF_TARGET=esp32c6', '-D', 'SDKCONFIG=' + str(sdkconfig_path),
                '-D', 'SDKCONFIG_DEFAULTS=' + ';'.join(str(p) for p in defaults)]
    idf_args.extend(['-D','MESH_TLS_TEST_IDENTITY_DIR=' + (negative_identity.as_posix() if args.tls_test_untrusted_client else '')])
    if args.port:
        idf_args.extend(['-p', args.port])
    idf_args.append(args.action)

    if args.dry_run:
        print('Dry run: no build, download, flash, erase or serial connection.')
        print('Transport: ' + args.transport)
        if args.transport=='mqtt_serial' and not args.node_id:
            print('Preview only: add --node-id before a real device operation.')
        print('Node ID: ' + node_id + '; UGV ID: ' + ugv_id)
        print('Reserved AP: '+('disabled (STA only)' if args.role=='micro_uav' else
              (f'192.168.{ap_subnet}.1/24' if ap_subnet is not None else 'unassigned; enroll before building')))
        if args.transport=='mqtt_serial':
            print('Identity: existing credentials are validated only; root gateway needs no MQTT client certificate')
        print('Build directory: ' + str(build_dir))
        for difference in mismatches:print('Cached config difference: '+difference)
        if args.reset_config:print('Config reset preview: back up sdkconfig, regenerate defaults, then run '+args.action+'; no files changed.')
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

    reset=args.reset_config
    if args.reset_config and sdkconfig_path.is_file():
        try:backup=backup_config(sdkconfig_path,project_root,args.role,node_id)
        except (ValueError,OSError) as exc:parser.error(str(exc))
        print('Previous sdkconfig backed up to '+str(backup),flush=True)

    def verify_generated_config():
        differences=config_mismatches(sdkconfig_path,expected)
        if differences:raise ValueError('Generated sdkconfig is not valid; requested action stopped:\n  '+'\n  '.join(differences))

    print('IDF: ' + version.stdout.strip(), flush=True)
    print('Role: {}; topology: {}; transport: {}; action: {}'.format(
        args.role, args.topology, args.transport, args.action), flush=True)
    print('Node ID: '+node_id+'; UGV ID: '+ugv_id,flush=True)
    print('Build directory: ' + str(build_dir), flush=True)
    try:
        return execute_idf([idf_python, str(idf_script)] + idf_args, build_dir, build_env,
                           force_reconfigure=reset,verify_config=verify_generated_config)
    except (ValueError,OSError) as exc:parser.error(str(exc))


if __name__ == '__main__':
    sys.exit(main())
