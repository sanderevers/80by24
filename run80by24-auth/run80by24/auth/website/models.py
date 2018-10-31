from authlib.specs.oidc.grants.base import UserInfo
from flask_sqlalchemy import SQLAlchemy

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



