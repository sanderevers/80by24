class State:
    def __init__(self):
        self.clients = {}

    @staticmethod
    def init(app):
        app['state'] = State()

    @staticmethod
    def of(app):
        return app['state']



