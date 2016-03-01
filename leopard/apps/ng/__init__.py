from leopard.core import factory
from leopard.core.config import get_config


def create_app(import_name):
    app = factory.create_app(import_name)

    app.config.update(get_config(import_name))

    return app

app = create_app(__name__)
