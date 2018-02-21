import yaml
import logging

class ServerConfig:
    port = 8080
    logfile = None  # 'server.log'
    debug = True
    debug_asyncio = False

    @staticmethod
    def read(filename):
        with open(filename) as f:
            yml = yaml.safe_load(f)
        for key,val in yml.items():
            if hasattr(ServerConfig,key):
                setattr(ServerConfig,key,val)
            else:
                logging.warning('Unknown configuration key "{}"'.format(key))
