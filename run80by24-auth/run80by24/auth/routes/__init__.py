from . import home, oauth2, tty, authc

def config_routes(app):
    app.register_blueprint(home.bp)
    app.register_blueprint(authc.bp)
    app.register_blueprint(oauth2.bp)
    app.register_blueprint(tty.bp)
    app.register_error_handler(authc.NotAuthenticatedException, authc.handle_notauthenticated)