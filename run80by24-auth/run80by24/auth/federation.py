from authlib.flask.client import OAuth, RemoteApp
from authlib.specs.rfc7519 import JWT
from authlib.specs.rfc7517 import JWK
from authlib.specs.rfc7518 import JWK_ALGORITHMS

import requests


class Federation:
    def __init__(self):
        self.clients = set()
        self._authlib_clients = OAuth()

    def register(self, client_name, **kwargs):
        self.clients.add(client_name)
        self._authlib_clients.register(client_name, **kwargs)

    def get(self, client_name):
        if client_name in self.clients:
            return self._authlib_clients.create_client(client_name)
        return None

    def init_app(self, app):
        self.register('solidsea', client_cls=OIDCClient, discovery_url=app.config['SOLIDSEA_DISCOVERY_URL'])
        self._authlib_clients.init_app(app)


class OIDCClient(RemoteApp):
    def __init__(self, name, discovery_url, **kwargs):
        discovery = self.fetch_discovery(discovery_url)
        self.issuer = discovery['issuer']
        self.jwks_uri = discovery['jwks_uri']
        self.jwks = {'keys':[]}
        kwargs['client_kwargs'] = {'scope':'openid'}
        kwargs['authorize_url'] = discovery['authorization_endpoint']
        kwargs['access_token_url'] = discovery['token_endpoint']
        super().__init__(name, **kwargs)

    def fetch_oidc_sub(self):
        options = {
            'iss' : {'essential':True, 'value':self.issuer},
            'aud' : {'essential':True, 'value':self.client_id},
            'exp' : {'essential':True}
        }
        id_token = JWT().decode(self.token['id_token'], self.load_key, claims_options=options)
        id_token.validate() # checking signature is not strictly necessary but let's do it anyway
        return id_token.sub

    def fetch_discovery(self, url):
        resp = requests.get(url)
        if not resp.status_code == 200:
            raise Exception('OIDC discovery URL {} returning {}.'.format(url, resp.status_code))
        return resp.json()

    def load_key(self, header, payload):
        kid = header['kid']
        if not any(key['kid']==kid for key in self.jwks['keys']):
            self.jwks = requests.get(self.jwks_uri).json()
        jwk = JWK(algorithms=JWK_ALGORITHMS)
        key = jwk.loads(self.jwks,kid)
        return key

federation = Federation()
