from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from config import Config
from .models import db


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class())

    # Behind nginx at a subpath (/timetables): honour X-Forwarded-* headers,
    # including X-Forwarded-Prefix, so url_for() builds correct links.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    db.init_app(app)

    from . import auth, routes
    app.register_blueprint(auth.bp)
    app.register_blueprint(routes.bp)

    with app.app_context():
        db.create_all()

    return app
