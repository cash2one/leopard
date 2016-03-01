import re
from sqlalchemy.sql import exists

from flask.ext.restful import abort

from leopard.orm import User
from leopard.helpers import get_current_user, get_parser
from leopard.core.orm import db_session


def trade_password():
    user = get_current_user()
    if not user.trade_password:
        abort(400, message='请先设置交易密码')
    return user.phone


def withdraw():
    user = get_current_user()
    if len(user.bankcards) == 0:
        abort(400, message='请先设置提现银行卡')
    return user.phone


def current_phone():
    user = get_current_user()
    return user.phone


def email_change():
    user = get_current_user()
    return user.phone


def change_phone():
    args = get_parser('register_phone_code').parse_args()

    if not re.match('^\d{11}$', args['phone']):
        abort(400, message='手机号码格式错误!')

    user = get_current_user()
    if user.phone == args['phone'] and args['phone'] != '18653199812':
        abort(400, message='新号码不能与原号码相同!')

    registered = db_session.query(
        exists().where(User.phone == args['phone'])
    ).scalar()

    if registered and args['phone'] != '18653199812':
        abort(400, message='此手机号已注册，如有疑问请咨询在线客服!')

    return args['phone']


def password():
    args = get_parser('password_phone_code').parse_args()
    user_info = args['user_info']
    if re.match('^[1][1-9][\d]{9}$', user_info):
        user = User.query.filter(User.phone == user_info).first()
    else:
        user = User.query.filter(User.username == user_info).first()
    if not user:
        abort(400, message='不存在的用户')
    return user.phone


def register():
    args = get_parser('register_phone_code').parse_args()

    if not re.match('^\d{11}$', args['phone']):
        abort(400, message='手机号码格式错误。')

    registered = db_session.query(
        exists().where(User.phone == args['phone'])
    ).scalar()

    if registered and args['phone'] != '18653199812':
        abort(400, message='此手机号已注册，如有疑问请咨询在线客服!')

    return args['phone']


def retrieve_password():
    data = get_parser('retrieve_password_phone_code').parse_args()

    user = User.query.filter_by(username=data['user_info']).first()

    if not user:
        abort(400, message='用户不存在!')

    return user.phone
