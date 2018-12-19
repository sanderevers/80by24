from flask import Blueprint, request, render_template, redirect, url_for
from werkzeug.security import gen_salt
from ..models import db, TTY, MayInteract
from ..oauth_models import OAuth2Client
from .. import permission
from .authc import current_user, authenticated_user
from collections import defaultdict

bp = Blueprint('home', __name__)

@bp.route('/')
def home():
    user = current_user()
    if user:
        ttys = TTY.query.filter_by(owner=user).all()
        mis = defaultdict(list)
        for mi in MayInteract.query.filter(MayInteract.tty_id.in_([tty.id for tty in ttys])).all():
            mis[mi.tty_id].append(mi.export())
        ttys_json = []
        for tty in ttys:
            exp = tty.export()
            exp['grants'] = mis[tty.id]
            ttys_json.append(exp)
    else:
        clients_json = []
        ttys_json = []
    return render_template('ttys.html', user=user, ttys=ttys_json)

@bp.route('/dev')
def dev():
    with authenticated_user(redirect=True) as user:
        clients = OAuth2Client.query.filter_by(user_id=user.id).all()
        clients_json = [c.export() for c in clients]
        return render_template('clients.html', user=user, clients=clients_json)


# @bp.route('/create_client', methods=('GET', 'POST'))
# def create_client():
#     with authenticated_user(redirect=True) as user:
#         if request.method == 'GET':
#             return render_template('create_client.html')
#
#         client = OAuth2Client(**request.form.to_dict(flat=True))
#         client.user_id = user.id
#         client.client_id = gen_salt(24)
#         if client.token_endpoint_auth_method == 'none':
#             client.client_secret = ''
#         else:
#             client.client_secret = gen_salt(48)
#         db.session.add(client)
#         db.session.commit()
#         return redirect('/')








