from flask import Blueprint, request, session, g
from flask import render_template, redirect, jsonify, url_for
from werkzeug.security import gen_salt
from authlib.flask.oauth2 import current_token
from authlib.specs.rfc6749 import OAuth2Error
from authlib.client.errors import OAuthException
from .models import db, User, OAuth2Client, TTY, MayInteract
from .auth_server import auth_server, require_oauth
from .federation import federation
from urllib.parse import quote_plus
from contextlib import contextmanager
from copy import copy

bp = Blueprint(__name__, 'home')

class NotAuthenticatedException(Exception):
    pass

@contextmanager
def authenticated_user():
    user = current_user()
    if user:
        g.user = user
        print('g.user: {}'.format(user.sub))
        try:
            yield user
        finally:
            g.user = None
            print('g.user removed')
    else:
        raise NotAuthenticatedException

def current_user():
    if 'id' in session:
        uid = session['id']
        return User.query.get(uid)
    return None

def remember_own_flow_args():
    own_flow_args = {}
    for arg in ('scope','client_id','state','nonce','response_type','redirect_uri'):
        if request.args.get(arg):
            own_flow_args[arg] = request.args[arg] # or encode it in state?
    session['own_flow_args'] = own_flow_args

def recall_own_flow_args():
    return session.pop('own_flow_args',None)


@bp.route('/')
def home():
    user = current_user()
    if user:
        clients = OAuth2Client.query.filter_by(user_id=user.id).all()
    else:
        clients = []
    return render_template('home.html', user=user, clients=clients)

@bp.route('/logout')
def logout():
    del session['id']
    return redirect('/')

@bp.route('/create_client', methods=('GET', 'POST'))
def create_client():
    with authenticated_user() as user:
        if request.method == 'GET':
            return render_template('create_client.html')

        client = OAuth2Client(**request.form.to_dict(flat=True))
        client.user_id = user.id
        client.client_id = gen_salt(24)
        if client.token_endpoint_auth_method == 'none':
            client.client_secret = ''
        else:
            client.client_secret = gen_salt(48)
        db.session.add(client)
        db.session.commit()
        return redirect('/')

@bp.route('/claim/<tty_id>')
def claim(tty_id):
    with authenticated_user() as user:
        existing = db.session.query(TTY).filter_by(id=tty_id).first()
        if not existing:
            new = TTY(id=tty_id, owner=user)
            db.session.add(new)
            db.session.commit()
            return 'claimed'
        if existing.owner is user:
            return 'redundant'
        else:
            return 'denied'


@bp.route('/authorize', methods=['GET', 'POST'])
def authorize():
    user = current_user()
    if not user:
        remember_own_flow_args()
        raise NotAuthenticatedException
    g.user = user

    if request.method == 'GET':
        try:
            grant = auth_server.validate_consent_request(end_user=user)
            perm = db.session.query(MayInteract).filter_by(tty_id=grant.request.scope,client_id=grant.client.client_id).first()
            if perm:
                return auth_server.create_authorization_response(grant_user=user)
        except OAuth2Error as error:
            return error.error
        return render_template('authorize.html', user=user, grant=grant)

    if request.form.get('confirm'):
        grant_user = user

        # save permission
        grant = auth_server.validate_consent_request(end_user=user)
        for tty_id in grant.request.scope.split(' '):
            perm = MayInteract(tty_id = tty_id, client_id = grant.client.client_id)
            db.session.add(perm)
        db.session.commit()
    else:
        grant_user = None
    return auth_server.create_authorization_response(grant_user=grant_user)



@bp.errorhandler(NotAuthenticatedException)
def authenticate_user(err):
    oidc_client = federation.get('solidsea')
    redirect_uri = url_for('.callback', _external=True)
    return oidc_client.authorize_redirect(redirect_uri)

@bp.route('/callback')
def callback():
    if request.args.get('error'):
        return auth_server.create_authorization_response() # access_denied error response

    oidc_client = federation.get('solidsea')
    try:
        oidc_client.authorize_access_token()
    except OAuthException:
        return auth_server.create_authorization_response()

    oidc_sub = oidc_client.fetch_oidc_sub()

    user = User.query.filter_by(sub=oidc_sub).first()
    if not user:
        user = User(sub=oidc_sub)
        db.session.add(user)
        db.session.commit()
    session['id'] = user.id

    own_flow_args = recall_own_flow_args()
    if own_flow_args:
        qp = '&'.join('{}={}'.format(quote_plus(k),quote_plus(v)) for k,v in own_flow_args.items())
        return redirect(url_for('.authorize')+'?'+qp)
    else:
        return redirect(url_for('.create_client'))

@bp.route('/token', methods=['POST'])
def token():
    return auth_server.create_token_response()


@bp.route('/revoke', methods=['POST'])
def revoke_token():
    return auth_server.create_endpoint_response('revocation')


@bp.route('/api/me')
@require_oauth('profile')
def api_me():
    user = current_token.user
    return jsonify(id=user.id, username=user.username)
