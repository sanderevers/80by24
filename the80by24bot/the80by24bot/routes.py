from .exceptions import AbortRequestException
from .state import State
from .conf import BotConfig
from .chat import Chat
from aiohttp import web
import logging

routes = web.RouteTableDef()

update_path = '/bot/{secret}/update'

@routes.post(update_path)
async def recv_updates(req):
    if req.match_info['secret'] != BotConfig.apikey:
        raise AbortRequestException()

    state = State.of(req.app)

    update = await req.json()
    logging.debug(str(update))


    msg = update.get('message')
    if msg:
        text = msg['text']
        chat_id = msg['chat']['id']
        chat = state.chats.get(chat_id)
        if chat is None:
            chat = Chat(chat_id, state.clientSession)
            state.chats[chat_id] = chat
        await chat.dispatch(text)
    return web.Response(status=200)

log = logging.getLogger(__name__)