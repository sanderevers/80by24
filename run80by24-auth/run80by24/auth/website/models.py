import time
from authlib.specs.oidc.grants.base import UserInfo
from flask import g
from flask_sqlalchemy import SQLAlchemy
from authlib.flask.oauth2.sqla import (
    OAuth2ClientMixin,
    OAuth2AuthorizationCodeMixin,
    OAuth2TokenMixin,
)

db = SQLAlchemy()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sub = db.Column(db.String(40), unique=True)

    def __str__(self):
        return self.sub

    def get_user_id(self):
        return self.id

    def generate_user_info(self,scopes):
        return UserInfo(sub=self.sub, name=self.sub)

class TTY(db.Model):
    __tablename__ = 'tty'
    id = db.Column(db.String(20), primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'))
    owner = db.relationship('User')

class MayInteract(db.Model):
    __tablename__ = 'may_interact'
    id = db.Column(db.Integer, primary_key=True)
    tty_id = db.Column(db.Integer, db.ForeignKey('tty.id', ondelete='CASCADE'))
    tty = db.relationship('TTY')
    client_id = db.Column(db.Integer, db.ForeignKey('oauth2_client.id', ondelete='CASCADE'))
    client = db.relationship('OAuth2Client')


class OAuth2Client(db.Model, OAuth2ClientMixin):
    __tablename__ = 'oauth2_client'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'))
    user = db.relationship('User')

    # NB this makes the scope field useless
    def check_requested_scopes(self, scopes):
        user = g.user
        user_ttys = db.session.query(TTY).filter_by(owner_id=user.id).all()
        return set(tty.id for tty in user_ttys).issuperset(set(scopes))



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
