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
            if type.lower() == m['type'].lower() and key.lower() == m['key'].lower():
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

    def respond(self, resList):
        data = resList[1]
        response = resList[0]
        print("<- POST (" + str(response.status) + ") h:" + str(len(response.getheaders())) + " d:" + str(len(data)))
        self.send_response(response.status)
        for p in response.getheaders():
            print(str(p[0]) + ": " + str(p[1]))
            val = CONFIG.runMatchers('response.header', p[0], p[1])
            if p[0].lower() == 'transfer-encoding':
                self.send_header("Content-Length", str(len(data)))
            else:
                self.send_header(p[0], val)
        self.end_headers()
        self.toFile('proxy.res', data)
        self.wfile.write(data.decode('utf-8'))   #'ascii'))

    def do_POST(self):
        try:
            print("-> POST " + self.requestline + " h:" + str(len(self.headers)) + " d:")
            hList = {}
            for key in self.headers:
                print(key + ": " + self.headers[key])
                val = CONFIG.runMatchers('request.header', key, self.headers[key])
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

            self.toFile('proxy.req', data)
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


    def postExt(self, headers, data):
        try:
            conn = httplib.HTTPSConnection(CONFIG.get('exthost'))
            if 'transfer-encoding' in headers:
                headers.pop("transfer-encoding", None)
            conn.request("POST", CONFIG.get('extpath'), data, headers)
            response = conn.getresponse()
            data = response.read()
            print("POST <- %s : %s" % (response.status, response.reason))
            conn.close()
            return (response, data)
        except:
            print("Error when posting" + str(sys.exc_info()[0]))
            raise

    def toFile(self, fname, data):
        f = open(fname, 'r+')
        text = f.read()
        f.seek(0)
        f.write(data)
        f.truncate()
        f.close()

httpd = SocketServer.TCPServer(("", int(CONFIG.get('port'))), Handler)

if(len(sys.argv) > 1):
    PORT = int(sys.argv[1])

print("serving at port %s" % CONFIG.get('port'))
httpd.serve_forever()
