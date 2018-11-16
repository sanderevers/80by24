import os
from flask import Flask
from .models import db
from .auth_server import config_oauth
from .routes import config_routes
from .federation import federation

def create_app():
    instance_path = os.environ.get('INSTANCE_PATH')
    app = Flask('run80by24.auth', instance_path=instance_path, instance_relative_config=True)
    app.config.from_pyfile('config.py') # in instance dir
    setup_app(app)
    return app


def setup_app(app):
    if app.config.get('SQLALCHEMY_DATABASE_URI_TEMPLATE'):
        app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI_TEMPLATE'].format(app.instance_path)
    db.init_app(app)
    federation.init_app(app)
    config_oauth(app)
    config_routes(app)

