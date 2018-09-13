import os
from flask import Flask
from .models import db
from .auth_server import config_oauth
from .routes import bp
from .federation import federation

def create_app(config=None):
    app = Flask(__name__, instance_relative_config=True)

    # load default configuration
    app.config.from_object('website.settings')

    # load environment configuration
    if 'WEBSITE_CONF' in os.environ:
        app.config.from_envvar('WEBSITE_CONF')

    # load app sepcified configuration
    if config is not None:
        if isinstance(config, dict):
            app.config.update(config)
        elif config.endswith('.py') or config.endswith('.cfg'):
            app.config.from_pyfile(config)

    setup_app(app)
    return app


def setup_app(app):
    if app.config.get('SQLALCHEMY_DATABASE_URI_TEMPLATE'):
        app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI_TEMPLATE'].format(app.instance_path)
    db.init_app(app)
    federation.init_app(app)
    config_oauth(app)
    app.register_blueprint(bp, url_prefix='')
