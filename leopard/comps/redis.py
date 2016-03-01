import pickle

from datetime import timedelta
from uuid import uuid4
from redis import Redis, ConnectionPool
from flask import flash
from flask.sessions import SessionInterface, SessionMixin
from werkzeug.datastructures import CallbackDict


pool = ConnectionPool()
redis = Redis(connection_pool=pool)


def get_redis():
    return Redis(connection_pool=pool)


def cache(key=None, expire=None):
    def wrapper(func):
        name = key if key else func.__name__

        def _wrapper(*args, **kwargs):
            value = redis.get(name)
            if not value:
                value = func(*args, **kwargs)
                redis.set(name, value, expire)
            return value
        return _wrapper
    return wrapper


def redis_repeat_submit_by_admin_action():
    def wrapper(func):
        repeat_name = "repeat_submit:{}".format(func.__name__)

        def _wrapper(*args, **kwargs):
            if redis.get(repeat_name):
                flash('请不要重复提交', 'failed')
            else:
                redis.set(repeat_name, '1', 60)
                func(*args, **kwargs)
                redis.delete(repeat_name)
        return _wrapper
    return wrapper


class RedisSession(CallbackDict, SessionMixin):

    def __init__(self, initial=None, sid=None, new=False):
        def on_update(self):
            self.modified = True
        CallbackDict.__init__(self, initial, on_update)
        self.sid = sid
        self.new = new
        self.modified = False


class RedisSessionInterface(SessionInterface):
    serializer = pickle
    session_class = RedisSession

    def __init__(self, redis=None, prefix='session:'):
        if not redis:
            redis = Redis(connection_pool=pool)
        self.redis = redis
        self.prefix = prefix

    def generate_sid(self):
        return str(uuid4())

    def get_redis_expiration_time(self, app, session):
        if session.permanent:
            return app.permanent_session_lifetime
        return timedelta(days=1)

    def open_session(self, app, request):
        sid = request.cookies.get(app.session_cookie_name)
        if not sid:
            sid = self.generate_sid()
            return self.session_class(sid=sid, new=True)
        val = self.redis.get(self.prefix + sid)
        if val:
            data = self.serializer.loads(val)
            return self.session_class(data, sid=sid)
        return self.session_class(sid=sid, new=True)

    def save_session(self, app, session, response):
        domain = self.get_cookie_domain(app)
        if not session:
            self.redis.delete(self.prefix + session.sid)
            if session.modified:
                response.delete_cookie(app.session_cookie_name,
                                       domain=domain)
            return
        redis_exp = self.get_redis_expiration_time(app, session)
        cookie_exp = self.get_expiration_time(app, session)
        val = self.serializer.dumps(dict(session))
        self.redis.setex(self.prefix + session.sid, val,
                         int(redis_exp.total_seconds()))
        response.set_cookie(app.session_cookie_name, session.sid,
                            expires=cookie_exp, httponly=True,
                            domain=domain)
