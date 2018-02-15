import asyncio
import logging

class FiniteQueue(asyncio.Queue):
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

class Subscriber():
    def __init__(self,sublist):
        self.waiter = None
        self.sublist = sublist
        self.replace_waiter()

    def replace_waiter(self):
        if self.waiter:
            self.sublist.remove(self.waiter)
        self.waiter = asyncio.Future()
        self.sublist.append(self.waiter)

    def __aiter__(self):
        return self

    async def __anext__(self):
        res = await self.waiter
        self.replace_waiter()
        return res

log = logging.getLogger(__name__)