"""Car business requests and compatibility exports for transport adapters."""
import time
from .protocol import command
from .transport import SerialClient,MQTTClient
def request_line(client,line):
    if line.strip()=='help' or line.strip().startswith('task '):
        from .tasks import task_line
        return task_line(client,line)
    packet=command(line);packet['deadline_unix']=int(time.time())+20
    response=client.request(packet)
    if response.get('type')=='error':raise ValueError(response.get('error','UGV rejected request'))
    return response['nodes'] if response.get('type')=='nodes' else response
