from .conf import ServerConfig
import asyncio
import logging
import warnings
import aiohttp.web
from . import app
import sys

def main():
    if len(sys.argv)>1:
        ServerConfig.read(sys.argv[1])

    if ServerConfig.debug_asyncio:
        asyncio.get_event_loop().set_debug(True)
        warnings.simplefilter("always", ResourceWarning)
    logging.basicConfig(level=logging.DEBUG if ServerConfig.debug else logging.INFO, filename=ServerConfig.logfile)
    aiohttp.web.run_app(app.create(),port=ServerConfig.port)

if __name__=='__main__':
    main()