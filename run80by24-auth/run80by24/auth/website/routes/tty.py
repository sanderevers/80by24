from flask import Blueprint
from ..models import db, User, TTY, MayInteract
from .. import permission
from .authc import authenticated_user

bp = Blueprint('tty', __name__, url_prefix='/tty')

@bp.route('/<tty_id>', methods=['POST'])
def claim(tty_id):
    with authenticated_user() as user:
        tty = TTY.query.get(tty_id)
        if not tty:
            tty = TTY(id=tty_id)
            permission.Owner(user,tty).grant_by('80by24')
            return '', 201
        if permission.Owner(user,tty).test():
            return '', 200
        else:
            return '', 403

@bp.route('/<tty_id>', methods=['DELETE'])
def release(tty_id):
    with authenticated_user() as user:
        tty = TTY.query.get(tty_id)
        if tty and permission.Owner(user,tty).test():
            mis = MayInteract.query.filter_by(tty=tty).all()
            for mi in mis:
                permission.ToInteract(mi.client, mi.tty).revoke_by(user)
            permission.Owner(user,tty).revoke_by('80by24')
            return '', 200
        else:
            return '', 403

