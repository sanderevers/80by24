from flask import Blueprint, request, session, g
from flask import render_template, redirect, jsonify, url_for
from werkzeug.security import gen_salt
from authlib.flask.oauth2 import current_token
from authlib.specs.rfc6749 import OAuth2Error
from authlib.client.errors import OAuthException
from .models import db, User, TTY, MayInteract
from .oauth_models import OAuth2Client
from .auth_server import auth_server, require_oauth
from .federation import federation
from urllib.parse import quote_plus
from contextlib import contextmanager
from . import permission

bp = Blueprint(__name__, 'home')

class NotAuthenticatedException(Exception):
    pass

@contextmanager
def authenticated_user():
    user = current_user()
    if user:
        g.user = user
        try:
            yield user
        finally:
            g.user = None
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
        ttys = TTY.query.filter_by(owner=user).all()
        grants = MayInteract.query.filter(MayInteract.tty_id.in_([tty.id for tty in ttys])).all()
    else:
        clients = []
        ttys = []
        grants = []
    return render_template('home.html', user=user, clients=clients, ttys=ttys, grants=grants)

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
        tty = TTY.query.get(tty_id)
        if not tty:
            tty = TTY(id=tty_id)
            permission.Owner(user,tty).grant_by('80by24')
            return 'claimed'
        if permission.Owner(user,tty).test():
            return 'redundant'
        else:
            return 'denied'

@bp.route('/release/<tty_id>')
def release(tty_id):
    with authenticated_user() as user:
        tty = TTY.query.get(tty_id)
        if tty:
            mis = MayInteract.query.filter_by(tty=tty).all()
            for mi in mis:
                permission.ToInteract(mi.client, mi.tty).revoke_by(user)
            permission.Owner(user,tty).revoke_by('80by24')
            return 'released'
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
            tty_id = grant.request.scope # support multiple ttys?
            tty = TTY.query.get(tty_id)
            if permission.ToInteract(grant.client, tty).test():
                return auth_server.create_authorization_response(grant_user=user)
        except OAuth2Error as error:
            return error.error
        return render_template('authorize.html', user=user, grant=grant)

    # POST
    if request.form.get('confirm'):
        grant_user = user

        # save permission
        grant = auth_server.validate_consent_request(end_user=user)
        for tty_id in grant.request.scope.split(' '):
            tty = db.session.query(TTY).get(tty_id)
            permission.ToInteract(grant.client,tty).grant_by(user)
        db.session.commit()
    else:
        grant_user = None
    return auth_server.create_authorization_response(grant_user=grant_user)


# if user is not authenticated yet, log in with solidsea
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
        # /token call to solidsea (token is saved in oidc_client state)
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

@bp.route('/owner-revoke', methods=['GET']) # hmmm GET?
def owner_revoke():
    with authenticated_user() as user:
        #try:
            client = OAuth2Client.query.filter_by(client_id=request.args['client_id']).one()
            tty = TTY.query.get(request.args['tty_id'])
            permission.ToInteract(client,tty).revoke_by(user)
            return redirect(url_for('.home'))
        # except:
        #     return 400


@bp.route('/api/me')
@require_oauth('profile')
def api_me():
    user = current_token.user
    return jsonify(id=user.id, username=user.username)
