"""Direct HTTP requests and resumable WebSocket events; no MQTT or serial identity."""
import asyncio
import concurrent.futures
import json
import threading
from urllib.parse import urlsplit
import aiohttp


class HTTPClient:
    def __init__(self,base_url='http://127.0.0.1:8080', *, events=True):
        parsed=urlsplit(base_url)
        if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.query or parsed.fragment or parsed.username:
            raise ValueError('Expected HTTP(S) backend URL')
        self.base_url=base_url.rstrip('/')
        self.on_event=lambda body:None
        self.cursor=0
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
        if events:self.event_task=asyncio.create_task(self._events())

    async def _request(self,packet):
        # Mutations are sent once. On timeout callers query by their task/request ID.
        async with self.session.post(self.base_url+'/api/v1/requests',
                                     data=json.dumps(packet,allow_nan=False).encode('utf-8'),
                                     headers={'Content-Type':'application/json'}) as reply:
            reply.raise_for_status()
            body=await reply.json()
            if not isinstance(body,dict) or body.get('msg_id')!=packet.get('msg_id'):
                raise ValueError('Mismatched backend response')
            return body

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
                                                   params={'cursor':self.cursor},heartbeat=15) as ws:
                    async for message in ws:
                        if message.type!=aiohttp.WSMsgType.TEXT:continue
                        body=json.loads(message.data)
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
