from SimpleHTTPServer import SimpleHTTPRequestHandler
import SocketServer
import sys
import httplib, urllib

#import http.server
#import socketserver

PORT = 8080
EXTHOST = "ext-endpoint-host.com"
EXTPATH = "/some/path"


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, request, client_address, server):
        self.responded = False
        SimpleHTTPRequestHandler.__init__(self, request, client_address, server)

    def respond(self, response):
        self.send_response(response.status)
        for p in response.getheaders():
            print("RES HD %s: %s" % (p[0], p[1]))
            self.send_header(p[0], p[1])
        self.end_headers()
        self.wfile.write(response.read())

    def do_POST(self):
        try:
            print("POST" + str(self.__dict__))
            #print(str(self.rfile))
            print("HEADERS:")
            print(str(self.headers))
            hList = {}
            for key in self.headers:
                hList[key] = self.headers[key]
            rSize = int(self.headers["Content-Length"])
            print("READING %s" % str(rSize))
            data = self.rfile.read(rSize)
            print("DATA LEN: %s" % str(len(data)))
            res = self.postExt(hList, data)

            print("REsponding back")
            self.respond(res)

        except:
            print("Unexpected error:" + str(sys.exc_info()[0]))
            self.send_response(500)
            raise

    def do_GET(self):
        try:
            print("GET" + str(self.__dict__))
            SimpleHTTPRequestHandler.do_GET(self)
        except:
            print("Unexpected error:" + str(sys.exc_info()[0]))
            raise

            
    def postExt(self, headers, data):
        try:
            print("POSTING EXT")
            conn = httplib.HTTPSConnection(EXTHOST)
            conn.request("POST", EXTPATH, data, headers)
            response = conn.getresponse()
            print("%s : %s" % (response.status, response.reason))
            print(data)
            conn.close()
            return response
        except:
            print("Error when posting" + str(sys.exc_info()[0]))
            raise

httpd = SocketServer.TCPServer(("", PORT), Handler)

if(len(sys.argv) > 1):
    PORT = int(sys.argv[1])

print("serving at port %s" % str(PORT))
httpd.serve_forever()
