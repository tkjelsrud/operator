#!/usr/bin/env python
# 

import http.server
#import socketserver
import sys

from server import ExServer

PORT = 8000

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, request, client_address, server):
        self.responded = False
        http.server.SimpleHTTPRequestHandler.__init__(self, request, client_address, server)
        
    def respond(self, resList):
        data = resList[1]
        response = resList[0]
        
    def do_POST(self):
        print(self.headers)
        
    def do_GET(self):
        try:
            print("-> GET" + str(self.__dict__))
            http.server.SimpleHTTPRequestHandler.do_GET(self)
        except KeyboardInterrupt:
            # Stop the server
            self.server.stop = True
            None
        except:
            print("Unexpected error:" + str(sys.exc_info()[0]))
            raise
            
            
httpd = ExServer(("", PORT), Handler)
httpd.allow_reuse_address = True # Prevent 'cannot bind to address' errors on restart
#httpd.server_bind()     # Manually bind, to support allow_reuse_address
httpd.server_activate() # (see above comment)
    
print("serving at port", PORT)
try:
    httpd.serve_forever()
except KeyboardInterrupt:
    # Stop the server
    sys.exit(0)