from ..common import messages as m
import asyncio
import logging
import contextlib
from .banner import banner
from .aqueue import FiniteQueue

class ClientInfo():
    def __init__(self,ttyId):
        self.ttyId = ttyId

class Session:
    def __init__(self):
        self.socket = None
        self.got_socket = asyncio.Event()
        self.sendq = FiniteQueue()
        self.recvq = FiniteQueue()
        self.psq = asyncio.ensure_future(self.process_sendq())
   #     self.prq = asyncio.ensure_future(self.proccess_recvq())
        self.pprot = asyncio.ensure_future(self.run_protocol())

    # how to differentiate between network loss and self cancel?
    # self-cancel closes the socket first, then FiniteQueue.End
    # async def process_sendq(self):
    #     async for msg in self.sendq:
    #         log.debug('{} < {}'.format(self.path, msg))
    #         while True:
    #             try:
    #                 await self.socket.send_str(msg)
    #                 break
    #             except asyncio.CancelledError:
    #                 if self.closing:
    #                     break
    #                 else:
    #                     wait_for_socket_to_return
    #         if self.closing:
    #             break

    # cancel using SessionCloseException
    async def process_sendq(self):
        async for msg in self.sendq:
            while True:
                socket = await self.get_socket()
                with contextlib.suppress(asyncio.CancelledError): # connection drop
                    await socket.send_str(msg)
                    break

    async def schedule_send(self,text):
        await self.sendq.put(text)

    async def recv(self):
        return await self.recvq.get()

    # async def process_recvq(self):
    #     async for msg in self.recvq:
    #         handled = await self.handle_message(msg)

    # async def process_sendq(self):
    #     async with self.reget_socket() as socket:
    #         async for msg in self.sendq:
    #             try:
    #                 await socket.send_str(msg)
    #             except asyncio.CancelledError:
    #                 raise CancelledWhileSendingException(msg)

    def set_socket(self,socket):
        if self.socket:
            raise SocketOccupiedException
        self.socket = socket
        self.got_socket.set()

    def unset_socket(self):
        self.socket = None
        self.got_socket.clear()

    async def get_socket(self,socket):
        await self.got_socket.wait()
        return self.socket

    async def run_protocol(self):
        self.schedule_send_banner()
        async for msg in self.recvq:
            pass

    async def run_socket(self,socket):
        self.set_socket(socket)
        # wait until the other side closes the socket properly
        with contextlib.suppress(asyncio.CancelledError):  # or the connection is dropped
            async for msg in self.socket:
                # dispatch to recvq so we can react immediately on connection drop/close
                await self.recvq.put(msg)
            await self.close() # on deliberate client-close: free resources
        self.unset_socket()

    async def close(self):
        if self.socket:
            await self.socket.close()
            self.unset_socket()
        self.psq.set_exception(SessionClosedException())
        self.recvq.close()
        try:
            await asyncio.wait_for(self.pprot,1)
        except asyncio.TimeoutError:
            log.debug('protocol force-cancelled after timeout')



class BaseClient:
    def __init__(self, path):
        self.sendq = FiniteQueue()
        self.path = path

    async def run(self,socket):
        self.socket = socket
        log.info('{} connected'.format(self.path))
        self.psq = asyncio.ensure_future(self.process_sendq())

        await self.first_messages()

        # wait until the other side closes the socket properly
        with contextlib.suppress(asyncio.CancelledError):  # or the connection is dropped
            async for msg in self.socket:
                handled = await self.handle_message(msg)
                if not handled:
                    log.debug('{} > [IGNORED] {}'.format(self.path, msg.data))

        # put this in a with:__exit__ instead of suppressing CancelledError?
        self.psq.cancel()

    async def send_text(self,text):
        await self.sendq.put(text)

    async def first_messages(self):
        pass

    async def handle_message(self,msg):
        pass

    async def close(self):
        log.info('{} < [CLOSE]'.format(self.path))
        await self.socket.close()

    async def process_sendq(self):
        async for msg in self.sendq:
            log.debug('{} < {}'.format(self.path, msg))
            await self.socket.send_str(msg)
        await self.socket.close()


class FeedClient(BaseClient):
    def __init__(self,path,ttyId):
        super().__init__(path)
        self.info = ClientInfo(ttyId)
        self.rlc = None
        self.devc = None

    async def first_messages(self):
        await self.send_banner()

    async def handle_message(self, raw):
        try:
            msg = m.Message.parse(raw.data)
        except:
            msg = None
        if isinstance(msg, m.Info):
            for k, v in msg.__dict__.items():
                setattr(self.info, k, v)
            log.debug('{} > INFO({})'.format(self.path, self.info.__dict__))
            await self.send_passphrase()
        elif isinstance(msg,m.LineRead) and self.rlc:
            await self.rlc.send(msg.text)
        elif isinstance(msg, m.KeyRead) and self.rlc:
            await self.rlc.send(msg.key)
        else:
            return False # message ignored
        return True #message handled

    async def send(self,cmd):
        assert isinstance(cmd, m.Message)
        await self.send_text(str(cmd))

    async def send_banner(self):
        for line in banner.splitlines():
            await self.send(m.Line(line))

    async def send_passphrase(self):
        text = 'Access this terminal with the following passphrase:'
        await self.send(m.Line(text))
        await self.send(m.Line(self.info.passphrase))

    async def read_line(self,path,socket):
        self.rlc = ReadLineClient(path,self)
        await self.send(m.ReadLine())
        await self.rlc.run(socket)
        await self.rlc.close()
        self.rlc = None

    async def read_key(self,path,socket,echo):
        self.rlc = ReadLineClient(path,self)
        await self.send(m.ReadKey(echo=echo))
        await self.rlc.run(socket)
        await self.rlc.close()
        self.rlc = None

    async def run_dev_client(self,path,socket):
        self.devc = DevClient(path,self)
        await self.devc.run(socket)
        await self.devc.close()
        self.devc = None

    async def close(self):
        await super().close()
        if self.rlc:
            await self.rlc.close()
        if self.devc:
            await self.devc.close()

class DevClient(BaseClient):
    def __init__(self, path, yinClient):
        super().__init__(path)
        self.yinClient = yinClient
        self.info = ClientInfo(yinClient.info.ttyId)

    async def handle_message(self,msg):
        log.debug('{} > {}'.format(self.info.path, msg.data))
        await self.yinClient.send_text(msg.data)
        return True

class ReadLineClient(BaseClient):
    def __init__(self, path, yinClient):
        super().__init__(path)
        self.info = ClientInfo(yinClient.info.ttyId)

    async def send(self, text):
        await self.send_text(text)
        await self.send_text(FiniteQueue.End)


log = logging.getLogger(__name__)
