from flask import Flask

from .orm import register_shutdown_handler


def create_app(import_name, **kwargs):
    app = Flask(import_name, **kwargs)

    register_shutdown_handler(app)

    return app
