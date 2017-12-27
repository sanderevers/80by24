import json as _json

class Message:

    @staticmethod
    def parse(js):
        d = _json.loads(js)
        (cls_name,attrs), = d.items()
        cls = _commands[cls_name]
        inst = cls.__new__(cls)
        inst.setattrs(attrs)
        return inst

    def setattrs(self,attrs):
        self.__dict__ = attrs

    def __str__(self):
        cls_name = self.__class__.__name__
        d ={cls_name : self.__dict__}
        return _json.dumps(d)

# Server -> Client

class Line(Message):
    def __init__(self,text,halign='left'):
        self.text = text
        self.halign = halign

class Page(Message):
    def __init__(self,text,halign='left',valign='top'):
        self.text = text
        self.halign = halign
        self.valign = valign

class Cls(Message):
    pass

class ReadLine(Message):
    pass

class ReadKey(Message):
    def __init__(self,echo=False):
        self.echo = echo

# Client -> Server

class Info(Message):
    pass

class LineRead(Message):
    def __init__(self,text):
        self.text = text

class KeyRead(Message):
    def __init__(self,key):
        self.key = key


_commands = {k:v for k,v in locals().items() if not k.startswith('_')}
