"""Direct-terminal adapter selection and root radio topology; no network required."""
import unittest
from unittest.mock import patch
from car_terminal.gui import open_transport
from car_terminal.network import network_snapshot
from car_terminal.transport.http import HTTPClient
from car_terminal.client import request_line


class HTTPSettings(unittest.TestCase):
    def test_admission_command_uses_explicit_revision(self):
        class Transport:
            def request(self,packet):
                self.packet=packet
                return dict(ok=True,type='node.admission.reply')
        client=Transport()
        request_line(client,'node revoke ugv-001 4')
        self.assertEqual('revoked',client.packet['trust_status'])
        self.assertEqual(4,client.packet['expected_revision'])
        self.assertEqual('node.admission',client.packet['type'])
    def test_http_requires_no_mqtt_keys_or_com_port(self):
        with patch('car_terminal.gui.HTTPClient') as client:
            result=open_transport(dict(base_url='http://127.0.0.1:8080'))
            client.assert_called_once_with('http://127.0.0.1:8080')
            self.assertIs(result,client.return_value)

    def test_invalid_url_is_rejected_before_starting_io(self):
        for url in ('mqtt://localhost','file:///secret','http://user:password@localhost','http://localhost?token=x'):
            with self.assertRaises(ValueError):HTTPClient(url)

    def test_host_radio_report_is_root_and_matches_second_layer_parent(self):
        rows=[dict(node_id='ugv-root',ready=True,status=dict(execution_host='local',
                  network_status=dict(fresh=True,age_s=1,status=dict(role='ugv_root',level=1,
                      ap_mac='aa:bb:cc:00:00:01',parent_connected=False)))),
              dict(node_id='ugv-001',ready=True,status=dict(role='ugv',level=2,
                   ap_mac='aa:bb:cc:00:00:02',parent_bssid='aa:bb:cc:00:00:01',parent_connected=True))]
        nodes=network_snapshot(rows)
        self.assertEqual('root',nodes['ugv-root']['group'])
        self.assertEqual('ugv-root',nodes['ugv-001']['parent'])
