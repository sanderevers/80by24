class AbortRequestException(Exception):
    def __init__(self,status=403, text=None):
        self.status = status
        self.text = text