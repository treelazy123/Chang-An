"""Local development API. No cloud simulator, MQTT terminal identity or COM access."""
import asyncio
import json
import threading
import time
import uuid
from urllib.parse import urlsplit
from aiohttp import web
from changan_ugv.protocol.messages import _unique_object


def decode(text):
    return json.loads(text,object_pairs_hook=_unique_object,
        parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Non-finite JSON')))


def application(service):
    @web.middleware
    async def local_only(request, handler):
        # This adapter represents a single trusted local operator, not a cloud identity.
        if request.remote not in ('127.0.0.1','::1') or request.headers.get('Origin'):
            raise web.HTTPForbidden(text='Local native clients only')
        if urlsplit('//'+request.host).hostname not in ('127.0.0.1','localhost','::1'):
            raise web.HTTPForbidden(text='Invalid local host')
        return await handler(request)

    app=web.Application(client_max_size=16384,middlewares=[local_only])
    slots=asyncio.Semaphore(16)
    sockets=set()

    async def dispatch(packet):
        async with slots:
            return await asyncio.to_thread(service.submit_local,packet)

    async def health(request):
        return web.json_response(dict(v=1,root_id=service.tasks.ugv_id,
            broker_connected=service.connected.is_set(),mode='local-http'))

    async def request_packet(request):
        try:
            packet=decode(await request.text())
            if not isinstance(packet,dict):raise ValueError('Expected JSON object')
            rows=await dispatch(packet)
            if rows and rows[0].get('type')=='nodes':
                result=dict(rows[-1],nodes=[n for row in rows for n in row.get('nodes',[])])
            else:result=rows[0]
            return web.json_response(result)
        except (ValueError,UnicodeError) as exc:
            raise web.HTTPBadRequest(text=str(exc)) from exc
        except (ConnectionError,TimeoutError) as exc:
            raise web.HTTPServiceUnavailable(text=str(exc)) from exc

    async def catalog(request):
        return web.json_response(dict(v=1,nodes=await asyncio.to_thread(service.catalog.records)))

    async def admission(request):
        try:
            body=decode(await request.text())
            if not isinstance(body,dict):raise ValueError('Expected JSON object')
            body.update(v=1,type='node.admission',target=request.match_info['node_id'])
            return web.json_response((await dispatch(body))[0])
        except (ValueError,UnicodeError) as exc:raise web.HTTPBadRequest(text=str(exc)) from exc

    async def events(request):
        try:
            cursor=int(request.query.get('cursor','0'))
            if not 0<=cursor<=9223372036854775807:raise ValueError()
        except ValueError as exc:raise web.HTTPBadRequest(text='Invalid cursor') from exc
        if len(sockets)>=16:raise web.HTTPServiceUnavailable(text='Too many streams')
        ws=web.WebSocketResponse(heartbeat=15,max_msg_size=1024)
        await ws.prepare(request)
        sockets.add(ws)

        async def stream():
            nonlocal cursor
            last_nodes=None
            last_node_at=0
            while not ws.closed:
                packet=dict(v=1,type='task.events',msg_id=uuid.uuid4().hex,
                            deadline_unix=int(time.time())+20,cursor=cursor)
                rows=await dispatch(packet)
                body=rows[0]
                if body.get('type')=='error':
                    await ws.send_json(body)
                    break
                for event in body.get('items',[]):
                    cursor=event['cursor']
                    await ws.send_json(dict(v=1,type='task.event',node_id='ugv-service',**event))
                if time.monotonic()-last_node_at>=2:
                    last_node_at=time.monotonic()
                    rows=await dispatch(dict(v=1,type='list',msg_id=uuid.uuid4().hex,
                                             deadline_unix=int(time.time())+20))
                    nodes=[node for row in rows for node in row.get('nodes',[])]
                    signature=json.dumps(nodes,sort_keys=True)
                    if signature!=last_nodes:
                        await ws.send_json(dict(v=1,type='nodes.snapshot',nodes=nodes,
                                                broker_connected=service.connected.is_set()))
                        last_nodes=signature
                if not body.get('more'):await asyncio.sleep(.25)

        async def guarded_stream():
            try:await stream()
            finally:
                if not ws.closed:await ws.close()

        sender=asyncio.create_task(guarded_stream())
        try:
            async for message in ws:
                if message.type==web.WSMsgType.TEXT:
                    await ws.close(code=1008,message=b'Read-only event stream')
        finally:
            sender.cancel()
            await asyncio.gather(sender,return_exceptions=True)
            sockets.discard(ws)
        return ws

    async def shutdown(app):
        await asyncio.gather(*(ws.close(code=1001,message=b'Service stopping') for ws in list(sockets)))

    app.router.add_get('/api/v1/health',health)
    app.router.add_post('/api/v1/requests',request_packet)
    app.router.add_get('/api/v1/nodes/catalog',catalog)
    app.router.add_post('/api/v1/nodes/{node_id}/admission',admission)
    app.router.add_get('/api/v1/events',events)
    app.on_shutdown.append(shutdown)
    return app


class LocalAPI:
    def __init__(self,service,port=8080):
        self.service,self.port=service,port
        self.ready=threading.Event()
        self.error=None
        self.loop=None
        self.thread=threading.Thread(target=self._run,name='ugv-http',daemon=True)

    def start(self):
        self.thread.start()
        if not self.ready.wait(10):raise TimeoutError('HTTP startup timed out')
        if self.error:raise self.error

    def _run(self):
        try:asyncio.run(self._serve())
        except BaseException as exc:
            self.error=exc
            self.ready.set()

    async def _serve(self):
        self.loop=asyncio.get_running_loop()
        self.stop=asyncio.Event()
        runner=web.AppRunner(application(self.service),access_log=None)
        await runner.setup()
        try:
            site=web.TCPSite(runner,'127.0.0.1',self.port)
            await site.start()
            self.port=site._server.sockets[0].getsockname()[1]
            self.ready.set()
            await self.stop.wait()
        finally:await runner.cleanup()

    def close(self):
        if self.loop and self.loop.is_running():self.loop.call_soon_threadsafe(self.stop.set)
        if self.thread.ident:self.thread.join(15)
