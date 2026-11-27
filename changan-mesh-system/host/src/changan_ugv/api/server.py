"""Local development API. No cloud simulator, MQTT terminal identity or COM access."""
import asyncio
import json
import threading
import time
import uuid
from ipaddress import ip_address, ip_network
from urllib.parse import urlsplit
from aiohttp import web
from changan_ugv.protocol.messages import _unique_object


def decode(text):
    return json.loads(text,object_pairs_hook=_unique_object,
        parse_constant=lambda _:(_ for _ in ()).throw(ValueError('Non-finite JSON')))


def application(service,allowed_peers=('127.0.0.1','::1'),allowed_hosts=('127.0.0.1','localhost','::1')):
    allowed_peers=tuple(ip_network(peer,strict=False) if isinstance(peer,str) else peer for peer in allowed_peers)
    from changan_ugv.mci import MCI
    mci=MCI(service,authorize=getattr(service,'mci_authorize',None))
    @web.middleware
    async def local_only(request, handler):
        # This adapter represents one trusted operator; peers and Host are explicit allowlists.
        try:remote=ip_address(request.remote)
        except ValueError:raise web.HTTPForbidden(text='Client not allowed')
        if not any(remote in network for network in allowed_peers) or request.headers.get('Origin'):
            raise web.HTTPForbidden(text='Client not allowed')
        if urlsplit('//'+request.host).hostname not in allowed_hosts:
            raise web.HTTPForbidden(text='Invalid host')
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

    async def mci_request(request):
        try:
            packet=decode(await request.text())
            async with slots:
                handler=mci.discover if request.match_info['operation']=='listMethod' else mci.call
                result=await asyncio.to_thread(handler,packet)
            return web.json_response(result)
        except (ValueError,UnicodeError):
            return web.json_response(mci.error('INVALID_ARGUMENT','Invalid JSON'),status=400)

    async def admission(request):
        try:
            body=decode(await request.text())
            if not isinstance(body,dict):raise ValueError('Expected JSON object')
            body.update(v=1,type='node.admission',target=request.match_info['node_id'])
            return web.json_response((await dispatch(body))[0])
        except (ValueError,UnicodeError) as exc:raise web.HTTPBadRequest(text=str(exc)) from exc

    async def capability_tests(request):
        manager=getattr(service,'capability_measurements',None)
        if manager is None:raise web.HTTPServiceUnavailable(text='Capability measurement service unavailable')
        try:
            if request.method=='POST':
                body=decode(await request.text())
                result=await asyncio.to_thread(manager.start,body)
            elif 'batch_id' not in request.match_info:
                result=dict(v=1,items=await asyncio.to_thread(manager.list))
            elif request.match_info.get('export'):
                format=request.query.get('format','jsonl')
                content=await asyncio.to_thread(manager.export,request.match_info['batch_id'],format)
                return web.Response(text=content,content_type='text/csv' if format=='csv' else 'application/x-ndjson')
            else:result=await asyncio.to_thread(manager.get,request.match_info['batch_id'])
            return web.json_response(result)
        except (ValueError,UnicodeError) as exc:raise web.HTTPBadRequest(text=str(exc)) from exc

    async def events(request):
        mci_format=request.query.get('format')=='mci'
        if mci_format and not all(mci.authorize('subscribe',key) for key in
                [('Mesh_Task','Ntf_TaskChanged'),('Mesh_Node','Ntf_NodeSnapshot'),('Mesh_Task','Et_TestIncident')]):
            return web.json_response(mci.error('PERMISSION_DENIED','Subscription denied'),status=403)
        try:
            cursor=int(request.query.get('cursor','0'))
            if not 0<=cursor<=9223372036854775807:raise ValueError()
            incident_cursor=int(request.query.get('incidentCursor','0'))
            if not 0<=incident_cursor<=9223372036854775807:raise ValueError()
        except ValueError as exc:raise web.HTTPBadRequest(text='Invalid cursor') from exc
        if len(sockets)>=16:raise web.HTTPServiceUnavailable(text='Too many streams')
        ws=web.WebSocketResponse(heartbeat=15,max_msg_size=1024)
        await ws.prepare(request)
        sockets.add(ws)
        node_changed=asyncio.Event()
        loop=asyncio.get_running_loop()
        def wake_nodes():
            loop.call_soon_threadsafe(node_changed.set)
        subscribe=getattr(service,'subscribe_nodes',None)
        unsubscribe=subscribe(wake_nodes) if subscribe else lambda:None

        async def stream():
            nonlocal cursor,incident_cursor
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
                    await ws.send_json(mci.notification('Mesh_Task','Ntf_TaskChanged',event) if mci_format else
                        dict(v=1,type='task.event',node_id='ugv-service',**event))
                if mci_format:
                    incidents=(await dispatch(dict(v=1,type='task.events',scope='incidents',cursor=incident_cursor,
                        msg_id=uuid.uuid4().hex,deadline_unix=int(time.time())+20)))[0]
                    for event in incidents.get('items',[]):
                        incident_cursor=incidents['cursor']
                        await ws.send_json(dict(mci.notification('Mesh_Task','Et_TestIncident',event),incidentCursor=incident_cursor))
                if node_changed.is_set() or time.monotonic()-last_node_at>=2:
                    # Clear before querying: an update during dispatch must trigger another snapshot.
                    node_changed.clear()
                    last_node_at=time.monotonic()
                    rows=await dispatch(dict(v=1,type='list',msg_id=uuid.uuid4().hex,
                                             deadline_unix=int(time.time())+20))
                    nodes=[node for row in rows for node in row.get('nodes',[])]
                    snapshot=dict(nodes=nodes,broker_connected=service.connected.is_set())
                    signature=json.dumps(snapshot,sort_keys=True)
                    if signature!=last_nodes:
                        await ws.send_json(mci.notification('Mesh_Node','Ntf_NodeSnapshot',snapshot) if mci_format else
                            dict(v=1,type='nodes.snapshot',**snapshot))
                        last_nodes=signature
                if not body.get('more'):
                    try:await asyncio.wait_for(node_changed.wait(),timeout=.25)
                    except asyncio.TimeoutError:pass

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
            unsubscribe()
            sender.cancel()
            await asyncio.gather(sender,return_exceptions=True)
            sockets.discard(ws)
        return ws

    async def shutdown(app):
        await asyncio.gather(*(ws.close(code=1001,message=b'Service stopping') for ws in list(sockets)))

    app.router.add_get('/api/v1/health',health)
    app.router.add_post('/api/v1/capability-tests',capability_tests)
    app.router.add_get('/api/v1/capability-tests',capability_tests)
    app.router.add_get('/api/v1/capability-tests/{batch_id}/{export:export}',capability_tests)
    app.router.add_get('/api/v1/capability-tests/{batch_id}',capability_tests)
    app.router.add_post('/api/v1/mci/{operation:listMethod|call}',mci_request)
    app.router.add_post('/api/v1/requests',request_packet)
    app.router.add_get('/api/v1/nodes/catalog',catalog)
    app.router.add_post('/api/v1/nodes/{node_id}/admission',admission)
    app.router.add_get('/api/v1/events',events)
    app.on_shutdown.append(shutdown)
    return app


class LocalAPI:
    def __init__(self,service,port=8080,host='127.0.0.1',allowed_peers=('127.0.0.1','::1')):
        self.service,self.port,self.host=service,port,host
        self.allowed_peers=tuple(ip_network(peer,strict=False) for peer in allowed_peers)
        self.allowed_hosts=tuple(dict.fromkeys(('127.0.0.1','localhost','::1',host)))
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
        runner=web.AppRunner(application(self.service,self.allowed_peers,self.allowed_hosts),access_log=None)
        await runner.setup()
        try:
            site=web.TCPSite(runner,self.host,self.port)
            await site.start()
            self.port=site._server.sockets[0].getsockname()[1]
            self.ready.set()
            await self.stop.wait()
        finally:await runner.cleanup()

    def close(self):
        if self.loop and self.loop.is_running():self.loop.call_soon_threadsafe(self.stop.set)
        if self.thread.ident:self.thread.join(15)
