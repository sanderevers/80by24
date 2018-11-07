from contextlib import contextmanager
from flask import session, g, url_for
from ..models import User
from ..federation import federation

class NotAuthenticatedException(Exception):
    def __init__(self, redirect=False):
        self.redirect = redirect

@contextmanager
def authenticated_user(redirect=False):
    user = current_user()
    if user:
        g.user = user
        try:
            yield user
        finally:
            g.user = None
    else:
        raise NotAuthenticatedException(redirect=redirect)

def current_user():
    if 'id' in session:
        uid = session['id']
        return User.query.get(uid)
    return None

# if user is not authenticated yet, log in with solidsea
def authenticate_user(exc):
    if exc.redirect:
        oidc_client = federation.get('solidsea')
        redirect_uri = url_for('oauth2.callback', _external=True)
        return oidc_client.authorize_redirect(redirect_uri)
    else:
        return '', 403