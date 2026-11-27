"""Translate the node-side MCI capability message into the registry view."""
import re


REQUIRED = {
    'operations': 'operations',
    'taskRole': 'task_role',
    'taskTypes': 'task_types',
    'taskOperations': 'task_operations',
    'taskStatus': 'task_status',
    'capMeasureV': 'cap_measure_v',
}
OPTIONAL = {
    'executionMode': 'execution_mode',
    'taskId': 'task_id',
    'capId': 'cap_id',
    'capSeq': 'cap_seq',
    'sentUs': 'sent_us',
}


def normalize_capabilities(wire):
    if wire.get('type') == 'capabilities':
        return wire
    if (wire.keys() != {'v', 'service', 'method', 'nodeId', 'bootId', 'params'}
            or type(wire['v']) is not int or wire['v'] != 1
            or wire['service'] != 'Mesh_Node' or wire['method'] != 'Ntf_Capabilities'):
        raise ValueError('Invalid node capability envelope')
    boot = wire['bootId']
    if not isinstance(boot, str) or not re.fullmatch('[0-9a-f]{16}', boot):
        raise ValueError('Invalid capability bootId')
    params = wire['params']
    if (not isinstance(params, dict) or not REQUIRED.keys() <= params.keys()
            or params.keys() - REQUIRED.keys() - OPTIONAL.keys()
            or params['taskRole'] not in ('ugv', 'uav', 'micro_uav')
            or type(params['capMeasureV']) is not int or params['capMeasureV'] != 1
            or not isinstance(params['taskTypes'], list) or 'diagnostics' not in params['taskTypes']
            or not isinstance(params['taskOperations'], list)
            or not all(isinstance(op, str) for op in params['taskOperations'])
            or set(params['taskOperations']) != {'start', 'pause', 'resume', 'cancel', 'query'}
            or ('executionMode' in params and params['executionMode'] != 'esp32_test')
            or (params['taskStatus'] == 'IDLE') == ('taskId' in params)):
        raise ValueError('Invalid node capability parameters')
    if {'capId', 'capSeq', 'sentUs'} & params.keys():
        seq, sent = params.get('capSeq'), params.get('sentUs')
        if (type(seq) is not int or not 1 <= seq <= 0xffffffff
                or type(sent) is not int or not 0 <= sent < 2**53
                or params.get('capId') != f'{boot}-{seq:08x}'):
            raise ValueError('Invalid capability measurement fields')
    return dict(v=1, type='capabilities', node_id=wire['nodeId'], boot_id=boot,
                **{(REQUIRED | OPTIONAL)[field]: value for field, value in params.items()})
