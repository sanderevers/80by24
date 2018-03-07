import asyncio
import logging
import contextlib
import traceback
from collections import defaultdict
from .aqueue import FiniteQueue,Subscriber
from ..common import messages as m
from .banner import banner

class SocketOccupiedException(Exception):
    pass

class SessionInfo():
    pass

class BaseSession:
    def __init__(self,session_id):
        self.socket = None
        self.got_socket = asyncio.Event()
        self.session_id=session_id
        self.tasks = []
        self.open = True
        log.info('{}: OPEN'.format(session_id))

    async def run_socket(self,socket):
        self.set_socket(socket)
        # wait until the other side closes the socket properly
        with contextlib.suppress(asyncio.CancelledError):  # or the connection is dropped
            async for wsm in self.socket:
                await self.handle_incoming(wsm.data)
            await self.close() # on deliberate client-close: also close session
        self.unset_socket()

    def set_socket(self,socket):
        if self.socket:
            raise SocketOccupiedException()
        self.socket = socket
        self.got_socket.set()

    def unset_socket(self):
        self.socket = None
        self.got_socket.clear()

    def spawn_task(self, coro):
        task = asyncio.ensure_future(self.exceptionlogger(coro))
        self.tasks.append(task)
        return task

    async def exceptionlogger(self,coro):
        try:
            await coro
        except asyncio.CancelledError:
            pass # so we can await a task being stopped
        except:
            log.error('{}: Exception in task: {}'.format(self.session_id, traceback.format_exc()))

    async def stop_tasks(self):
        waitfor = []
        for task in self.tasks:
            if not task.done() and not task is asyncio.Task.current_task():
                task.cancel()
                waitfor.append(task)
        if waitfor:
            await asyncio.wait(waitfor) # necessary for server close

    async def send(self,text):
        socket = await self.get_socket()
        socket.send_str(text)
        log.debug('{}: > {}'.format(self.session_id, text[:20]+'...'))

    async def get_socket(self):
        await self.got_socket.wait()
        return self.socket

    async def handle_incoming(self,text):
        log.debug('{}: < {} [IGNORED]'.format(self.session_id,text))

    async def close(self):
        if self.open:
            self.open = False
            log.debug('{}: CLOSING'.format(self.session_id))
            if self.socket:
                await self.socket.close()
                self.unset_socket()
            await self.stop_tasks()
            log.info('{}: CLOSED'.format(self.session_id))

class FeedSession(BaseSession):
    def __init__(self,session_id):
        super().__init__(session_id)
        self.info = SessionInfo()
        self.sendq = FiniteQueue()
        self.recvq = FiniteQueue()
        self.spawn_task(self.process_sendq())
        self.spawn_task(self.run_protocol())
        self.spawn_task(self.listen_info())
        self.spawn_task(self.send_passphrase())
        self.subscriberlists = defaultdict(list) # message class -> [Future]

    async def process_sendq(self):
        async for msg in self.sendq:
            while True:
                try:
                    await self.send(msg)
                    break
                except RuntimeError as err: #connection drop
                    log.info('{}: retry sending {} because of {}'.format(self.session_id, msg, err))

    async def handle_incoming(self,text):
        # dispatch to recvq so we can react immediately on connection drop/close
        await self.recvq.put(m.Message.parse(text))

    async def schedule_send(self,msg):
        await self.sendq.put(str(msg))

    async def run_protocol(self):
        await self.schedule_banner()
        async for msg in self.recvq:
            subs = self.subscriberlists[msg.__class__]
            if subs:
                log.debug('{}: < {}'.format(self.session_id, msg.__class__.__name__))
                for sub in subs:
                    sub.set_result(msg)
            else:
                log.debug('{}: No subscribers for {}'.format(self.session_id,msg.__class__.__name__))

    async def schedule_banner(self):
        for line in banner.splitlines():
            await self.schedule_send(m.Line(line))

    async def close(self):
        await super().close()

    async def subscribe_once(self,mclass):
        fut = asyncio.Future()
        self.subscriberlists[mclass].append(fut)
        res = await fut
        self.subscriberlists[mclass].remove(fut)
        return res

    async def listen_info(self):
        async for msg in Subscriber(self.subscriberlists[m.Info]):
            for k, v in msg.__dict__.items():
                setattr(self.info, k, v)
            log.debug('{}: info acquired'.format(self.session_id))

    async def send_passphrase(self):
        msg = await self.subscribe_once(m.Info)
        text = 'Access this terminal with the following passphrase:'
        await self.schedule_send(m.Line(text))
        await self.schedule_send(m.Line(msg.passphrase))


    async def read_line_conv(self,socket,line=True,echo=False):
        rls = BaseSession(self.session_id+'_R')

        async def copy_from_feedclient():
            try:
                if line:
                    await self.schedule_send(m.ReadLine())
                    lr = await self.subscribe_once(m.LineRead)
                    await rls.send(lr.text)
                else:
                    await self.schedule_send(m.ReadKey(echo=echo))
                    kr = await self.subscribe_once(m.KeyRead)
                    await rls.send(kr.key)
            except asyncio.CancelledError:
                log.info('{} closing because parent session closes:'.format(rls.session_id))
            finally:
                await asyncio.shield(rls.close()) # otherwise it will indirectly cancel itself

        copy_task = self.spawn_task(copy_from_feedclient())
        await rls.run_socket(socket)
        await rls.close()
        if not copy_task.done():
            copy_task.cancel()
            await copy_task


log = logging.getLogger(__name__)