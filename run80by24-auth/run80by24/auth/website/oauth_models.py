from authlib.flask.oauth2.sqla import (
    OAuth2ClientMixin,
    OAuth2AuthorizationCodeMixin,
    OAuth2TokenMixin,
)
from flask import g
import time
from . import permission
from .models import TTY,db

class OAuth2Client(db.Model, OAuth2ClientMixin):
    __tablename__ = 'oauth2_client'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'))
    user = db.relationship('User')

    # NB this makes the scope field useless
    def check_requested_scopes(self, scopes):
        requested_ttys = db.session.query(TTY).filter(TTY.id.in_(scopes)).all()
        if len(requested_ttys) != len(scopes):
            return False
        return all(permission.ToGrant(g.user,permission.ToInteract(self,tty)).test() for tty in requested_ttys)
        # user = g.user
        # user_ttys = db.session.query(TTY).filter_by(owner_id=user.id).all()
        # return set(tty.id for tty in user_ttys).issuperset(set(scopes))


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