#!/usr/bin/env python

from xml.dom import minidom
import sys, re

class Config:
    def __init__(self):
        self.data = {'exec': [], 'routing': []}

    def readCfg(self, cfgPath):
        xd = minidom.parse(cfgPath)
        
        vList = xd.getElementsByTagName('var')
        for v in vList:
            self.data[v.attributes['key'].value] = v.attributes['value'].value
        eList = xd.getElementsByTagName('exec')
        if eList and len(eList) > 0:
            for n in eList[0].childNodes:
                if n.nodeType == n.ELEMENT_NODE:
                    ma = {'type': n.nodeName, 'event': n.attributes['event'].value}
                    if ma['type'] == "replace": ma['replace'] = n.attributes['replace'].value
                    if ma['type'] == "delay": ma['time'] = n.attributes['time'].value
                    if n.hasAttribute("key"): ma['key'] = n.attributes['key'].value
                    if n.hasAttribute("match"): ma['match'] = n.attributes['match'].value
                    if n.hasAttribute("chance"): ma['chance'] = float(n.attributes['chance'].value)
                    if n.hasAttribute("action"): ma['act'] = n.attributes['action'].value
                    self.data['exec'].append(ma)
            #if len(self.data['exec']) > 0:
            #    print("ADD EVENTS: " + str(len(self.data['exec'])))
        
        eList = xd.getElementsByTagName('routing')
        for e in eList:
            ep = {'match': e.attributes['match'].value,
                  'host': e.attributes['host'].value,
                  'path': e.attributes['path'].value,
                  'secure': True}
            if e.hasAttribute('secure'):
                if e.attributes['secure'].value.lower () == "false":
                    ep['secure'] = False
            #print("ADD ROUTE: " + ep['match'])
            self.data['routing'].append(ep)

    def get(self, key, default=None):
        if key in self.data:
            return self.data[key]
        if default:
            return default
        return None

    def runEvents(self, event, act = None, key = None, value = None):
        for m in self.data['exec']:
            if event.lower() == m['event'].lower():
                if not act or not 'act' in m or (act and m['act'].lower() in act.lower()):
                    if not key or not 'key' in m or (key != None and key.lower() == m['key'].lower()):
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
            print("\t[" + event + "] DELAY " + ex['time'] + "s " + str(key) + ": " + str(value))
            sleep(float(ex['time']))
        if ex['type'].lower() == "notify":
            print("\t[" + event + "] " + str(key) + ": " + str(value))
        if ex['type'].lower() == "replace":
            print("\t[" + event + "] REPLACE " + ex['match'] + " -> " + ex['replace'])
            value = value.replace(ex['match'], ex['replace'])
        return value

    def getEndpoint(self, searchpath):
        for r in self.data['routing']:
            p = re.compile(r['match'])
            m = p.match(searchpath)
            
            if m:
                path = r['path']
                for i in range(1, 9):
                    if '$' + str(i) in path:
                         path = path.replace('$' + str(i), m.group(i))
                secure = False
                if 'secure' in r:
                    secure = r['secure']
                
                return [r['host'], path, secure]
        return None