"""Local HTTP administration console; no node credentials or serial access."""
import argparse
import json
import time
import urllib.request
from changan_ugv.protocol.messages import command
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base-url',default='http://127.0.0.1:8080')
    p.add_argument('--command',default='list')
    args=p.parse_args()
    packet=command(args.command);packet['deadline_unix']=int(time.time())+20
    req=urllib.request.Request(args.base_url.rstrip('/')+'/api/v1/requests',data=json.dumps(packet).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=15) as response:print(json.dumps(json.load(response),ensure_ascii=False))
if __name__=='__main__':main()
