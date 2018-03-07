from .exceptions import AbortRequestException
from .state import State
from ..common import messages as m
from ..common import id_generator
from .session import FeedSession
from aiohttp import web

routes = web.RouteTableDef()

def augment(handler):
    def augmented(req):
        info = get_req_info(req)
        return handler(req,**info)
    return augmented

@routes.get('/tty/id')
@augment
async def find_id(req, path):
    try:
        words = req.query.getall('phrase')
    except KeyError:
        raise AbortRequestException(status=400, text='Usage: GET {}?phrase=example%20pass%20phrase\n'.format(path))
    ttyId = id_generator.id_hash(words)
    return web.Response(text=ttyId)

@routes.get('/tty/{ttyId}/readline')
@augment
async def read_line(req, path, ttyId):
    session = find_session(req.app, ttyId)
    # if client.rlc:
    #     return web.Response(status=409, text='This endpoint is already in use.')
    socket = web.WebSocketResponse(heartbeat=15)
    await socket.prepare(req)
    await session.read_line_conv(socket)
    return socket

@routes.get('/tty/{ttyId}/readkey')
@augment
async def read_key(req, path, ttyId):
    session = find_session(req.app, ttyId)
    # if client.rlc:
    #     return web.Response(status=409, text='This endpoint is already in use.')
    socket = web.WebSocketResponse(heartbeat=15)
    await socket.prepare(req)
    await session.read_line_conv(socket,line=False,echo=parse_echo(req.query.getall('echo',[])))
    return socket

def parse_echo(queryvals):
    return 'on' in queryvals

@routes.get('/feed/{ttyId}')
@augment
async def feed_endpoint(req, path, ttyId):
    sessions = State.of(req.app).sessions
    if ttyId in sessions:
        session = sessions[ttyId]
        if session.socket:
            return web.Response(status=409, text='This endpoint is already in use.')
    else:
        session = FeedSession(ttyId)
        sessions[ttyId] = session

    socket = web.WebSocketResponse(heartbeat=15)
    await socket.prepare(req)
    await session.run_socket(socket)
    if not session.open:
        del sessions[ttyId]
    return socket

@routes.post('/tty/{ttyId}/line')
@augment
async def post_line(req, path, ttyId):
    session = find_session(req.app, ttyId)
    text = await req.text()
    opts = parse_align_opts(req.query.getall('align',[]),'h')

    await session.schedule_send(m.Line(text,**opts))
    return web.Response(status=200)

@routes.post('/tty/{ttyId}/page')
@augment
async def post_page(req, path, ttyId):
    session = find_session(req.app, ttyId)
    text = await req.text()
    opts = parse_align_opts(req.query.getall('align',[]),'hv')

    await session.schedule_send(m.Page(text,**opts))
    return web.Response(status=200)

def parse_align_opts(queryvals,hv):
    vals = [v for qv in queryvals for v in qv.split()]
    halign = [val for val in vals if val in ('left','center','right')]
    valign = [val for val in vals if val in ('top','middle','bottom')]
    opts = {}
    if halign and 'h' in hv:
        opts['halign'] = halign[0]
    if valign and 'v' in hv:
        opts['valign'] = valign[0]
    return opts

@routes.post('/tty/{ttyId}/cls')
@augment
async def post_cls(req, path, ttyId):
    session = find_session(req.app, ttyId)
    await session.schedule_send(m.Cls())
    return web.Response(status=200)

def get_req_info(req):
    info = dict(req.match_info)
    info['path'] = req.match_info.route.url_for(**req.match_info)
    return info

def find_session(app, ttyId):
    try:
        return State.of(app).sessions[ttyId]
    except KeyError:
        raise AbortRequestException(status=403, text='magnie')

