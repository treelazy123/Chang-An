"""Direct HTTP requests and resumable WebSocket events; no MQTT or serial identity."""
import asyncio
import concurrent.futures
import json
import threading
from urllib.parse import urlsplit
import aiohttp
from ..mci import envelope,legacy_response,legacy_event


class HTTPClient:
    def __init__(self,base_url='http://127.0.0.1:8080', *, events=True):
        parsed=urlsplit(base_url)
        if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.query or parsed.fragment or parsed.username:
            raise ValueError('Expected HTTP(S) backend URL')
        self.base_url=base_url.rstrip('/')
        self.on_event=lambda body:None
        self.on_wire=lambda body:None
        self.cursor=0
        self.incident_cursor=0
        self.closed=False
        self.session=None
        self.event_task=None
        self.loop=asyncio.new_event_loop()
        self.thread=threading.Thread(target=self._run,name='car-http',daemon=True)
        self.thread.start()
        connection=asyncio.run_coroutine_threadsafe(self._connect(events),self.loop)
        try:
            connection.result(10)
        except BaseException:
            connection.cancel()
            self.close()
            raise

    def _run(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()
        self.loop.close()

    async def _connect(self,events):
        self.session=aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15))
        async with self.session.get(self.base_url+'/api/v1/health') as reply:
            reply.raise_for_status()
            body=await reply.json()
            if body.get('v')!=1:raise ValueError('Unsupported backend API')
            self.root_id=body.get('root_id')
        catalog=await self._mci('listMethod',dict(service='Mesh_Node',method='Get_Status'))
        if catalog.get('specVersion')!='1.0.0':raise ValueError('MCI unavailable; update and restart UGV Service')
        if events:self.event_task=asyncio.create_task(self._events())

    async def _request(self,packet):
        body=await self._mci('call',envelope(packet))
        return legacy_response(packet,body)

    async def _mci(self,operation,packet):
        # Mutations are sent once. On timeout callers query by their task/request ID.
        path='/api/v1/mci/'+operation
        async with self.session.post(self.base_url+path,
                                     data=json.dumps(packet,allow_nan=False).encode('utf-8'),
                                     headers={'Content-Type':'application/json'}) as reply:
            try:body=await reply.json()
            except (aiohttp.ContentTypeError,ValueError):
                body=dict(error=dict(code='HTTP_ERROR',message='MCI endpoint unavailable; update and restart UGV Service'))
            self.on_wire(dict(protocol='MCI',path=path,request=packet,response=body,httpStatus=reply.status))
            if reply.status==404:raise ConnectionError('MCI endpoint missing; update and restart UGV Service')
            reply.raise_for_status()
            if not isinstance(body,dict):raise ValueError('Invalid MCI response')
            return body

    def discover(self,params=None):
        if self.closed:raise ConnectionError('HTTP transport is closed')
        result=asyncio.run_coroutine_threadsafe(self._mci('listMethod',params or {}),self.loop).result(16)
        if 'error' in result:raise ValueError(str(result['error']))
        if result.get('specVersion')!='1.0.0':raise ValueError('Unsupported MCI version')
        return result

    async def _capability_test(self,action,body):
        path='/api/v1/capability-tests'
        if action in ('get','export'):
            import re
            batch=body.get('batch_id','')
            if not re.fullmatch(r'[A-Za-z0-9_-]{1,32}',batch):raise ValueError('请选择有效测试批次')
            path+='/'+batch
        if action=='export':
            format=body.get('format','jsonl')
            if format not in ('csv','jsonl'):raise ValueError('不支持的导出格式')
            path+='/export?format='+format
        method='POST' if action=='start' else 'GET'
        async with self.session.request(method,self.base_url+path,json=body if action=='start' else None) as response:
            if response.status>=400:
                raise ValueError(await response.text())
            return await response.text() if action=='export' else await response.json()

    def capability_test(self,action,body=None):
        if self.closed:raise ConnectionError('HTTP transport is closed')
        if action not in ('start','get','list','export'):raise ValueError('Invalid capability test action')
        return asyncio.run_coroutine_threadsafe(self._capability_test(action,body or {}),self.loop).result(16)

    def request(self,packet):
        if self.closed:raise ConnectionError('HTTP transport is closed')
        future=asyncio.run_coroutine_threadsafe(self._request(packet),self.loop)
        try:return future.result(16)
        except concurrent.futures.TimeoutError as exc:
            future.cancel()
            raise TimeoutError('Backend timeout; request was not retried, query task state') from exc
        except aiohttp.ClientError as exc:raise ConnectionError(str(exc)) from exc

    async def _events(self):
        while not self.closed:
            try:
                async with self.session.ws_connect(self.base_url+'/api/v1/events',
                                                   params={'format':'mci','cursor':self.cursor,'incidentCursor':self.incident_cursor},heartbeat=15) as ws:
                    async for message in ws:
                        if message.type!=aiohttp.WSMsgType.TEXT:continue
                        body=json.loads(message.data)
                        if 'method' not in body:raise ValueError('Expected MCI notification; update and restart UGV Service')
                        self.on_wire(dict(protocol='MCI',notification=body))
                        if 'incidentCursor' in body:
                            if body['incidentCursor']<=self.incident_cursor:continue
                            self.incident_cursor=body['incidentCursor']
                        body=legacy_event(body)
                        if body.get('type')=='task.event':
                            cursor=body.get('cursor')
                            if type(cursor) is not int or cursor<=self.cursor:continue
                            self.cursor=cursor
                        self.on_event(body)
            except (aiohttp.ClientError,OSError,ValueError):
                pass
            if not self.closed:await asyncio.sleep(1)

    async def _close(self):
        if self.event_task:
            self.event_task.cancel()
            await asyncio.gather(self.event_task,return_exceptions=True)
        if self.session:await self.session.close()

    def close(self):
        if self.closed:return
        self.closed=True
        try:asyncio.run_coroutine_threadsafe(self._close(),self.loop).result(5)
        finally:
            self.loop.call_soon_threadsafe(self.loop.stop)
            self.thread.join(5)
