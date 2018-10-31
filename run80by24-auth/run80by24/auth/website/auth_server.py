from authlib.flask.oauth2 import AuthorizationServer, ResourceProtector
from authlib.flask.oauth2.sqla import (
    create_query_client_func,
    create_save_token_func,
    create_revocation_endpoint,
    create_bearer_token_validator,
)
from authlib.specs.rfc6749 import grants
from werkzeug.security import gen_salt
from .models import db, User
from .oauth_models import OAuth2Client, OAuth2AuthorizationCode, OAuth2Token
from .permission import deps as permission_deps

import redis

class AuthorizationCodeGrant(grants.AuthorizationCodeGrant):
    def create_authorization_code(self, client, user, request):
        code = gen_salt(48)
        item = OAuth2AuthorizationCode(
            code=code,
            client_id=client.client_id,
            redirect_uri=request.redirect_uri,
            scope=request.scope,
            user_id=user.id,
        )
        db.session.add(item)
        db.session.commit()
        return code

    def parse_authorization_code(self, code, client):
        item = OAuth2AuthorizationCode.query.filter_by(
            code=code, client_id=client.client_id).first()
        if item and not item.is_expired():
            return item

    def delete_authorization_code(self, authorization_code):
        db.session.delete(authorization_code)
        db.session.commit()

    def authenticate_user(self, authorization_code):
        return User.query.get(authorization_code.user_id)


class RefreshTokenGrant(grants.RefreshTokenGrant):
    def authenticate_refresh_token(self, refresh_token):
        item = OAuth2Token.query.filter_by(refresh_token=refresh_token).first()
        if item and not item.is_refresh_token_expired():
            return item

    def authenticate_user(self, credential):
        return User.query.get(credential.user_id)


auth_server = AuthorizationServer()
require_oauth = ResourceProtector()

save_token_to_db = create_save_token_func(db.session, OAuth2Token)

def save_token_to_db_and_redis(token,request):
    save_token_to_db(token,request)
    auth_server.redis_client.set('token:{}'.format(token['access_token']),token['scope'],ex=token['expires_in'])

def config_oauth(app):
    query_client = create_query_client_func(db.session, OAuth2Client)

    auth_server.init_app(
        app, query_client=query_client, save_token=save_token_to_db_and_redis)

    # support all grants
    auth_server.register_grant(grants.ImplicitGrant)
    auth_server.register_grant(grants.ClientCredentialsGrant)
    auth_server.register_grant(AuthorizationCodeGrant)
    auth_server.register_grant(RefreshTokenGrant)

    auth_server.redis_client = redis.StrictRedis(decode_responses=True)
    permission_deps.init_redis(auth_server.redis_client)

    # support revocation
    SQLARevocationEndpoint = create_revocation_endpoint(db.session, OAuth2Token)

    class RedisRevocationEndpoint(SQLARevocationEndpoint):
        def revoke_token(self,token):
            super().revoke_token(token)
            auth_server.redis_client.delete('token:{}'.format(token.access_token))

    auth_server.register_endpoint(RedisRevocationEndpoint)

    # protect resource
    bearer_cls = create_bearer_token_validator(db.session, OAuth2Token)
    require_oauth.register_token_validator(bearer_cls())
