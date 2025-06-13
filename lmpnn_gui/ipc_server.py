from socketserver import BaseRequestHandler, TCPServer

class LmpnnRequestHandler(BaseRequestHandler):

    def __init__(self, *args, **kwargs):
        super(BaseRequestHandler).__init__(*args, **kwargs)
        print("le init")

    def handle(self, *args, **kwargs):
        print("Ihandle")

def init_server():
    return TCPServer(('127.0.0.1', 6666), LmpnnRequestHandler)
