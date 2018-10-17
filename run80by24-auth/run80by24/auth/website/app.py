import os
from flask import Flask
from .models import db
from .auth_server import config_oauth
from .routes import bp
from .federation import federation

def create_app(instance_path):
    app = Flask(__name__, instance_path=instance_path, instance_relative_config=True)

    # load default configuration
    app.config.from_object('run80by24.auth.website.settings')

    # load environment configuration
    if 'WEBSITE_CONF' in os.environ:
        app.config.from_envvar('WEBSITE_CONF')

    app.config.from_pyfile('run80by24-auth.cfg') # in instance dir

    setup_app(app)
    return app


def setup_app(app):
    if app.config.get('SQLALCHEMY_DATABASE_URI_TEMPLATE'):
        app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI_TEMPLATE'].format(app.instance_path)
    db.init_app(app)
    federation.init_app(app)
    config_oauth(app)
    app.register_blueprint(bp, url_prefix='')
