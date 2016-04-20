#!/usr/bin/python
# thomas.kjelsrud@vegvesen.no
# 
# versjonering
#
# unit tester

from SimpleHTTPServer import SimpleHTTPRequestHandler
import SocketServer
import sys, random, re
import httplib, urllib
from xml.dom import minidom
from time import sleep

CFG = "proxy-config.xml"

class Config:
    def __init__(self):
        self.data = {'exec': [], 'routing': []}

    def readCfg(self, cfgPath):
        xd = minidom.parse(cfgPath)
        vList = xd.getElementsByTagName('var')
        for v in vList:
            self.data[v.attributes['key'].value] = v.attributes['value'].value
        eList = xd.getElementsByTagName('exec')
        for n in eList[0].childNodes:
            if n.nodeType == n.ELEMENT_NODE:
                ma = {'type': n.nodeName, 'event': n.attributes['event'].value}
                if ma['type'] == "replace":
                    ma['replace'] = n.attributes['replace'].value
                if ma['type'] == "delay":
                    ma['time'] = n.attributes['time'].value
                if n.hasAttribute("key"):
                    ma['key'] = n.attributes['key'].value
                if n.hasAttribute("match"):
                    ma['match'] = n.attributes['match'].value
                if n.hasAttribute("chance"):
                    ma['chance'] = float(n.attributes['chance'].value)
                self.data['exec'].append(ma)
        if len(self.data['exec']) > 0:
            print("ADD EVENTS: " + str(len(self.data['exec'])))
        eList = xd.getElementsByTagName('routing')
        for e in eList:
            ep = {'match': e.attributes['match'].value,
                  'host': e.attributes['host'].value,
                  'path': e.attributes['path'].value,
                  'secure': True}
            if e.hasAttribute('secure'):
                if e.attributes['secure'].value.lower () == "false":
                    ep['secure'] = False
            print("ADD ROUTE: " + ep['match'])
            self.data['routing'].append(ep)
        #print(str(self.data))

    def get(self, key):
        if key in self.data:
            return self.data[key]
        return None

    def runEvents(self, event, key = None, value = None):
        for m in self.data['exec']:
            if event.lower() == m['event'].lower():
                #print(str(key))
                if not key or not 'key' in m or (key and key.lower() == m['key'].lower()):
                    value = self.run(m, event, key, value)

        return value

    def run(self, ex, event, key=None, value=None):
        if 'chance' in ex:
            if random.random() > ex['chance']:
                return value

        if 'match' in ex:
            if ex['match'] not in value:
                return value
        if ex['type'].lower() == "fail":
            print("\t[" + event + "] Failing " + str(key) + ": " + str(value)) 
            raise Exception("Fail!1")
        if ex['type'].lower() == "delay":
            print("\t[" + event + "] DELAY " + ex['time'] + "s " +  + str(key) + ": " + str(value))
            sleep(float(ex['time']))
        if ex['type'].lower() == "notify":
            print("\t[" + event + "] " + str(key) + ": " + str(value))
        if ex['type'].lower() == "replace":
            print("\t[" + event + "] REPLACE " + ex['match'] + " -> " + ex['replace'])
            value = value.replace(ex['match'], ex['replace'])
        return value

    def getEndpoint(self, context):
        context = context.split(' ')[1] # Skip post and http version
        #context = context.replace('POST ' , '')
        #context = context.replace(' HTTP/1.1', '') # TODO: Stop failing...
        #context = context.split('?')
        #print(":::" + context)
        for r in self.data['routing']:
            p = re.compile(r['match'])
            m = p.match(context)
            #print(m.group())
            if m:
                path = r['path']
                for i in range(1, 9):
                    if '$' + str(i) in path:
                         #print("MATCH" + str(i) + " : " + m.group(i))
                         path = path.replace('$' + str(i), m.group(i))
                         #print("NEWP:" + path)
                #if len(context) > 1:
                #    path = path + '?' + context[1]
                return [r['host'], path, r['secure']]
        return None


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
            #print(str(p))
        self.end_headers()
        self.toFile('proxy_' + str(response.status) + '.res', data)
        self.wfile.write(data.decode('utf-8'))   #'ascii'))

    def do_POST(self):
        try:
            print("-> POST " + self.requestline + " h:" + str(len(self.headers)))
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

            self.toFile('proxy_200.req', data)

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
        #print("WF: " + fname)
        f = open(fname, 'r+')
        text = f.read()
        f.seek(0)
        f.write(data)
        f.truncate()
        f.close()

CONFIG = 0

if __name__ == "__main__":
    CONFIG = Config()
    CONFIG.readCfg(CFG)

    sys.tracebacklimit=0
    
    httpd = SocketServer.TCPServer(("", int(CONFIG.get('port'))), Handler)

    if(len(sys.argv) > 1):
        PORT = int(sys.argv[1])

    print("PROXY RUNNING: %s" % CONFIG.get('port'))
    httpd.serve_forever()

