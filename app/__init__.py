from flask import Flask

from config import Config
from .models import db


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class())

    db.init_app(app)

    from . import auth, routes
    app.register_blueprint(auth.bp)
    app.register_blueprint(routes.bp)

    with app.app_context():
        db.create_all()

    return app
