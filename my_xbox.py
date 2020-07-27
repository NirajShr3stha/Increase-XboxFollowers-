import re
import json
import requests
from urllib.parse import urlparse, parse_qs, urlencode, unquote


class XBoxException(Exception):
    pass


class AuthenticationException(XBoxException):
    pass


class InvalidRequest(XBoxException):
    pass

    def __init__(self, message, response):
        self.message = message
        self.response = response


class Client:
    def __init__(self):
        self.session = requests.session()
        self.authenticated = False
        self.token_16hr = None
        self.token_14d = None
        self.user_xid = None
        self.user_gamertag = None
        self.access_token = None

    @staticmethod
    def _raise_for_status(response):
        if response.status_code == 400:
            try:
                description = response.json()['description']
            except:
                description = 'Invalid request'
            raise InvalidRequest(description, response=response)

    def _get(self, url, **kw):
        headers = kw.pop('headers', {})
        headers.setdefault('Content-Type', 'application/json')
        headers.setdefault('Accept', 'application/json')
        headers.setdefault('Authorization', self.token_16hr)
        kw['headers'] = headers
        resp = self.session.get(url, **kw)
        self._raise_for_status(resp)
        return resp

    def _post(self, url, **kw):
        headers = kw.pop('headers', {})
        headers.setdefault('Authorization', self.token_16hr)
        kw['headers'] = headers
        resp = self.session.post(url, **kw)
        self._raise_for_status(resp)
        return resp

    def _post_json(self, url, data, **kw):
        data = json.dumps(data)
        headers = kw.pop('headers', {})
        headers.setdefault('Content-Type', 'application/json')
        headers.setdefault('Accept', 'application/json')

        kw['headers'] = headers
        kw['data'] = data
        return self._post(url, **kw)

    def authenticate(self, login: str = None, password: str = None) -> object:
        if not login or not password:
            msg = (
                'Authentication credentials required. Please refer to '
                'http://xbox.readthedocs.org/en/latest/authentication.html'
            )
            raise AuthenticationException(msg)

        base_url = 'https://login.live.com/oauth20_authorize.srf?'

        qs = unquote(urlencode({
            'client_id': '0000000048093EE3',
            'redirect_uri': 'https://login.live.com/oauth20_desktop.srf',
            'response_type': 'token',
            'display': 'touch',
            'scope': 'service::user.auth.xboxlive.com::MBI_SSL',
            'locale': 'en',
        }))
        resp = self.session.get(base_url + qs)

        url_re = b'urlPost:\\\'([A-Za-z0-9:\?_\-\.&/=]+)'
        ppft_re = b'sFTTag:\\\'.*value="(.*)"/>'

        login_post_url = re.search(url_re, resp.content).group(1)
        post_data = {
            'login': login,
            'passwd': password,
            'PPFT': re.search(ppft_re, resp.content).groups(1)[0],
            'PPSX': 'Passpor',
            'SI': 'Sign in',
            'type': '11',
            'NewUser': '1',
            'LoginOptions': '1',
            'i3': '36728',
            'm1': '768',
            'm2': '1184',
            'm3': '0',
            'i12': '1',
            'i17': '0',
            'i18': '__Login_Host|1',
        }

        resp = self.session.post(
            login_post_url, data=post_data, allow_redirects=False,
        )

        if 'Location' not in resp.headers:
            # we can only assume the login failed
            msg = 'Could not log in with supplied credentials'
            raise AuthenticationException(msg)

        # the access token is included in fragment of the location header
        location = resp.headers['Location']
        parsed = urlparse(location)
        fragment = parse_qs(parsed.fragment)
        self.access_token = fragment['access_token'][0]

        url = 'https://user.auth.xboxlive.com/user/authenticate'
        resp = self.session.post(url, data=json.dumps({
            "RelyingParty": "http://auth.xboxlive.com",
            "TokenType": "JWT",
            "Properties": {
                "AuthMethod": "RPS",
                "SiteName": "user.auth.xboxlive.com",
                "RpsTicket": self.access_token,
            }
        }), headers={'Content-Type': 'application/json'})

        json_data = resp.json()
        user_token = json_data['Token']
        uhs = json_data['DisplayClaims']['xui'][0]['uhs']

        url = 'https://xsts.auth.xboxlive.com/xsts/authorize'
        resp = self.session.post(url, data=json.dumps({
            "RelyingParty": "http://xboxlive.com",
            "TokenType": "JWT",
            "Properties": {
                "UserTokens": [user_token],
                "SandboxId": "RETAIL",
            }
        }), headers={'Content-Type': 'application/json'})

        response = resp.json()
        with open('response.json', 'w', encoding='utf-8') as file:
            file.write(json.dumps(response))

        self.token_16hr = 'XBL3.0 x=%s;%s' % (uhs, response['Token'])
        self.user_xid = response['DisplayClaims']['xui'][0]['xid']
        self.user_gamertag = response['DisplayClaims']['xui'][0]['gtg']
        self.authenticated = True

        return self
