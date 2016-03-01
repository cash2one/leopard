import inspect
import random
import string
import pkgutil

from flask import Blueprint, Flask
from flask.ext.admin import Admin
from flask.ext.admin.contrib.sqla import ModelView
from flask.ext.restful import Api, Resource


VIEWS_MODULE_NAME = 'views'


def gen_random_str(length):
    chars = string.ascii_letters + string.digits
    return ''.join([random.choice(chars) for i in range(length)])


def register_resources(api, resources):
    for resource in resources:
        api.add_resource(resource, *resource.urls,
                         endpoint=getattr(resource, 'endpoint',
                                          resource.__name__.lower()))


def register_module_services(app, import_name):
    module = pkgutil.importlib.import_module(import_name)
    blueprint, api, resources = None, None, []
    for item_name in dir(module):
        item = getattr(module, item_name)
        if isinstance(item, Blueprint):
            blueprint = item
        elif isinstance(item, Api):
            api = item
        elif (inspect.isclass(item) and issubclass(item, Resource)
              and hasattr(item, 'urls')):
            resources.append(item)
    if blueprint:
        register_resources(api or Api(blueprint), resources)
        app.register_blueprint(blueprint)


def register_path_services(app, import_name, import_path):
    for _, name, _ in pkgutil.iter_modules(import_path):
        module_package = import_name + '.' + name
        register_module_services(app, module_package)


def register_applications(import_name, import_path):
    applications = {}
    for _, name, _ in pkgutil.iter_modules(import_path):
        module_package = import_name + '.' + name
        module = pkgutil.importlib.import_module(module_package)
        for item_name in dir(module):
            item = getattr(module, item_name)
            if isinstance(item, Flask):
                register_blueprints(item, module_package)
                applications[module_package] = item
            elif isinstance(item, Admin):
                register_admin_views(item, module_package)
    return applications


def register_blueprints(app, import_name):
    module_package = import_name + '.' + VIEWS_MODULE_NAME
    module = pkgutil.importlib.import_module(module_package)
    for item_name in dir(module):
        item = getattr(module, item_name)
        if isinstance(item, Blueprint):
            app.register_blueprint(item)


def register_admin_views(admin, import_name):
    from leopard.core.orm import db_session
    from leopard.comps.admin import BaseView

    module_package = import_name + '.' + VIEWS_MODULE_NAME
    module = pkgutil.importlib.import_module(module_package)
    view_classes = []
    for item_name in dir(module):
        item = getattr(module, item_name)
        if (inspect.isclass(item) and issubclass(item, (BaseView, ModelView))
           and hasattr(item, 'constructor')):
            view_classes.append(item)
    for view_class in sorted(
        view_classes, key=lambda e: e.constructor.get('order', float('inf'))
    ):
        constructor = getattr(view_class, 'constructor')
        constructor.pop('order', None)
        if issubclass(view_class, ModelView) and 'session' not in constructor:
            constructor.update(session=db_session)
        view = view_class(**constructor)
        admin.add_view(view)


def register_services(app, service_import_name, service_import_path):
    register_path_services(app, service_import_name, service_import_path)
