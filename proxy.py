from SimpleHTTPServer import SimpleHTTPRequestHandler
import SocketServer
import sys
import httplib, urllib
from xml.dom import minidom

CFG = "proxy-config.xml"

class Config:
    def __init__(self):
        self.data = {'matchers': []}
        xd = minidom.parse(CFG)
        vList = xd.getElementsByTagName('var')
        for v in vList:
            self.data[v.attributes['key'].value] = v.attributes['value'].value
        nList = xd.getElementsByTagName('match')
        for n in nList:
            ma = {'type': n.attributes['type'].value,
                  'key': n.attributes['key'].value,
                  'match': n.attributes['match'].value}
            if n.hasAttribute('replace'):
                ma['replace'] = n.attributes['replace'].value
            self.data['matchers'].append(ma)
        print(str(self.data))

    def get(self, key):
        if key in self.data:
            return self.data[key]
        return None

    def runMatchers(self, type, key, value):
        for m in self.data['matchers']:
            if type == m['type'] and key == m['key']:
                if 'replace' in m:
                    print('Want to replace something in ' + key)
                else:
                    print(key + ': ' + value)
        return value


CONFIG = Config()

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, request, client_address, server):
        self.responded = False
        SimpleHTTPRequestHandler.__init__(self, request, client_address, server)

    def respond(self, response):
        data = response.read()
        print(str(type(data)))
        print("<- POST (" + str(response.status) + ") h:" + str(len(response.getheaders())) + " d:" + str(len(data)))
        self.send_response(response.status)
        for p in response.getheaders():
            #print(str(p[0]) + " " + str(p[1]))
            val = CONFIG.runMatchers('response.header', p[0], p[1])
            self.send_header(p[0], val)
        self.end_headers()

        print(str(data))
        #print("Will post data" + str(type(data)) + " LEN:" + str(len(data)))

        self.wfile.write(bytes(data.decode('UTF-8')))

    def do_POST(self):
        try:
            print("-> POST " + self.requestline + " h:" + str(len(self.headers)) + " d:")

            #print(str(self.headers))
            hList = {}
            for key in self.headers:
                val = CONFIG.runMatchers('request.header', key, self.headers[key])
                hList[key] = val
            rSize = int(self.headers["Content-Length"])
            data = self.rfile.read(rSize)
            res = self.postExt(hList, data)

            self.respond(res)

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


    def postExt(self, headers, data):
        try:
            conn = httplib.HTTPSConnection(CONFIG.get('exthost'))
            conn.request("POST", CONFIG.get('extpath'), data, headers)
            response = conn.getresponse()
            print("POST <- %s : %s" % (response.status, response.reason))
            conn.close()
            return response
        except:
            print("Error when posting" + str(sys.exc_info()[0]))
            raise

httpd = SocketServer.TCPServer(("", int(CONFIG.get('port'))), Handler)

if(len(sys.argv) > 1):
    PORT = int(sys.argv[1])

print("serving at port %s" % CONFIG.get('port'))
httpd.serve_forever()
