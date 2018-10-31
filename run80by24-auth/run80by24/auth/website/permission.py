from .models import MayInteract, db, User, TTY
from .oauth_models import OAuth2Token

# for dependency injection
class Deps:
    def init_redis(self, redis_client):
        self.redis_client = redis_client

deps = Deps()

class NotPermittedException(Exception):
    def __init__(self, perm):
        self.perm = perm

class ToInteract:
    def __init__(self, client, tty):
        self.client = client
        self.tty = tty

    def __bool__(self):
        return self.test()

    def test(self):
        return MayInteract.query \
            .filter(MayInteract.client == self.client) \
            .filter(MayInteract.tty == self.tty) \
            .one_or_none() is not None

    def grant_by(self,granting_sub):
        to_grant = ToGrant(granting_sub,self)
        if to_grant.test():
            # test for existing?
            mi = MayInteract(client = self.client, tty = self.tty)
            db.session.add(mi)
            db.session.commit()
            # or defer commit to request finalisation?
            #https://chase-seibert.github.io/blog/2016/03/31/flask-sqlalchemy-sessionless.html
        else:
            raise NotPermittedException(to_grant)

    def revoke_by(self, revoking_sub):
        to_grant = ToGrant(revoking_sub, self)
        if to_grant.test():
            mi = MayInteract.query \
                .filter(MayInteract.client == self.client) \
                .filter(MayInteract.tty == self.tty) \
                .one_or_none()
            if mi:
                db.session.delete(mi)
                db.session.commit()
                # or defer commit to request finalisation?
            tokens = OAuth2Token.query \
                .filter_by(client_id = self.client.client_id) \
                .filter_by(user = revoking_sub) \
                .all()
            for token in tokens:
                if self.tty.id in token.scope.split():
                    token.revoked = True
                    deps.redis_client.delete('token:{}'.format(token.access_token))
        else:
            raise NotPermittedException(to_grant)



class Owner:
    def __init__(self,sub,res):
        self.sub = sub
        self.res = res

    def test(self):
        if isinstance(self.sub,User) and isinstance(self.res,TTY):
            return self.res.owner is self.sub
        return False

    def grant_by(self,granting_sub):
        if granting_sub=='80by24' and isinstance(self.res,TTY):
            self.res.owner = self.sub
            db.session.add(self.res)
            deps.redis_client.sadd('claimed', self.res.id)
            db.session.commit() # TODO or not?
        else:
            raise NotPermittedException(self)

class ToGrant:
    def __init__(self, sub, perm):
        self.sub = sub
        self.perm = perm

    def test(self):
        if isinstance(self.perm,ToInteract):
            return Owner(self.sub, self.perm.tty).test()
        return False
