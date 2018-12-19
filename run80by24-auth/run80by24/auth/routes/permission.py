from flask import Blueprint, request, jsonify
from ..models import db, User, TTY
from ..oauth_models import OAuth2Client
from .. import permission
from .authc import authenticated_user

bp = Blueprint('permission', __name__, url_prefix='/permission')

@bp.route('/interact', methods=['DELETE'])
def revoke_interact():
    with authenticated_user() as user:
        client = OAuth2Client.query.filter_by(client_id=request.args['client_id']).one()
        tty = TTY.query.get(request.args['tty_id'])
        try:
            permission.ToInteract(client, tty).revoke_by(user)
        except permission.NotPermittedException:
            return '', 403
        return '', 200
