import logging
from aiohttp import web, ClientSession
import asyncio

from .routes import routes, update_path
from .state import State
from .exceptions import AbortRequestException
from .conf import BotConfig

def create():
    app = web.Application(middlewares=[exception_mapper])
    State.init(app)
    app.router.add_routes(routes)
    app.on_startup.append(init_client_and_webhook)
    app.on_shutdown.append(close_chats_client_webhook)
    return app

async def init_client_and_webhook(app):
    session = ClientSession()
    State.of(app).clientSession = session
    url = BotConfig.register_endpoint.format(apikey=BotConfig.apikey)
    data = {
        'url': BotConfig.bot_host + update_path.format(secret=BotConfig.apikey),
        'allowed_updates' : ['message']
    }
    async with session.post(url,json=data) as resp:
        json = await resp.json()
        log.debug('{} on webhook register {}: {}'.format(resp.status,data['url'],json))

async def close_chats_client_webhook(app):
    chat_closers = [c.close() for c in State.of(app).chats.values()]
    if len(chat_closers) > 0:
        await asyncio.wait(chat_closers)
    session = State.of(app).clientSession
    url = BotConfig.register_endpoint.format(apikey=BotConfig.apikey)
    data = {'url':''}
    async with session.post(url,json=data) as resp:
        json = await resp.json()
        log.debug('{} on webhook deregister: {}'.format(resp.status, json))
    await session.close()

@web.middleware
async def exception_mapper(request,handler):
    try:
        resp = await handler(request)
        return resp
    except AbortRequestException as e:
        return web.Response(status=e.status, text=e.text)


log = logging.getLogger(__name__)

