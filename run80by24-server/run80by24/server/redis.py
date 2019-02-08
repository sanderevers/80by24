import aioredis
import json
from .conf import ServerConfig
from ..common import messages as m

class Redis:
    @staticmethod
    async def init(app):
        r = Redis()
        await r.start(app.loop)
        app['redis'] = r

    @staticmethod
    async def teardown(app):
        await Redis.of(app).stop()

    @staticmethod
    def of(app):
        return app['redis']

    async def start(self,loop):
        pool = await aioredis.create_pool(ServerConfig.redis_uri,loop=loop)
        self.r = aioredis.Redis(pool)

    async def stop(self):
        self.r.close()
        await self.r.wait_closed()

    async def scopes(self, token):
        scopestr = await self.r.get('token:' + token)
        if scopestr:
            return scopestr.split()
        else:
            return ()

    async def claimed(self, ttyId):
        return (await self.r.sismember('claimed',ttyId))

    async def publish(self, ttyId, msg):
        await self.r.publish(ServerConfig.psfw_channel_prefix+ttyId, str(msg))


