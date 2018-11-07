from flask import Blueprint, request, session, g
from flask import render_template, redirect, jsonify, url_for
from authlib.flask.oauth2 import current_token
from authlib.specs.rfc6749 import OAuth2Error
from authlib.client.errors import OAuthException
from ..models import db, User, TTY, MayInteract
from ..auth_server import auth_server, require_oauth
from ..federation import federation
from urllib.parse import quote_plus
from .. import permission
from .authc import current_user, authenticated_user, NotAuthenticatedException

bp = Blueprint('oauth2', __name__)

def remember_own_flow_args():
    own_flow_args = {}
    for arg in ('scope','client_id','state','nonce','response_type','redirect_uri'):
        if request.args.get(arg):
            own_flow_args[arg] = request.args[arg] # or encode it in state?
    session['own_flow_args'] = own_flow_args

def recall_own_flow_args():
    return session.pop('own_flow_args',None)

@bp.route('/authorize', methods=['GET', 'POST'])
def authorize():
    user = current_user()
    if not user:
        remember_own_flow_args()
        raise NotAuthenticatedException(redirect=True)
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
        return redirect(url_for('oauth2.authorize')+'?'+qp)
    else:
        return redirect(url_for('home.create_client'))

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
