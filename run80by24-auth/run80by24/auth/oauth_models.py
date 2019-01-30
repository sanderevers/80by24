from authlib.flask.oauth2.sqla import (
    OAuth2ClientMixin,
    OAuth2AuthorizationCodeMixin,
    OAuth2TokenMixin,
)
from werkzeug.security import gen_salt
import time
from .models import TTY,db

class OAuth2Client(db.Model, OAuth2ClientMixin):
    __tablename__ = 'oauth2_client'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'))
    user = db.relationship('User')
    event_uri = db.Column(db.Text)

    @staticmethod
    def emport(req_client):
        flow = req_client.pop('flow')
        client = OAuth2Client(**req_client)
        client.client_id = gen_salt(24)
        if flow=='code':
            client.grant_type = 'authorization_code'
            client.response_type = 'code'
            client.token_endpoint_auth_method = 'client_secret_basic'
            client.client_secret = gen_salt(48)
        else:
            client.grant_type = 'implicit'
            client.response_type = 'token'
            client.token_endpoint_auth_method = 'none'
            client.client_secret = ''
        return client

    def export(self):
        json_keys = ['client_id', 'client_name', 'client_secret', 'redirect_uri', 'event_uri']
        ret = {k: getattr(self, k) for k in json_keys}
        ret['flow'] = 'code' if self.grant_type == 'authorization_code' else 'implicit'
        return ret

class OAuth2AuthorizationCode(db.Model, OAuth2AuthorizationCodeMixin):
    __tablename__ = 'oauth2_code'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'))
    user = db.relationship('User')


class OAuth2Token(db.Model, OAuth2TokenMixin):
    __tablename__ = 'oauth2_token'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'))
    user = db.relationship('User')

    def is_refresh_token_expired(self):
        expires_at = self.issued_at + self.expires_in * 2
        return expires_at < time.time()