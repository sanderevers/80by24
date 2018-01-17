from .conf import BotConfig
import asyncio
import logging
import warnings
import aiohttp.web
from . import app
import sys

def main():
    if len(sys.argv)>1:
        BotConfig.read(sys.argv[1])

    if BotConfig.debug:
        asyncio.get_event_loop().set_debug(True)
        warnings.simplefilter("always", ResourceWarning)
    logging.basicConfig(level=logging.DEBUG if BotConfig.debug else logging.INFO, filename=BotConfig.logfile)
    aiohttp.web.run_app(app.create(),port=BotConfig.port)

if __name__=='__main__':
    main()