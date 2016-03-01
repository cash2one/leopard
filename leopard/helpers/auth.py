# flake8: noqa
import base64
import random
import datetime

from flask import session, request
from flask.ext.restful import abort

from itsdangerous import Signer, TimestampSigner

from leopard.conf import consts
from leopard.core.config import get_config
from leopard.comps.redis import get_redis


project_config = get_config('project')
service_config = get_config('leopard.apps.service')
redis = get_redis()


def get_user_username(username, password):
    from leopard.orm import User

    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        return user
    return None


def validate_admin_user(username):
    from leopard.orm import User

    return User.query.filter_by(username=username).first()


def get_user_phone(phone, password):
    from leopard.orm import User

    user = User.query.filter_by(phone=phone).first()
    if user and user.check_password(password):
        return user
    return None


def get_current_user():
    from leopard.orm import User

    user_id = get_current_user_id()
    if user_id:
        return User.query.get(user_id)
    return None


def get_current_user_id():
    platfrom = request.headers.get('Platform')

    if platfrom in project_config['BEARER_TOKEN_PLATFORM']:
        token = request.headers.get('Authorization', 'Bearer').split()[-1]
        user_id = redis.get(consts.BEARER_TOKEN.format(token))
        if user_id:
            user_id = user_id.decode()
        else:
            user_id = ''
        token_cached = redis.get(consts.BEARER_TOKEN_ID.format(user_id))
        if token_cached and token == token_cached.decode():
            return user_id
    else:
        if 'user_id' in session:
            return session['user_id']

    return None


def assert_current_user(obj, attr='user'):
    current_user = get_current_user()
    if not current_user or (obj is not current_user
                            and getattr(obj, attr, None) is not current_user):
        abort(403, message='无访问权限')


def timestamp_sign(value, secret_key, *, salt=''):
    signer = TimestampSigner(secret_key, salt=salt)
    return signer.sign(value)


def sign(value, secret_key, *, salt=''):
    signer = Signer(secret_key, salt=salt)
    return signer.sign(value)


def generate_and_save_bearer_token(user_id):
    value = "{}:{}".format(
        datetime.datetime.now().strftime("%Y%m%d%H%M%S%s"),
        random.random()
    )
    token = base64.b64encode(value.encode()).decode()[:64]
    redis.set(consts.BEARER_TOKEN.format(token), user_id)
    redis.set(consts.BEARER_TOKEN_ID.format(user_id), token)
    return token


def get_user_realname_and_card(user_id):
    from leopard.orm import (Authentication, AuthenticationFieldType,
                             AuthenticationField)

    realname = AuthenticationField.query.filter(
        Authentication.user_id == user_id,
        AuthenticationField.authentication_id == Authentication.id,
        AuthenticationField.type_id == AuthenticationFieldType.id,
        AuthenticationFieldType.name == "真实姓名"
    ).first()

    idcard = AuthenticationField.query.filter(
        Authentication.user_id == user_id,
        AuthenticationField.authentication_id == Authentication.id,
        AuthenticationField.type_id == AuthenticationFieldType.id,
        AuthenticationFieldType.name == "身份证号码"
    ).first()

    realname_value = None if not realname else realname.value
    idcard_value = None if not idcard else idcard.value
    return realname_value, idcard_value
