#!/usr/bin/env python
# 

import http.server
import socketserver
import sys

class ExServer(http.server.HTTPServer):
    def serve_forever (self):
        self.stop = False
        while not self.stop:
            self.handle_request()