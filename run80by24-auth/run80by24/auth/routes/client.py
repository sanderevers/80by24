from flask import Blueprint, request, jsonify
from ..models import db, User
from ..oauth_models import OAuth2Client
from .. import permission
from .authc import authenticated_user

bp = Blueprint('client', __name__, url_prefix='/client')

@bp.route('/', methods=['POST'])
def create():
    with authenticated_user() as user:
        req_client = request.json
        req_client['user_id']= user.id
        client = OAuth2Client.emport(req_client)
        db.session.add(client)
        db.session.commit()
        return jsonify(client.export()), 201

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

