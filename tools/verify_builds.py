"""Build and audit the twelve ESP32-C6 role/topology combinations."""
import hashlib
import itertools
import json
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def main():
    validation = ROOT / 'build' / 'four-node' / 'validation'
    validation.mkdir(parents=True, exist_ok=True)
    sdk = Path('D:/esp/v6.1/esp-idf')
    from idf_env import prepare_idf_environment
    env, python = prepare_idf_environment(ROOT)
    sdk = Path(env['IDF_PATH'])
    sdk_files = [sdk / ('components/lwip/lwip/src/core/ipv4/' + name) for name in ('ip4.c', 'ip4_napt.c')]
    before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sdk_files}
    report = {'idf': '6.1', 'target': 'esp32c6', 'architecture': 2, 'sdk_before_sha256': before, 'builds': []}
    report_path = ROOT / 'build' / 'four-node' / 'verification.json'
    failed = False
    for role, topology in itertools.product(('pc_root', 'ugv', 'uav', 'micro_uav'), ('star', 'chain', 'auto')):
        key = role + '-' + topology
        print('BUILD ' + key, flush=True)
        start = time.monotonic()
        log = validation / (key + '.log')
        with log.open('w', encoding='utf-8') as output:
            result = subprocess.run([python, str(ROOT/'tools/lab.py'), '--role', role, '--topology', topology, 'build'],
                                    stdout=output, stderr=subprocess.STDOUT, env=env)
        build = ROOT / 'build' / 'four-node' / key
        entry = {'role': role, 'topology': topology, 'exit_code': result.returncode,
                 'seconds': round(time.monotonic() - start, 1), 'log': str(log.relative_to(ROOT))}
        if result.returncode == 0:
            config = (build/'sdkconfig').read_text(encoding='utf-8')
            expected = ['CONFIG_APP_ROLE_' + role.upper() + '=y',
                        'CONFIG_APP_TOPOLOGY_' + topology.upper() + '=y',
                        'CONFIG_FREERTOS_TIMER_TASK_STACK_DEPTH=4096',
                        'CONFIG_PARTITION_TABLE_CUSTOM=y', 'CONFIG_APP_ARCHITECTURE_VERSION=2',
                        'CONFIG_MESH_LITE_MAXIMUM_LEVEL_ALLOWED=4']
            missing = [s for s in expected if not re.search('^' + re.escape(s) + '$', config, re.MULTILINE)]
            if missing:
                entry['config_errors'] = missing
                failed = True
            for extension in ('bin', 'elf'):
                artifact = build / ('mesh_lite_node.' + extension)
                entry[extension] = {'path': str(artifact.relative_to(ROOT)), 'bytes': artifact.stat().st_size,
                                    'sha256': hashlib.sha256(artifact.read_bytes()).hexdigest()}
            if entry['bin']['bytes'] > 0x1f0000:
                entry['partition_overflow'] = True
                failed = True
        else:
            failed = True
            print(log.read_text(encoding='utf-8', errors='replace')[-6000:], flush=True)
        report['builds'].append(entry)
        print(('PASS ' if result.returncode == 0 and not entry.get('config_errors') else 'FAIL ') + key, flush=True)
        report_path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        if result.returncode:
            break
    after = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sdk_files}
    report['sdk_after_sha256'] = after
    report['sdk_unchanged'] = before == after
    report['all_passed'] = not failed and before == after and len(report['builds']) == 12
    report_path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print('REPORT ' + str(report_path), flush=True)
    return 0 if report['all_passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
