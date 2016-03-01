from flask.ext.restful.reqparse import Argument
from flask.ext.restful.inputs import boolean

session = [
    Argument('username', type=str, required=True),
    Argument('password', type=str, required=True),
    Argument('identifying_code', type=str, default=''),
    Argument('cb', type=str, required=False)
]

auto_investment = [
    Argument('is_open', type=boolean, required=True),
    Argument('min_rate', type=float, required=True),
    Argument('max_rate', type=float, required=True),
    Argument('min_periods', type=int, required=True),
    Argument('max_periods', type=int, required=True),
    Argument('min_amount', type=float, required=True),
    Argument('max_amount', type=float, required=True),
    Argument('reserve_amount', type=float, required=True),
    Argument('trade_password', type=str, required=True)
]

user_create = [
    Argument('username', type=str, required=True),
    Argument('password', type=str, required=True),
    Argument('email', type=str, default=''),
    Argument('phone', type=str, required=True),
    Argument('phone_code', type=str, default=''),
    Argument('identifying_code', type=str, default=''),
    Argument('friend_invitation', type=str, default=''),
    Argument('invite_code', type=str, default=''),
    Argument('urlparams', type=str, default='')
]

register_phone_code = [
    Argument('phone', type=str, required=True)
]

retrieve_password_phone_code = [
    Argument('user_info', type=str, required=True)
]

phoneauth_code = [
    Argument('phone', type=str, required=True)
]

user_profile_update = [
    Argument('address', type=str, required=True),
    Argument('age', type=int, required=True),
    Argument('sex', type=str, required=True),
    Argument('education', type=str, required=True),
    Argument('marital_status', type=str, required=True)
]

user_password = [
    Argument('oldpassword', type=str, required=True),
    Argument('newpassword', type=str, required=True),
]

password_phone_code = [
    Argument('user_info', type=str, required=True)
]

resetter_password = [
    Argument('user_info', type=str, required=True),
    Argument('phone_code', type=str, required=True),
    Argument('password', type=str, required=True)
]

user_set_trade_password = [
    Argument('password', type=str, required=True),
]

user_change_trade_password = [
    Argument('newpassword', type=str, required=True),
    Argument('phone_code', type=str, default='')
]

change_phone_put = [
    Argument('current_phone_code', type=str, required=True),
    Argument('phone', type=str, required=True),
    Argument('change_phone_code', type=str, required=True)
]

vip_server = [
    Argument('id', type=int, required=True)
]

activation = [
    Argument('serial', type=str, required=True)
]

duplicated_user = [
    Argument('username', type=str),
    Argument('email', type=str),
]

avatar = [
    Argument('left', type=int, required=True),
    Argument('upper', type=int, required=True),
    Argument('right', type=int, required=True),
    Argument('lower', type=int, required=True),
    Argument('avatar', type=str, required=True)
]

identifying_code = [
    Argument('type', type=str, required=True)
]

post = [
    Argument('title', type=str, required=True),
    Argument('type', type=int, required=True),
    Argument('content', type=str, required=True)
]

ip_info = [
    Argument('ip', type=str, required=True)
]

project = [
    Argument('name', type=str, required=True),
    Argument('amount', type=float, required=True),
    Argument('rate', type=float, required=True),
    Argument('periods', type=int, required=True),
]

prepayment_put = [
    Argument('trade_password', type=str, required=True),
    Argument('amount', type=float, default=0.0),
    Argument('periods', type=int, default=0)
]

investment_transfer_post = [
    Argument('trade_password', type=str, required=True),
    Argument('pay_amount', type=float, default=0),
]

investment_transfer_put = [
    Argument('trade_password', type=str, required=True),
    Argument('capital_deduct_order', type=int, default=0)
]

public_project = [
    Argument('amount', type=float, required=True),
    Argument('trade_password', type=str, required=True),
    Argument('password', type=str, default=''),
    Argument('phone_code', type=str, default=''),
    Argument('capital_deduct_order', type=int, default=0),
    Argument('redpacket_id', type=int, required=False)
]

message = [
    Argument('title', type=str, required=True),
    Argument('content', type=str, required=True),
    Argument('to_user', type=str, required=True)
]

deposit = [
    Argument('amount', type=float, required=True),
    Argument('platform', type=int, required=True),
    Argument('bankcard_id', type=int, default=0),
    Argument('comment', type=str, default='')
]

withdraw = [
    Argument('amount', type=float, required=True),
    Argument('trade_password', type=str, required=True),
    Argument('phone_code', type=str, default=''),
    Argument('capital_deduct_order', type=int, default=0),
    Argument('bankcard_id', type=int, default=0)
]

application = [
    Argument('name', type=str, required=True),
    Argument('amount', type=int, required=True),
    Argument('repaymentmethod_id', type=int, required=True),
    Argument('guarantee_id', type=int, required=True),
    Argument('rate', type=float, required=True),
    Argument('nper_type', type=int, required=False),
    Argument('periods', type=int, required=True),
    Argument('description', type=str, required=True)
]

finapplication = [
    Argument('amount', type=str, required=True),
    Argument('periods', type=int, required=True),
    Argument('loan_use_for', type=str, required=True)
]

fin_mobile_application = {
    Argument('name', type=str, required=True),
    Argument('idcard', type=str, required=True),
    Argument('phone', type=str, required=True),
    Argument('school', type=str, required=True),
    Argument('grade', type=str, required=True),
    Argument('amount', type=float, required=True),
    Argument('term', type=str, required=True)
}

bankcard = [
    Argument('name', type=str, required=True),
    Argument('branch', type=str, required=True),
    Argument('card', type=str, required=True)
]

bankcard_delete = [
    Argument('trade_password', type=str, required=True),
    Argument('platform_type', type=str)
]

phone_auth = [
    Argument('code', type=str, required=True)
]

pagination = [
    Argument('offset', type=int, default=0),
    Argument('limit', type=int, default=25)
]

filtering = [
    Argument('filter', type=str, default='{}')
]

sorting = [
    Argument('sort', type=str, default='')
]

only_trade_password = [
    Argument('trade_password', type=str, required=True),
]

code_red_packet = [
    Argument('code', type=str, required=True)
]

commodity_order = [
    Argument('buy_number', type=int, required=True),
    Argument('trade_password', type=str, required=True),
    Argument('addressee', type=str),
    Argument('address', type=str),
    Argument('phone', type=str),
    Argument('description', type=str)
]
