from pathlib import Path
import json
import queue
import sys
import threading
import time
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from car_terminal.protocol import encode,Decoder,command
from car_terminal.serial_link import RootLink
from car_terminal.client import request_line
class FakeSerial:
    def __init__(self):self.input=queue.Queue();self.closed=False;self.decoder=Decoder();self.writes=0
    def read(self,count):
        try:return self.input.get(timeout=.02)
        except queue.Empty:return b''
    def write(self,data):
        self.writes+=1
        for request in self.decoder.feed(data):
            msg=request['msg_id']
            if request['type']=='list':
                replies=[dict(v=1,type='nodes',msg_id=msg,nodes=[dict(node_id='uav-001',ready=True)],more=True),
                         dict(v=1,type='nodes',msg_id=msg,nodes=[dict(node_id='micro-002',ready=True)],more=True),
                         dict(v=1,type='nodes',msg_id=msg,nodes=[],more=False)]
            else:
                replies=[dict(v=1,type='ack',msg_id=msg,node_id='wrong-node',ok=True),
                         dict(v=1,type='ack',msg_id=msg,node_id=request['target'],ok=True)]
            for reply in replies:
                wire=encode(reply)
                for i in range(0,len(wire),7):self.input.put(wire[i:i+7])
        return len(data)
    def close(self):self.closed=True
class TerminalTests(unittest.TestCase):
    def test_protocol_golden_vector(self):
        import binascii,struct
        body=b'{"v":1,"type":"list"}'
        wire=struct.pack('!4sHH',b'MLT1',len(body),binascii.crc_hqx(body,0xffff))+body
        self.assertEqual(wire,encode(dict(v=1,type='list')))
        self.assertEqual([dict(v=1,type='list')],Decoder().feed(wire))
    def test_serial_pages_are_collected_and_wrong_ack_is_ignored(self):
        serial=FakeSerial();link=RootLink(serial).start()
        try:
            result=link.request(command('list'),timeout=2)
            self.assertEqual(['uav-001','micro-002'],[r['node_id'] for r in result['nodes']])
            ack=link.request(command('ping micro-002'),timeout=2)
            self.assertEqual('micro-002',ack['node_id'])
        finally:link.close()
    def test_frontend_adds_deadline_and_does_not_manage_registry_or_clock(self):
        seen=[]
        class Client:
            def request(self,packet):seen.append(packet);return dict(v=1,type='nodes',nodes=[])
        self.assertEqual([],request_line(Client(),'list'))
        self.assertIn('deadline_unix',seen[0]);self.assertNotIn('certificate',seen[0])
if __name__=='__main__':unittest.main()
