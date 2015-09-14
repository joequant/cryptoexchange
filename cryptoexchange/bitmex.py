#!/usr/bin/env python3

"""BitMEX API Connector."""
import requests
from time import sleep
import json
import uuid
import logging
import base64

class AuthenticationError(Exception):
    pass

from requests.auth import AuthBase

class AccessTokenAuth(AuthBase):

    """Attaches Access Token Authentication to the given Request object."""

    def __init__(self, accessToken):
        """Init with Token."""
        self.token = accessToken

    def __call__(self, r):
        """Called when forming a request - generates access token header."""
        if (self.token):
            r.headers['access-token'] = self.token
        return r

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
        # print "Computing HMAC: %s" % verb + path + str(nonce) + data
        message = bytes(verb + path + str(nonce) + data, "utf-8")
        signature = hmac.new(secret.encode("utf-8"),
                             message,
                             digestmod=hashlib.sha256).hexdigest()
        return signature

# https://www.bitmex.com/api/explorer/
class BitMEX(object):

    """BitMEX API Connector."""

    def __init__(self, base_url=None, login=None, password=None, otpToken=None,
                 apiKey=None, apiSecret=None, orderIDPrefix='mm_bitmex_'):
        """Init connector."""
        self.logger = logging.getLogger('root')
        self.base_url = base_url
        self.token = None
        self.login = login
        self.password = password
        self.otpToken = otpToken
        self.apiKey = apiKey
        self.apiSecret = apiSecret
        if len(orderIDPrefix) > 13:
            raise ValueError("settings.ORDERID_PREFIX must be at most 13 characters long!")
        self.orderIDPrefix = orderIDPrefix

        # Prepare HTTPS session
        self.session = requests.Session()
        # These headers are always sent
        self.session.headers.update({'user-agent': 'bitmex-robot'})

    #
    # Authentication required methods
    #
    def authenticate(self):
        """Set BitMEX authentication information."""
        if self.apiKey:
            return
        loginResponse = self._curl_bitmex(
            api="user/login",
            postdict={'email': self.login, 'password': self.password, 'token': self.otpToken})
        self.token = loginResponse['id']
        self.session.headers.update({'access-token': self.token})

    def authentication_required(function):
        """Annotation for methods that require auth."""
        def wrapped(self, *args, **kwargs):
            if not (self.token or self.apiKey):
                msg = "You must be authenticated to use this method"
                raise AuthenticationError(msg)
            else:
                return function(self, *args, **kwargs)
        return wrapped

    @authentication_required
    def position(self):
        return self._curl_bitmex(api="position", verb="GET")

    @authentication_required
    def place_order(self, quantity, symbol, price):
        """Place an order."""
        if price < 0:
            raise Exception("Price must be positive.")

        endpoint = "order"
        # Generate a unique clOrdID with our prefix so we can identify it.
        clOrdID = self.orderIDPrefix + base64.b64encode(uuid.uuid4().bytes).decode('ascii').rstrip('=\n')
        postdict = {
            'symbol': symbol,
            'quantity': quantity,
            'price': price,
            'clOrdID': clOrdID
        }
        return self._curl_bitmex(api=endpoint, postdict=postdict, verb="POST")

    @authentication_required
    def open_orders(self, symbol=None):
        """Get open orders via HTTP. Used on close to ensure we catch them all."""
        api = "order"
        query = {'ordStatus.isTerminated': False }
        if symbol != None:
            query['symbol'] =symbol
        orders = self._curl_bitmex(
            api=api,
            query={'filter': json.dumps(query)},
            verb="GET"
        )
        return orders
#        # Only return orders that start with our clOrdID prefix.
#        return [o for o in orders if str(o['clOrdID']).startswith(self.orderIDPrefix)]

    @authentication_required
    def cancel(self, orderID):
        """Cancel an existing order."""
        api = "order"
        postdict = {
            'orderID': orderID,
        }
        return self._curl_bitmex(api=api, postdict=postdict, verb="DELETE")

    def _curl_bitmex(self, api, query=None, postdict=None, timeout=3, verb=None):
        """Send a request to BitMEX Servers."""
        # Handle URL
        url = self.base_url + api

        # Default to POST if data is attached, GET otherwise
        if not verb:
            verb = 'POST' if postdict else 'GET'

        # Auth: Use Access Token by default, API Key/Secret if provided
        auth = AccessTokenAuth(self.token)
        if self.apiKey:
            auth = APIKeyAuthWithExpires(self.apiKey, self.apiSecret)

        # Make the request
        try:
#            url = "http://httpbin.org/post"
            req = requests.Request(verb, url, data=postdict, auth=auth, params=query)
            prepped = self.session.prepare_request(req)
            response = self.session.send(prepped, timeout=timeout)
            # Make non-200s throw
            response.raise_for_status()

        except requests.exceptions.HTTPError as e:
            # 401 - Auth error. Re-auth and re-run this request.
            if response.status_code == 401:
                if self.token is None:
                    self.logger.error("Login information or API Key incorrect, please check and restart.")
                    self.logger.error("Error: " + response.text)
                    if postdict:
                        self.logger.error(postdict)
                self.logger.warning("Token expired, reauthenticating...")
                sleep(1)
                self.authenticate()
                return self._curl_bitmex(api, query, postdict, timeout, verb)

            # 404, can be thrown if order canceled does not exist.
            elif response.status_code == 404:
                if verb == 'DELETE':
                    self.logger.error("Order not found: %s" % postdict['orderID'])
                    return
                self.logger.error("Unable to contact the BitMEX API (404). " +
                                  "Request: %s \n %s" % (url, json.dumps(postdict)))
            # 429, ratelimit
            elif response.status_code == 429:
                self.logger.error("Ratelimited on current request. Sleeping, then trying again. Try fewer " +
                                  "order pairs or contact support@bitmex.com to raise your limits. " +
                                  "Request: %s \n %s" % (url, json.dumps(postdict)))
                sleep(1)
                return self._curl_bitmex(api, query, postdict, timeout, verb)

            # 503 - BitMEX temporary downtime, likely due to a deploy. Try again
            elif response.status_code == 503:
                self.logger.warning("Unable to contact the BitMEX API (503), retrying. " +
                                    "Request: %s \n %s" % (url, json.dumps(postdict)))
                sleep(1)
                return self._curl_bitmex(api, query, postdict, timeout, verb)
            # Unknown Error
            else:
                self.logger.error("Unhandled Error: %s: %s %s" % (e, response.text, json.dumps(response.json(), indent=4)))
                self.logger.error("Endpoint was: %s %s" % (verb, api))
        except requests.exceptions.Timeout as e:
            # Timeout, re-run this request
            self.logger.warning("Timed out, retrying...")
            return self._curl_bitmex(api, query, postdict, timeout, verb)

        except requests.exceptions.ConnectionError as e:
            self.logger.warning("Unable to contact the BitMEX API (ConnectionError). Please check the URL. Retrying. " +
                                "Request: %s \n %s" % (url, json.dumps(postdict)))
            sleep(1)
            return self._curl_bitmex(api, query, postdict, timeout, verb)

        return response.json()

if __name__ == "__main__":
    # create console handler and set level to debug
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    # create formatter
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    # add formatter to ch
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    auth = APIKeyAuthWithExpires('LAqUlngMIQkIUjXMUreyu3qn',
                                 'chNOOS4KvNXR_Xq4k4c9qsfoKWvnDecLATCRlcBwyKDYnWgO')
    print (auth.generate_signature('chNOOS4KvNXR_Xq4k4c9qsfoKWvnDecLATCRlcBwyKDYnWgO',
                                   'POST',
                                   '/api/v1/order',
                                   1429631577995,
                                   '{"symbol":"XBTM15","price":219.0,"clOrdID":"mm_bitmex_1a/oemUeQ4CAJZgP3fjHsA","quantity":98}'))
