from datetime import timedelta

from flask.ext.cors import CORS

from leopard.core import factory
from leopard.core.config import get_config

from leopard.comps.redis import RedisSessionInterface
from leopard.comps.celery import make_celery


def create_app(import_name):
    app = factory.create_app(import_name)

    app.config.update(get_config(import_name))
    app.session_interface = RedisSessionInterface()
    app.permanent_session_lifetime = timedelta(minutes=10)
    return app

app = create_app(__name__)
cors = CORS(app, allow_headers=['Content-Type', 'Platform', 'Authorization',
            'withCredentials'],
            expose_headers=['Page-total', 'Page-current'],
            supports_credentials=True)
celery = make_celery(app)
