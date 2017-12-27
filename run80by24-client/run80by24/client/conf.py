import yaml
import logging

class ClientConfig:
    host = 'https://80by24.net'
    passphrase = None

def read(filename):
    with open(filename) as f:
        yml = yaml.safe_load(f)
    for key,val in yml.items():
        if hasattr(ClientConfig,key):
            setattr(ClientConfig,key,val)
        else:
            logging.warning('Unknown configuration key "{}"'.format(key))
