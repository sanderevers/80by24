import asyncio
import logging
from aiohttp import web

from .routes import routes
from .state import State
from .exceptions import AbortRequestException

def create():
    app = web.Application(middlewares=[cors_header, exception_mapper])
    State.init(app)
    app.router.add_routes(routes)
    app.on_shutdown.append(close_websockets)
    return app

# async def shutdown_close(ws):
#    await ws.close(code=http.WSCloseCode.GOING_AWAY, message='Server shutdown')
#    log.debug('socket status: {}:{}'.format(ws.closed,ws.close_code))

async def close_websockets(app):
    session_closers = [c.close() for c in State.of(app).sessions.values()]
    if len(session_closers)>0:
        await asyncio.wait(session_closers)
    log.debug('closed {} clients'.format(len(session_closers)))


@web.middleware
async def cors_header(request,handler):
    resp = await handler(request)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp

@web.middleware
async def exception_mapper(request,handler):
    try:
        resp = await handler(request)
        return resp
    except AbortRequestException as e:
        return web.Response(status=e.status, text=e.text)


log = logging.getLogger(__name__)

