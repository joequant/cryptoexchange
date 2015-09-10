#!/usr/bin/env python3
#-*- coding:utf-8 -*-

"""
    796 API Trading Example/DEMO in Python

    After getToken.

"""

import urllib.request, urllib.error, urllib.parse
import time
import base64
import hashlib
import hmac
import http.client
import json

def get_796_token(appid,apikey,secretkey):
    timestamp = time.time()#"1414142919" #time.time()
    params = {"apikey": apikey, "appid": appid, "secretkey": secretkey, "timestamp": str(timestamp)}
    params = sorted(iter(params.items()), key=lambda d: d[0], reverse=False)
    message = urllib.parse.urlencode(params)
    print("secretkey=",secretkey)
    print("message=",message)
    s = hmac.new(secretkey.encode('utf-8'),
                 message.encode('utf-8'),
                 digestmod=hashlib.sha1).hexdigest()
    print("hex=",s)
    sig = base64.b64encode(s.encode('utf-8'))
    print("sig=",sig)

    payload = urllib.parse.urlencode({'appid': appid, 'apikey': apikey, 'timestamp': timestamp, 'sig': sig})

    c = http.client.HTTPSConnection('796.com')
    c.request("GET", "/oauth/token?"+payload)
    r = c.getresponse()

    if r.status == 200:
        data = r.read()
        jsonDict = json.loads(data.decode('utf-8'));
        errno = jsonDict['errno']
        if errno=="0":
            return jsonDict['data']['access_token']
    return None



def getUserInfo(sAccessToken):
    sUrl = "/v1/user/get_info?access_token=%s" % (sAccessToken)
    c = http.client.HTTPSConnection('796.com')
    c.request("GET", sUrl)
    r = c.getresponse()
    print("r.status=",r.status)
    print(r.read())

def getUserInfo1(sAccessToken):
    sUrl = "https://796.com/v1/user/get_info?access_token=%s" % (sAccessToken)
    response = urllib.request.urlopen(sUrl)
    print(response.read())

def getUserInfo2(sAccessToken):
    import requests
    sUrl = "https://796.com/v1/user/get_info?access_token=%s" % (sAccessToken)
    response = requests.get(sUrl, timeout=20)
    print(response.content)

def getUserInfoError(sAccessToken):
    """
        May be return {u'msg': u'Access_token repealed', u'errno': u'-102', u'data': []}
    """
    import urllib.request, urllib.parse, urllib.error
    payload = urllib.parse.urlencode({'access_token': sAccessToken})
    c = http.client.HTTPSConnection('796.com')
    c.request("GET", "/v1/user/get_info?"+payload)
    r = c.getresponse()
    data = r.read()
    jsonDict = json.loads(data.decode('utf-8'));
    print(jsonDict)

def testHMacSHA(secretkey,message):
    print("secretkey=",secretkey)
    print("message=",message)
    s = hmac.new(secretkey, message.encode('utf-8'),
                 digestmod=hashlib.sha1).hexdigest()
    print("hex=",s)

if __name__ == "__main__":
    testHMacSHA(b"HF94bR940e1d9YZwfgickG5HR07SFJQGscgO+E3vFPQGwSzyGtUQLxIh6blv",
        "apikey=5999a1ce-4312-8a3c-75a5-327c-f5cf5251&appid=11040&secretkey=HF94bR940e1d9YZwfgickG5HR07SFJQGscgO%2BE3vFPQGwSzyGtUQLxIh6blv&timestamp=1414142919")

    access_token = get_796_token(appid = '##YOUR APPID##',apikey='##YOUR APIKEY##',secretkey='##YOUR SECRETKEY##')
    print("access_token=",access_token)

    getUserInfo(access_token)
    getUserInfo1(access_token)
    getUserInfo2(access_token)
    getUserInfoError(access_token)
