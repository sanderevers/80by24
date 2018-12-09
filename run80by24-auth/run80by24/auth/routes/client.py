from flask import Blueprint, request, jsonify
from werkzeug.security import gen_salt
from ..models import db, User
from ..oauth_models import OAuth2Client
from .. import permission
from .authc import authenticated_user

bp = Blueprint('client', __name__, url_prefix='/client')

@bp.route('/', methods=['POST'])
def create():
    with authenticated_user() as user:
        req_client = request.json
        flow = req_client.pop('flow')
        client = OAuth2Client(**req_client)
        client.user_id = user.id
        client.client_id = gen_salt(24)
        if flow=='code':
            client.grant_type = 'authorization_code'
            client.response_type = 'code'
            client.token_endpoint_auth_method = 'client_secret_basic'
            client.client_secret = gen_salt(48)
        else:
            client.grant_type = 'implicit'
            client.response_type = 'token'
            client.token_endpoint_auth_method = 'none'
            client.client_secret = ''
        db.session.add(client)
        db.session.commit()
        return jsonify(client.client_info), 201

@bp.route('/<client_id>', methods=['DELETE'])
def delete(client_id):
    with authenticated_user() as user:
        client = OAuth2Client.query.filter_by(client_id=client_id).first()
        if client and permission.Owner(user,client).test():
            db.session.delete(client)
            db.session.commit()
            return '', 200
        else:
            return '', 403

