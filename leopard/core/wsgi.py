def dispatch_apps(import_name, import_path):
    from leopard.helpers import register_applications
    from leopard.helpers import get_config

    wsgi_config = get_config(__name__)

    apps = register_applications(import_name, import_path)
    app, mounts = wsgi_config['DISPATCH'].copy().popitem()
    master = apps[app]
    slaves = {v: apps[k] for k, v in mounts.items()}

    from werkzeug.wsgi import DispatcherMiddleware, SharedDataMiddleware
    wsgi = SharedDataMiddleware(DispatcherMiddleware(master, slaves), wsgi_config['SHAREDDATA'])

    return wsgi


def create_wsgi():
    from leopard.core.logging import setup_logging
    setup_logging()

    from leopard.core.orm import create_engine_with_binding
    create_engine_with_binding('database')

    import leopard.apps
    import leopard.apps.service
    import leopard.services

    from leopard.helpers import get_config
    project_config = get_config('project')

    from leopard.helpers import register_services
    register_services(leopard.apps.service.app,
                      leopard.services.__name__,
                      leopard.services.__path__)

    wsgi = dispatch_apps(leopard.apps.__name__, leopard.apps.__path__)
    return wsgi
