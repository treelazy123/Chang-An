"""Apply retained IoT-Bridge extensions to a build-local SDK source copy."""
import argparse
import hashlib
import json
from pathlib import Path


def prepare(source, ip4, patch):
    if 'if (!netif->napt)' not in ip4:
        raise ValueError('SDK lacks the required NAPT forwarding guard.')
    if 'void ip_napt_table_clear(void)' in source and 'IP_NAPT_ADD_FAILED_HOOK();' in source:
        return source
    if 'ip_napt_table_clear' in source or 'IP_NAPT_ADD_FAILED_HOOK' in source:
        raise ValueError('SDK NAPT source is partially patched; inspect it before proceeding.')
    anchors = (
        ('#if ESP_LWIP && LWIP_IPV4 && IP_NAPT\n',
         '#if ESP_LWIP && LWIP_IPV4 && IP_NAPT\n\n#ifdef ESP_IDF_LWIP_HOOK_FILENAME\n#include ESP_IDF_LWIP_HOOK_FILENAME\n#endif\n'),
        ('  LWIP_DEBUGF(NAPT_DEBUG, ("ip_napt_add() failed to insert\\n"));',
         '  LWIP_DEBUGF(NAPT_DEBUG, ("ip_napt_add() failed to insert\\n"));\n#ifdef IP_NAPT_ADD_FAILED_HOOK\n  IP_NAPT_ADD_FAILED_HOOK();\n#endif'),
    )
    for old, new in anchors:
        if source.count(old) != 1:
            raise ValueError('Unrecognized SDK NAPT source anchor: ' + old)
        source = source.replace(old, new, 1)
    addition = []
    collecting = False
    for line in patch.splitlines():
        if line.startswith('+#define IP_GET_V4'):
            collecting = True
        if collecting and line.startswith('+'):
            addition.append(line[1:])
    if not addition or 'void ip_napt_table_clear(void)' not in addition:
        raise ValueError('Cannot find the NAPT clear implementation in the retained patch.')
    end = '#endif /* ESP_LWIP && LWIP_IPV4 && IP_NAPT */'
    if source.count(end) != 1:
        raise ValueError('Unrecognized SDK NAPT end marker.')
    return source.replace(end, '\n'.join(addition) + '\n' + end)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'ip4', 'patch', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    original = args.source.read_bytes()
    generated = prepare(original.decode('utf-8').replace('\r\n', '\n'),
                        args.ip4.read_text(encoding='utf-8'), args.patch.read_text(encoding='utf-8'))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if not args.output.exists() or args.output.read_text(encoding='utf-8') != generated:
        args.output.write_text(generated, encoding='utf-8', newline='\n')
    metadata = {'sdk_source': str(args.source), 'sdk_sha256': hashlib.sha256(original).hexdigest(),
                'generated_sha256': hashlib.sha256(args.output.read_bytes()).hexdigest(),
                'upstream_patch_sha256': hashlib.sha256(args.patch.read_bytes()).hexdigest()}
    args.output.with_suffix('.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
    print('NAPT: SDK unchanged; extensions generated in ' + str(args.output))


if __name__ == '__main__':
    main()
