from flask import Blueprint, request, render_template, redirect, url_for
from werkzeug.security import gen_salt
from ..models import db, TTY, MayInteract
from ..oauth_models import OAuth2Client
from .. import permission
from .authc import current_user, authenticated_user

bp = Blueprint('home', __name__)

@bp.route('/')
def home():
    user = current_user()
    if user:
        clients = OAuth2Client.query.filter_by(user_id=user.id).all()
        clients_json = [c.export() for c in clients]
        ttys = TTY.query.filter_by(owner=user).all()
        grants = MayInteract.query.filter(MayInteract.tty_id.in_([tty.id for tty in ttys])).all()
    else:
        clients_json = []
        ttys = []
        grants = []
    return render_template('clients.html', user=user, clients=clients_json, ttys=ttys, grants=grants)


@bp.route('/create_client', methods=('GET', 'POST'))
def create_client():
    with authenticated_user(redirect=True) as user:
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


