import aioredis

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
        pool = await aioredis.create_pool('redis://localhost',encoding='utf-8',loop=loop)
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


