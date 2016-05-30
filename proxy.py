#!/usr/bin/env python
# 
# https://github.com/tkjelsrud/proxy

# NOTE, need to support http.server in Python>3
from SimpleHTTPServer import SimpleHTTPRequestHandler

import SocketServer
import sys, random, re
import httplib, urllib

from time import sleep

from config import Config

CFG = "proxy-config.xml"

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, request, client_address, server):
        self.responded = False
        SimpleHTTPRequestHandler.__init__(self, request, client_address, server)

    def respond(self, resList):
        data = resList[1]
        response = resList[0]
        print("<- POST (" + str(response.status) + ") h:" + str(len(response.getheaders())) + " d:" + str(len(data)))
        self.send_response(response.status)
        for p in response.getheaders():
            val = CONFIG.runEvents('response.header', None,  p[0], p[1])
            if p[0].lower() == 'transfer-encoding':
                self.send_header("Content-Length", str(len(data)))
            else:
                self.send_header(p[0], val)
            #print(str(p))
        self.end_headers()
        self.toFile('proxy_' + str(response.status) + '.res', data)
        self.wfile.write(data.decode('utf-8'))   #'ascii'))

    def do_POST(self):
        try:
            act = ""
            if "soapaction" in self.headers:
                act = self.headers["soapaction"]
            print("-> POST " + self.requestline + " h:" + str(len(self.headers)))
            CONFIG.runEvents('request', act)
            hList = {}
            for key in self.headers:
                val = CONFIG.runEvents('request.header', act, key, self.headers[key])
                hList[key] = val

            rSize = 0
            chBt = 4
            data = ""
            if "Content-Length" in self.headers:
                rSize = int(self.headers["Content-Length"])
                data = self.rfile.read(rSize)
            else:
                data = self.readChunked(self.rfile)
                hList["Content-Length"] = str(len(data))

            data = CONFIG.runEvents('data', act, 'data', data)

            self.toFile('proxy_200.req', data)

            # Pick host/path
            reqpath = self.requestline.split(" ")[1]
            
            endpoint = CONFIG.getEndpoint(reqpath)
            if endpoint:
                res = self.postExt(endpoint, hList, data)

                self.respond(res)
            else:
                print("ENDPOINT not configured for: " + self.requestline)
        except:
            print("Unexpected error:" + str(sys.exc_info()[0]))
            self.send_response(500)
            raise

    def do_GET(self):
        try:
            print("-> GET" + str(self.__dict__))
            SimpleHTTPRequestHandler.do_GET(self)
        except:
            print("Unexpected error:" + str(sys.exc_info()[0]))
            raise

    def readChunked(self, stream):
        data = ""
        rSize = stream.readline()
        rSize = int(rSize, 16) + 2
        while rSize > 0:
            ndata = stream.read(rSize)
            data += ndata
            if rSize < 4089:
                rSize = 0 # Probable end
            else:
                try:
                    ch = stream.readline()
                    rSize = int(ch, 16) + 2
                except:
                    rSize = 0
        return data

    def getExt(self, endpoint, headers, url):
        None

    def postExt(self, endpoint, headers, data):
        try:
            #TODO add support for non-secure (http)
            #print(endpoint)
            conn = 0
            host = endpoint[0]
            port = None
            if ':' in host:
                host = endpoint[0].split(':')[0]
                port = int(endpoint[0].split(':')[1])
            if endpoint[2] == False:
                # Non secure
                if not port:
                    conn = httplib.HTTPConnection(host)
                else:
                    conn = httplib.HTTPConnection(host, port)
            else:
                conn = httplib.HTTPSConnection(host)
            if 'transfer-encoding' in headers:
                headers.pop("transfer-encoding", None)
            conn.request("POST", endpoint[1], data, headers)
            CONFIG.runEvents("request.connection")
            response = conn.getresponse()
            data = response.read()
            if response.status is not '200':
                print("POST <- %s : %s" % (response.status, response.reason))
            conn.close()
            return (response, data)
        except:
            print("Error when posting" + str(sys.exc_info()[0]))
            raise

    def toFile(self, fname, data):
        f = open(fname, 'rw+')
        text = f.read()
        f.seek(0)
        f.write(data)
        f.truncate()
        f.close()

CONFIG = 0

if __name__ == "__main__":
    CONFIG = Config()
    CONFIG.readCfg(CFG)

    sys.tracebacklimit=1

    #SocketServer.ThreadingTCPServer.allow_reuse_address = True
    #httpd = SocketServer.TCPServer(("", int(CONFIG.get('port'))), Handler)
    
    # NOTE, need to support http.server in Python>3
    
    httpd = SocketServer.ThreadingTCPServer((CONFIG.get('host', 'localhost'), int(CONFIG.get('port'))), Handler, False) # Do not automatically bind
    httpd.allow_reuse_address = True # Prevent 'cannot bind to address' errors on restart
    httpd.server_bind()     # Manually bind, to support allow_reuse_address
    httpd.server_activate() # (see above comment)
    
    #SO_REUSEADDR
    if(len(sys.argv) > 1):
        PORT = int(sys.argv[1])

    print("PROXY RUNNING: %s" % CONFIG.get('port'))
    httpd.serve_forever()
