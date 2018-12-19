from flask import Blueprint, render_template, jsonify, request
from authlib.flask.oauth2 import current_token
from authlib.specs.rfc6749 import OAuth2Error
from ..models import db, TTY
from ..auth_server import auth_server, require_oauth
from .. import permission
from .authc import authenticated_user

bp = Blueprint('oauth2', __name__)

@bp.route('/authorize', methods=['GET', 'POST'])
def authorize():
    with authenticated_user(redirect=True) as user:
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
        if request.form.get('consent')=='true':
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
