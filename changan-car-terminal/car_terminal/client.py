"""Car business requests and compatibility exports for transport adapters."""
import time
import shlex
import uuid
from .protocol import command
from .transport import HTTPClient
def request_line(client,line):
    if line.strip().startswith('node '):
        words=shlex.split(line)
        if len(words)!=4 or words[1] not in ('admit','revoke','pending'):
            raise ValueError('Usage: node admit|revoke|pending NODE_ID EXPECTED_REVISION')
        response=client.request(dict(v=1,type='node.admission',msg_id=uuid.uuid4().hex,
            deadline_unix=int(time.time())+20,target=words[2],expected_revision=int(words[3]),
            trust_status={'admit':'trusted','revoke':'revoked','pending':'pending'}[words[1]]))
        if response.get('type')=='error':raise ValueError(response.get('error'))
        return response
    if line.strip() in ('help','services') or line.strip().startswith('task '):
        from .tasks import task_line
        return task_line(client,line)
    packet=command(line);packet['deadline_unix']=int(time.time())+20
    response=client.request(packet)
    if response.get('type')=='error':raise ValueError(response.get('error','UGV rejected request'))
    return response['nodes'] if response.get('type')=='nodes' else response
