import asyncio
import logging
import contextlib
from collections import defaultdict
from .aqueue import FiniteQueue,Subscriber
from ..common import messages as m
from .banner import banner

class SocketOccupiedException(Exception):
    pass

class SessionClosedException(Exception):
    pass

class BaseSession:
    def __init__(self,session_id):
        self.socket = None
        self.got_socket = asyncio.Event()
        self.session_id=session_id
        self.tasks = []

    async def run_socket(self,socket):
        self.set_socket(socket)
        # wait until the other side closes the socket properly
        with contextlib.suppress(asyncio.CancelledError):  # or the connection is dropped
            async for wsm in self.socket:
                await self.handle_incoming(wsm.data)
            await self.close() # on deliberate client-close: free resources
        self.unset_socket()

    def set_socket(self,socket):
        if self.socket:
            raise SocketOccupiedException()
        self.socket = socket
        self.got_socket.set()

    def unset_socket(self):
        self.socket = None
        self.got_socket.clear()

    def start_task(self,coro):
        task = asyncio.ensure_future(coro)
        self.tasks.append(task)
        return task

    async def stop_tasks(self):
        if self.tasks:
            for task in self.tasks:
                if not task.done():
                    task.set_exception(SessionClosedException())
            await asyncio.wait(self.tasks) # necessary for server close

    async def send(self,text):
        socket = await self.get_socket()
        socket.send_str(text)

    async def get_socket(self):
        await self.got_socket.wait()
        return self.socket

    async def handle_incoming(self,text):
        log.debug('{} < {} [IGNORED]'.format(self.session_id,text))

    async def close(self):
        if self.socket:
            await self.socket.close()
            self.unset_socket()
        await self.stop_tasks()

class FeedSession(BaseSession):
    def __init__(self,session_id):
        super().__init__(session_id)
        self.info = None
        self.sendq = FiniteQueue()
        self.recvq = FiniteQueue()
        self.start_task(self.process_sendq())
        self.start_task(self.run_protocol())
        self.start_task(self.listen_info())
        self.start_task(self.send_passphrase())
        self.subscriberlists = defaultdict(list) # message class -> [Future]
        self.open = True

    # cancel using SessionClosedException
    async def process_sendq(self):
        with contextlib.suppress(SessionClosedException):
            async for msg in self.sendq:
                while True:
                    with contextlib.suppress(asyncio.CancelledError): # connection drop
                        await self.send(msg)
                        break

    async def handle_incoming(self,text):
        # dispatch to recvq so we can react immediately on connection drop/close
        await self.recvq.put(m.Message.parse(text))

    async def schedule_send(self,msg):
        await self.sendq.put(str(msg))

    async def run_protocol(self):
        with contextlib.suppress(SessionClosedException):
            await self.schedule_banner()
            async for msg in self.recvq:
                subs = self.subscriberlists[msg.__class__]
                if subs:
                    for sub in subs:
                        sub.set_result(msg)
                else:
                    log.debug('No subscribers for {}'.format(msg.__class__))

    async def schedule_banner(self):
        for line in banner.splitlines():
            await self.schedule_send(m.Line(line))


    async def close(self):
        await super().close()
        self.open = False
        # try:
        #     await asyncio.wait_for(self.pprot,1)
        # except asyncio.TimeoutError:
        #     log.debug('{}: protocol force-cancelled after timeout'.format(self.session_id))

    async def subscribe_once(self,mclass):
        fut = asyncio.Future()
        self.subscriberlists[mclass].append(fut)
        res = await fut
        self.subscriberlists[mclass].remove(fut)
        return res

    async def listen_info(self):
        with contextlib.suppress(SessionClosedException):
            async for msg in Subscriber(self.subscriberlists[m.Info]):
                for k, v in msg.__dict__.items():
                    setattr(self.info, k, v)
                log.debug('{} > INFO({})'.format(self.session_id, self.info.__dict__))

    async def send_passphrase(self):
        with contextlib.suppress(SessionClosedException):
            msg = await self.subscribe_once(m.Info)
            text = 'Access this terminal with the following passphrase:'
            await self.schedule_send(m.Line(text))
            await self.schedule_send(m.Line(msg.passphrase))


    async def read_line_conv(self,socket):
        rls = BaseSession(self.session_id+'_R')

        async def copy_from_feedclient():
            with contextlib.suppress(SessionClosedException):
                await self.schedule_send(m.ReadLine())
                lr = await self.subscribe_once(m.LineRead)
                await rls.send(lr.text)
                await rls.close()

        copy_task = self.start_task(copy_from_feedclient())
        await rls.run_socket(socket)
        await rls.close() # on rls connection drop
        if not copy_task.done():
            copy_task.set_exception(SessionClosedException())
            #await copy_task

log = logging.getLogger(__name__)