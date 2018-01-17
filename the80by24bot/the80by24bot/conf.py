import yaml
import logging

class BotConfig:
    port = 8081
    logfile = None  # 'bot.log'
    debug = True
    apikey = 'put_real_apikey_here'
    bot_host = 'https://80by24.net'
    tty_endpoint = 'https://80by24.net/tty/{ttyId}'
    register_endpoint = 'https://api.telegram.org/bot{apikey}/setWebhook'
    msg_endpoint = 'https://api.telegram.org/bot{apikey}/sendMessage'

    @staticmethod
    def read(filename):
        with open(filename) as f:
            yml = yaml.safe_load(f)
        for key,val in yml.items():
            if hasattr(BotConfig,key):
                setattr(BotConfig,key,val)
            else:
                logging.warning('Unknown configuration key "{}"'.format(key))
