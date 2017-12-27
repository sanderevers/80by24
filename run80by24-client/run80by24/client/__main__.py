import curses

import websockets
import asyncio
import logging
import sys
import os.path
from ..common import messages as m
from ..common import id_generator
from .conf import ClientConfig as config
from .conf import read as read_config

class App:
    def __init__(self,scr):
        self.scr = scr
        if config.passphrase:
            words = config.passphrase.split()
        else:
            words = id_generator.randomwords()

        self.ttyId = id_generator.id_hash(words)
        self.url = feed_url(self.ttyId)

        self.info = m.Info()
        self.info.passphrase = ' '.join(words)
        self.info.termname = str(curses.termname(), 'utf-8')
        self.info.baudrate = curses.baudrate()
        self.info.lines, self.info.cols = scr.getmaxyx()

    async def start(self):
        retries = 5
        sleepytime = 0
        while True:
            try:
                await asyncio.sleep(sleepytime)
                if retries == 0:
                    break
                self.writeline('Connecting to {}... '.format(self.url), False)
                retries -= 1
                async with websockets.connect(self.url) as conn:
                    retries = 5
                    self.writeline('done.')
                    await conn.send(str(self.info))
                    await self.handle_messages(conn)
            except OSError:
                self.writeline('failed. Retrying in 5 seconds.')
                sleepytime = 5
            except asyncio.futures.CancelledError:
                self.writeline('[ktnxbye]')
                sleepytime = 1
                retries = 0
            except websockets.exceptions.ConnectionClosed:
                self.writeline('[Disconnected by server.]')
                sleepytime = 2

    async def handle_messages(self,conn):
        while True:
            raw = await conn.recv()
            log.debug('< '+raw)
            msg = m.Message.parse(raw)
            if isinstance(msg,m.Line):
                self.writeline(msg.text, halign=msg.halign)
            if isinstance(msg,m.Page):
                self.writepage(msg.text, halign=msg.halign, valign=msg.valign)
            if isinstance(msg,m.Cls):
                self.clear()
            if isinstance(msg,m.ReadLine):
                curses.flushinp()
                curses.echo()
                text = await self.getstr()
                curses.noecho()
                await conn.send(str(m.LineRead(text)))
            if isinstance(msg,m.ReadKey):
                curses.flushinp()
                if msg.echo:
                    curses.echo()
                key = await self.getkey()
                curses.noecho()
                await conn.send(str(m.KeyRead(key)))

    async def getstr(self):
        bytes = await asyncio.get_event_loop().run_in_executor(None,self.scr.getstr)
        return str(bytes, 'utf-8')

    async def getkey(self):
        key = await asyncio.get_event_loop().run_in_executor(None,self.scr.getkey)
        return key

    def writepage(self,text,halign='left',valign='top'):
        self.scr.clear()
        lines = text.split('\n')
        if valign=='middle':
            y = max(0,(self.info.lines - len(lines))//2)
            self.scr.move(y,0)
        elif valign=='bottom':
            y = max(0,self.info.lines - len(lines))
            self.scr.move(y,0)
        for line in lines:
            self.writeline(line,halign=halign)
        self.scr.refresh()

    def writeline(self,text,newline=True,halign='left'):
        y, _ = self.scr.getyx()
        twidth = min(self.info.cols, len(text))
        text = text+('\n' if newline and len(text)!=self.info.cols and halign!='right' else '')
        if halign=='left':
            self.scr.addstr(text)
        elif halign=='center':
            x = (self.info.cols - twidth)//2
            self.scr.addstr(y,x,text)
        elif halign=='right':
            x = self.info.cols - twidth
            self.scr.addstr(y,x,text)
        self.scr.refresh()

    # def writeline(scr,text):
    #     y, x = scr.getyx()
    #     if y == 23:
    #         scr.scroll(1)
    #     else:
    #         y = y + 1
    #     scr.addstr(y, 0, text)
    #     scr.refresh()

    def clear(self):
        self.scr.clear()
        self.scr.refresh()

def feed_url(ttyId):
    return '{host}/feed/{ttyId}'.format(host=config.host, ttyId=ttyId).replace('http','ws',1)

def run_in_curses(scr):
    scr.clear()
    scr.idlok(1)
    scr.scrollok(1)
    curses.nonl()
    curses.noecho()
    app = App(scr)
    maintask = asyncio.ensure_future(app.start())
    try:
        asyncio.get_event_loop().run_until_complete(maintask)
    except KeyboardInterrupt:
        maintask.cancel()
        asyncio.get_event_loop().run_until_complete(maintask)

def main():
    default_config_file = os.path.join(os.path.expanduser('~'), '.80by24.conf')
    if len(sys.argv)>1:
        read_config(sys.argv[1])
    elif os.path.exists(default_config_file):
        read_config(default_config_file)
    curses.wrapper(run_in_curses)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__package__)
if __name__=='__main__':
    main()
