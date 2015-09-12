#!/usr/bin/env python3
from websocket import create_connection
import json, base64, hashlib, urllib.parse, hmac, time
import requests
import os
import uuid

###
# websocket-apikey-auth-test.py
#
# Reference Python implementation for authorizing with websocket.
# See https://www.bitmex.com/app/wsAPI for more details, including a list
# of methods.
###

# These are not real keys - replace them with your keys.
API_KEY = os.environ.get("API_KEY", None)
API_SECRET = os.environ.get("API_SECRET", None)

# Switch these comments to use testnet instead.
BITMEX_URL = "https://testnet.bitmex.com"
#BITMEX_URL = "https://www.bitmex.com"

VERB = "GET"
ENDPOINT = "/api/v1"

from requests.auth import AuthBase
import urllib.parse
import time
import hashlib
import hmac

class APIKeyAuthWithExpires(AuthBase):

    """Attaches API Key Authentication to the given Request object. This implementation uses `expires`."""

    def __init__(self, apiKey, apiSecret):
        """Init with Key & Secret."""
        self.apiKey = apiKey
        self.apiSecret = apiSecret

    def __call__(self, r):
        """
        Called when forming a request - generates api key headers. This call uses `expires` instead of nonce.

        This way it will not collide with other processes using the same API Key if requests arrive out of order.
        For more details, see https://www.bitmex.com/app/apiKeys
        """
        # modify and return the request
        expires = int(round(time.time()) + 5) # 5s grace period in case of clock skew 
#        r.headers['api-expires'] = str(expires)
        r.headers['api-expires'] = str(expires)
        r.headers['api-key'] = self.apiKey
        data = r.body or ''
        r.headers['api-signature'] = self.generate_signature(self.apiSecret, r.method, r.url, expires, data)
        return r

    # Generates an API signature.
    # A signature is HMAC_SHA256(secret, verb + path + nonce + data), hex encoded.
    # Verb must be uppercased, url is relative, nonce must be an increasing 64-bit integer
    # and the data, if present, must be JSON without whitespace between keys.
    # 
    # For example, in psuedocode (and in real code below):
    # 
    # verb=POST
    # url=/api/v1/order
    # nonce=1416993995705
    # data={"symbol":"XBTZ14","quantity":1,"price":395.01}
    # signature = HEX(HMAC_SHA256(secret, 'POST/api/v1/order1416993995705{"symbol":"XBTZ14","quantity":1,"price":395.01}'))
    def generate_signature(self, secret, verb, url, nonce, data):
        """Generate a request signature compatible with BitMEX."""
        # Parse the url so we can remove the base and extract just the path.
        parsedURL = urllib.parse.urlparse(url)
        path = parsedURL.path
        if parsedURL.query:
            path = path + '?' + parsedURL.query
        
        print(verb, path, nonce, data)
        # print "Computing HMAC: %s" % verb + path + str(nonce) + data
        message = bytes(verb + path + str(nonce) + data, "utf-8")
        signature = hmac.new(secret.encode("utf-8"),
                             message,
                             digestmod=hashlib.sha256).hexdigest()
        return signature



def main():
    """Authenticate with the BitMEX API & request account information."""
    test_with_message()

def test_with_message():
    # This is up to you, most use microtime but you may have your own scheme so long as it's increasing
    auth = APIKeyAuthWithExpires(API_KEY, API_SECRET)
    query = None
    data = None
    postdict = None
    timeout = 3
    session = requests.Session()
    session.headers.update({'user-agent': 'bitmex-robot'})
    url = BITMEX_URL + ENDPOINT + "/position"
    req = requests.Request(VERB, url, data=postdict, auth=auth, params=query)
    prepped = session.prepare_request(req)
    response = session.send(prepped, timeout=timeout)
    print(url, response.text)

    url = BITMEX_URL + ENDPOINT + "/order"
    clOrdID = "test_" + \
              base64.b64encode(uuid.uuid4().bytes).decode('ascii').rstrip('=\n')
    postdict = {"symbol" : "XBT7D",
                "quantity" : -10,
                "price" : 241.0,
                "clOrdID": clOrdID}
    
    req = requests.Request("POST", url, data=postdict, auth=auth, params=query)
    prepped = session.prepare_request(req)
    response = session.send(prepped, timeout=timeout)
    print(url, response.text)

if __name__ == "__main__":
    main()
