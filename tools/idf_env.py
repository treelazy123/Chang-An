"""Use active ESP-IDF or read EIM static environment data without executing scripts."""
import json
import os
from pathlib import Path
import re
import sys


def prepare_idf_environment(project_root):
    env = dict(os.environ, IDF_COMPONENT_MANAGER='0', PYTHONUTF8='1')
    if env.get('IDF_PATH') and env.get('IDF_PYTHON_ENV_PATH'):
        python = Path(env['IDF_PYTHON_ENV_PATH']) / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        return env, str(python)
    if os.name != 'nt':
        if not env.get('IDF_PATH'):
            raise ValueError('Activate ESP-IDF 6.1.x first.')
        return env, sys.executable
    tools = Path(env.get('IDF_TOOLS_PATH', 'C:/Espressif/tools'))
    manifest = tools / 'eim_idf.json'
    if not manifest.is_file():
        raise ValueError('Activate ESP-IDF 6.1.x, or set IDF_TOOLS_PATH to the EIM tools directory.')
    installs = json.loads(manifest.read_text(encoding='utf-8'))['idfInstalled']
    selected = env.get('IDF_PATH')
    candidates = [item for item in installs if item['name'] == 'v6.1' or item['name'].startswith('v6.1.')]
    if selected:
        candidates = [item for item in candidates if Path(item['path']).resolve() == Path(selected).resolve()]
    if len(candidates) != 1:
        raise ValueError('Select a unique ESP-IDF 6.1 installation with IDF_PATH.')
    install = candidates[0]
    profile = Path(install['activationScript']).read_text(encoding='utf-8-sig')
    for key, value in re.findall(r'^\s*"([A-Z_]+)"\s*=\s*"([^"\r\n]+)"', profile, re.MULTILINE):
        env[key] = value
    paths = re.findall(r'^\s*"PATH=([^"\r\n]+)"', profile, re.MULTILINE)
    if len(paths) != 1:
        raise ValueError('Cannot read PATH from the EIM profile. Activate IDF manually.')
    env['PATH'] = paths[0] + os.pathsep + env.get('PATH', '')
    env['IDF_PATH'] = install['path']
    env['IDF_TOOLS_PATH'] = install['idfToolsPath']
    env['IDF_PYTHON_ENV_PATH'] = str(Path(install['python']).parent.parent)
    env['ESP_IDF_VERSION'] = '6.1'
    return env, install['python']
