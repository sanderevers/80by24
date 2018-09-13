from flask import Blueprint, request, session, g
from flask import render_template, redirect, jsonify, url_for
from werkzeug.security import gen_salt
from authlib.flask.oauth2 import current_token
from authlib.specs.rfc6749 import OAuth2Error
from authlib.client.errors import OAuthException
from .models import db, User, OAuth2Client
from .auth_server import auth_server, require_oauth
from .federation import federation
from urllib.parse import quote_plus
from copy import copy

bp = Blueprint(__name__, 'home')


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


@bp.route('/create_client', methods=('GET', 'POST'))
def create_client():
    user = current_user()
    if not user:
        return authenticate_user()

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


@bp.route('/authorize', methods=['GET', 'POST'])
def authorize():
    user = current_user()
    if not user:
        remember_own_flow_args()
        return authenticate_user()

    if request.method == 'GET':
        try:
            grant = auth_server.validate_consent_request(end_user=user)
        except OAuth2Error as error:
            return error.error
        return render_template('authorize.html', user=user, grant=grant)

    if request.form['confirm']:
        grant_user = user
    else:
        grant_user = None
    return auth_server.create_authorization_response(grant_user=grant_user)

def authenticate_user():
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


@bp.route('/token', methods=['POST'])
def issue_token():
    print(request.form)
    return auth_server.create_token_response()


@bp.route('/revoke', methods=['POST'])
def revoke_token():
    return auth_server.create_endpoint_response('revocation')


@bp.route('/api/me')
@require_oauth('profile')
def api_me():
    user = current_token.user
    return jsonify(id=user.id, username=user.username)
