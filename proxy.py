from SimpleHTTPServer import SimpleHTTPRequestHandler
import SocketServer
import sys
import httplib, urllib
from xml.dom import minidom
from time import sleep

CFG = "proxy-config.xml"

class Config:
    def __init__(self):
        self.data = {'exec': [], 'routing': []}
        xd = minidom.parse(CFG)
        vList = xd.getElementsByTagName('var')
        for v in vList:
            self.data[v.attributes['key'].value] = v.attributes['value'].value
        eList = xd.getElementsByTagName('exec')
        for n in eList[0].childNodes:
            if n.nodeType == n.ELEMENT_NODE:
                ma = {'type': n.nodeName, 'event': n.attributes['event'].value}
                if ma['type'] == "notify" or ma['type'] == "replace":
                    ma['key'] = n.attributes['key'].value
                    ma['match'] = n.attributes['match'].value
                if ma['type'] == "replace":
                    ma['replace'] = n.attributes['replace'].value
                if ma['type'] == "delay":
                    ma['time'] = n.attributes['time'].value
                self.data['exec'].append(ma)
        eList = xd.getElementsByTagName('routing')
        for e in eList:
            ep = {'match': e.attributes['match'].value,
                  'host': e.attributes['host'].value,
                  'path': e.attributes['path'].value}
            self.data['routing'].append(ep)
        print(str(self.data))

    def get(self, key):
        if key in self.data:
            return self.data[key]
        return None

    def runEvents(self, event, key = None, value = None):
        for m in self.data['exec']:
            if event.lower() == m['event'].lower():
                None
                if not key or (key and key.lower() == m['key'].lower()):
                    value = self.run(m, event, key, value)

        return value

    def run(self, ex, event, key=None, value=None):
        if ex['type'].lower() == "delay":
            print("\t[" + event + "] DELAY " + ex['time'] + "s")
            sleep(float(ex['time']))
        if ex['type'].lower() == "notify":
            print("\t[" + event + "] " + str(key) + ": " + str(value))
        if ex['type'].lower() == "replace":
            if ex['match'] in value:
                print("\t[" + event + "] REPLACE " + ex['match'] + " -> " + ex['replace'])
                value = value.replace(ex['match'], ex['replace'])
        return value

    def getEndpoint(self, context):
        for r in self.data['routing']:
            if r['match'] in context:
                return [r['host'], r['path']]
        return None

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
            val = CONFIG.runEvents('response.header', p[0], p[1])
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
            CONFIG.runEvents('request')
            hList = {}
            for key in self.headers:
                val = CONFIG.runEvents('request.header', key, self.headers[key])
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

            data = CONFIG.runEvents('data', 'data', data)

            self.toFile('proxy.req', data)

            # Pick host/path
            endpoint = CONFIG.getEndpoint(self.requestline)
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


    def postExt(self, endpoint, headers, data):
        try:
            conn = httplib.HTTPSConnection(endpoint[0])
            if 'transfer-encoding' in headers:
                headers.pop("transfer-encoding", None)
            conn.request("POST", endpoint[1], data, headers)
            CONFIG.runEvents("request.connection")
            response = conn.getresponse()
            data = response.read()
            #print("POST <- %s : %s" % (response.status, response.reason))
            conn.close()
            return (response, data)
        except:
            print("Error when posting" + str(sys.exc_info()[0]))
            raise

    def toFile(self, fname, data):
        #print("WF: " + fname)
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
