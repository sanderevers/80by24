import logging
import asyncio
import contextlib
from .conf import BotConfig
from run80by24.common.id_generator import id_hash

class FiniteQueue(asyncio.queues.Queue):
    End = object()
    def __aiter__(self):
        return self
    async def close(self):
        await self.put(FiniteQueue.End) # how to dispatch this to all getters?
    async def __anext__(self):
        elt = await self.get()
        if elt is FiniteQueue.End:
            # maybe here? self.put_nowait(FiniteQueue.End)
            raise StopAsyncIteration
        else:
            return elt

def parse(text):
    if text.startswith('/'):
        hd, *tl = text.split()
        return hd[1:],tl
    return None,text

class Chat:
    def __init__(self,chat_id,clientSession):
        self.chat_id = chat_id
        self.clientSession = clientSession
        self.recvq = FiniteQueue()
        self.ttyId = None
        self.task = asyncio.ensure_future(self.run())

    async def run(self):
        with contextlib.suppress(asyncio.CancelledError):
            async for text in self.recvq:
                cmd,args = parse(text)
                if cmd=='start':
                    await self.send(start_text)
                    await self.pw_conversation()
                elif cmd=='help':
                    await self.send(help_text)
                elif cmd=='pw':
                    if len(args)==0:
                        await self.pw_conversation()
                    else:
                        success = await self.set_tty(args)
                        if success:
                            await self.send(pw_success_text)
                        else:
                            await self.send("Sorry, that didn't work.")
                elif cmd is None:
                    if self.ttyId:
                        await self.tty_cmd('line',args)
                    else:
                        await self.send('Please identify your terminal first. Use /pw')
                else:
                    await self.send("I don't know that command.")

    async def dispatch(self,text):
        await self.recvq.put(text)

    async def pw_conversation(self):
        await self.send(ask_pw_text)
        await self.expect_pw()

    async def expect_pw(self):
        while True:
            text = await self.recvq.get()
            cmd,args = parse(text)
            if cmd is None:
                success = await self.set_tty(args.split())
                if success:
                    await self.send(pw_success_text)
                    break
                else:
                    await self.send('Sorry, try again:')
            else:
                await self.send("That's not a password.")
                break

    async def set_tty(self,words):
        log.debug('trying {}'.format(words))
        self.ttyId = id_hash(words)
        log.debug('hash {}'.format(self.ttyId))
        success = await self.tty_cmd('cls',None)
        if not success:
            self.ttyId = None
        return success

    async def tty_cmd(self,cmd,body):
        assert(self.ttyId is not None)
        url = BotConfig.tty_endpoint.format(ttyId=self.ttyId) + '/' + cmd
        async with self.clientSession.post(url,data=body) as resp:
            #json = await resp.json()
            log.debug('80by24 reply: {}: {}'.format(resp.status,'json'))
            if resp.status==200:
                return True
            else:
                return False

    async def send(self,text):
        url = BotConfig.msg_endpoint.format(apikey=BotConfig.apikey)
        data = {
            'chat_id':self.chat_id,
            'text':text
        }
        async with self.clientSession.post(url,json=data) as resp:
            json = await resp.json()
            log.debug('reply: {}: {}'.format(resp.status,json))

    async def close(self):
        self.task.cancel()
        await self.send("Goodbye, cruel world.")

start_text = 'Hi! I can relay messages to your 80by24.net terminal.'
help_text = '''1. Download, install and run the 80by24.net client. It will show a passphrase.
2. Say to me: /pw [your passphrase]
3. Everything you say to me after that will show up at your terminal.'''
ask_pw_text = "What is your terminal's passphrase?"
pw_success_text = 'Thank you! Anything you say to me from now will show up at your terminal.'

log = logging.getLogger(__name__)