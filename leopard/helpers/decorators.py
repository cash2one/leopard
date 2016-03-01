from functools import wraps

from flask import g, session
from flask.ext.restful import abort

from leopard.apps.service import app
from leopard.helpers import get_current_user


@app.after_request
def call_after_request_callbacks(response):
    for callback in getattr(g, 'after_request_callbacks', ()):
        response = callback(response)

    from leopard.core.middlewares import register_middlewares
    for middleware in register_middlewares:
        response = middleware(response)
    return response


def after_current_request(func):
    if not hasattr(g, 'after_request_callbacks'):
        g.after_request_callbacks = []
    g.after_request_callbacks.append(func)
    return func


def authenticate(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not getattr(func, 'authenticated', True):
            return func(*args, **kwargs)

        user = get_current_user()
        if not user:
            abort(403, message='请先登录!')
        if user.is_bane:
            session.pop('user_id', None)
            abort(403, message='账号已被冻结')
        return func(*args, **kwargs)
    return wrapper
