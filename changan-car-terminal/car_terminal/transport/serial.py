"""C6 native USB serial adapter."""
from ..serial_link import RootLink
class SerialClient:
    def __init__(self,port):
        import serial
        device=serial.Serial(port=None,baudrate=115200,timeout=.1,write_timeout=1)
        device.dtr=device.rts=False;device.port=port;device.open()
        self.link=RootLink(device).start()
    def request(self,packet):return self.link.request(packet,timeout=15)
    def close(self):self.link.close()
