from contextlib import contextmanager
from flask import session, g, url_for, request, Blueprint, redirect
from ..models import User, db
from ..federation import federation
from ..auth_server import auth_server
from authlib.client.errors import OAuthException
from authlib.common.security import generate_token

bp = Blueprint('authc', __name__)

class NotAuthenticatedException(Exception):
    def __init__(self, redirect=False):
        self.redirect = redirect

def authenticate(sub):
    user = User.query.filter_by(sub=sub).first()
    if not user:
        user = User(sub=sub)
        db.session.add(user)
        db.session.commit()
    session['id'] = user.id

def current_user():
    if 'id' in session:
        uid = session['id']
        return User.query.get(uid)
    return None

def unauthenticate():
    del session['id']

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

# if user is not authenticated yet, log in with solidsea
def handle_notauthenticated(exc):
    if exc.redirect:
        oidc_client = federation.get('solidsea')
        redirect_uri = url_for('authc.callback', _external=True)
        state = remember_own_flow()
        return oidc_client.authorize_redirect(redirect_uri,state=state)
    else:
        return '', 403

def remember_own_flow():
    state = generate_token()
    own_flow = request.endpoint, request.view_args, request.args
    session['own_flow_'+state] = own_flow
    return state

def recall_own_flow(state):
    return session.pop('own_flow_'+state, None)

@bp.route('/login')
def login():
    with authenticated_user(redirect=True) as user:
        return 'You are logged in as {}.'.format(user)

@bp.route('/callback')
def callback():
    if request.args.get('error'):
        return auth_server.create_authorization_response() # access_denied error response

    oidc_client = federation.get('solidsea')
    try:
        # /token call to solidsea (token is saved in oidc_client state)
        oidc_client.authorize_access_token()
    except OAuthException:
        return auth_server.create_authorization_response()

    oidc_sub = oidc_client.fetch_oidc_sub()
    authenticate(oidc_sub)

    endpoint,view_args,req_args = recall_own_flow(request.args.get('state'))
    return redirect(url_for(endpoint,**view_args,**req_args))

@bp.route('/logout')
def logout():
    unauthenticate()
    return redirect('/')