"""Bounded ESP32 workflow-test contracts. No physical mission execution."""
import re

WORKFLOW_ROLES = {'patrol': 'micro_uav', 'anomaly_review': 'uav'}
WORKFLOW_KINDS = tuple(WORKFLOW_ROLES)
SERVICE_SUFFIX = {'patrol': 'patrol', 'anomaly_review': 'anomaly-review'}
MODE = 'esp32_test'
VERDICTS = ('confirmed', 'cleared', 'inconclusive')


def token(value, maximum=32):
    return isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_-]{1,' + str(maximum) + '}', value) is not None


def config_valid(value, kind):
    fields = {'patrol': {'execution_mode','area_id','point_ids','point_duration_s','anomaly_point'},
              'anomaly_review': {'execution_mode','event_id','test_verdict','duration_s'}}[kind]
    if not isinstance(value, dict) or set(value) - fields:
        raise ValueError('invalid_workflow_config')
    if value.get('execution_mode') != MODE:
        raise ValueError('esp32_test_mode_required')
    value = dict(value)
    if kind == 'patrol':
        points = value.get('point_ids')
        if (not token(value.get('area_id'),12) or not isinstance(points,list) or not 1 <= len(points) <= 3
            or any(not token(p,12) for p in points) or len(set(points)) != len(points)):
            raise ValueError('invalid_patrol_points')
        value.setdefault('point_duration_s',3)
        value.setdefault('anomaly_point',0)
        if type(value['point_duration_s']) is not int or not 1 <= value['point_duration_s'] <= 60:
            raise ValueError('invalid_point_duration')
        if type(value['anomaly_point']) is not int or not 0 <= value['anomaly_point'] <= len(points):
            raise ValueError('invalid_anomaly_point')
    else:
        if not token(value.get('event_id')):
            raise ValueError('invalid_event_id')
        value.setdefault('test_verdict','inconclusive')
        value.setdefault('duration_s',5)
        if value['test_verdict'] not in VERDICTS:
            raise ValueError('invalid_test_verdict')
        if type(value['duration_s']) is not int or not 1 <= value['duration_s'] <= 60:
            raise ValueError('invalid_review_duration')
    return value
