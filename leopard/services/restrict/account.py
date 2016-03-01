import math
import logging
import datetime

from redis import Redis
from decimal import Decimal
from sqlalchemy.sql import func
from flask.ext.restful import abort

from leopard.orm import (Config, Withdraw, Log, Bankcard)
from leopard.core.orm import db_session
from leopard.core.config import get_config
from leopard.comps.redis import pool
from leopard.helpers import generate_order_withdraw, float_quantize_by_two

redis = Redis(connection_pool=pool)
logger = logging.getLogger('rotate')
project_config = get_config('project')


def check_withdraw_post_vaild(user, args):
    if not user.trade_password:
        abort(400, message='请先设置交易密码')
    if not user.bankcards:
        abort(400, message='请先添加银行卡')
    if not user.check_trade_password(args['trade_password']):
        abort(400, message='交易密码错误')
    if args['amount'] > user.available_amount:
        abort(400, message='对不起，您的余额不足')
    if args['amount'] > Config.get_float('WITHDRAW_ONCE_AMOUNT_LIMIT'):
        abort(400, message='您申请的金额超过单笔限额')

    total_amount = user.repaying_amount + user.available_amount
    amount = total_amount - user.experience_amount
    if amount < args['amount']:
        abort(400, message='您申请的金额包括注册体验金')


def check_withdraw_post(args, user):
    if Config.get_bool('WITHDRAW_PHONE_CODE_ENABLE'):
        withdraw_code = redis.get('withdraw_phone_code:%s' % user.phone)
        if not withdraw_code or \
                not args['phone_code'] == withdraw_code.decode():
            abort(400, message='验证码错误')

    check_withdraw_post_vaild(user, args)

    now = datetime.datetime.now()
    tomorrow = datetime.datetime(
        now.year, now.month, now.day) + datetime.timedelta(days=1)
    yestody = datetime.datetime(now.year, now.month, now.day)
    apply_withdraw_sum, = db_session.query(
        func.sum(Withdraw.amount + Withdraw.commission)).filter(
        Withdraw.user_id == user.id, Withdraw.added_at < tomorrow,
        Withdraw.added_at > yestody).first()
    apply_withdraw_sum = Decimal(apply_withdraw_sum) \
        if apply_withdraw_sum else 0

    if apply_withdraw_sum >= Config.get_decimal('WITHDRAW_DAYLI_AMOUNT_LIMIT'):
        abort(400, message='您已经达到每日提现金额上限了')
    remaing_withdraw_amount = Config.get_decimal(
        'WITHDRAW_DAYLI_AMOUNT_LIMIT') - apply_withdraw_sum
    if args['amount'] > remaing_withdraw_amount:
        abort(400, message='您今日剩余提现金额为{}元'.format(remaing_withdraw_amount))

    apply_withdraw_count, = db_session.query(
        func.count(Withdraw.id)).filter(
        Withdraw.user_id == user.id, Withdraw.added_at < tomorrow,
        Withdraw.added_at > yestody).first()
    if apply_withdraw_count >= Config.get_int('WITHDRAW_DAYLI_TIME_LIMIT'):
        abort(400, message='您已经达到每日提现次数上限了')


def withdraw_commission(amount):
    commission = 0
    fixed = Config.get_decimal('COMMISSION_WITHDRAW_FIXED')
    rate = Config.get_decimal('COMMISSION_WITHDRAW_RATE') / 100
    if project_config['PLATFORM'] == 'yjd':
        commission = fixed * math.ceil(amount / 200000)
    else:
        commission = rate * amount + fixed
    return commission


def withdraw_post(args, user):
    bankcard = Bankcard.query.filter(
        Bankcard.user_id == user.id,
        Bankcard.id == args['bankcard_id']).first()
    if not bankcard:
        return 400, '银行卡不存在'

    amount = Decimal(str(args['amount']))


    allow_amount = user.available_amount - user.bankcard_need_amount + bankcard.need_amount
    if allow_amount < amount:
        return 400, '本卡可提现额度%s'%(allow_amount)

    commission = withdraw_commission(amount)

    active_amount = user.active_amount
    deposit_amount = user.deposit_amount
    income_amount = user.income_amount

    withdraw = Withdraw()
    withdraw.order_number = generate_order_withdraw()
    withdraw.amount = amount - commission
    withdraw.commission = commission
    withdraw.user = user
    withdraw.description = "{} - {}".format(
        bankcard.bank.replace(':', ' - '), bankcard.card)

    user.capital_blocked(amount, args['capital_deduct_order'])

    #  提现卡金额调整
    if bankcard.need_amount > amount:
        bankcard.need_amount -= amount
        redis.set('withdraw:{}:bankcard_id'.format(
            withdraw.order_number), bankcard.id)
        redis.set('withdraw:{}:need_amount'.format(
            withdraw.order_number), amount)
    elif bankcard.need_amount > Decimal('0.0'):
        redis.set('withdraw:{}:bankcard_id'.format(
            withdraw.order_number), bankcard.id)
        redis.set('withdraw:{}:need_amount'.format(
            withdraw.order_number), bankcard.need_amount)
        bankcard.need_amount = Decimal('0.0')

    redis.set('withdraw:{}:active_amount'.format(
        withdraw.order_number), active_amount - user.active_amount)
    redis.set('withdraw:{}:deposit_amount'.format(
        withdraw.order_number), deposit_amount - user.deposit_amount)
    redis.set('withdraw:{}:income_amount'.format(
        withdraw.order_number), income_amount - user.income_amount)

    fundstr = '[申请提现] 订单号:{order_number}, 冻结金额:{amount}'
    description = fundstr.format(
        order_number=withdraw.order_number, amount=amount)
    Log.create_log(withdraw, amount=amount, description=description)

    if Config.get_bool('WITHDRAW_PHONE_CODE_ENABLE'):
        redis.delete('withdraw_phone_code:' + user.phone)
    db_session.commit()

    logstr = '[Withdraw Post Success] User(id: {}): {}, Withdraw: {}, \
              amount: {}, commission: {}'
    logger.info(logstr.format(user.id, user, withdraw.id, withdraw.amount,
                withdraw.commission))

    return 200, None


def deduct_experience_amount(investment, amount):
    """ 注册体验金收回 """
    balance_amount = amount
    exp_amount = investment.user.experience_amount
    if exp_amount > 0:
        user = investment.user

        dif_amount = amount - exp_amount
        balance_amount = 0 if dif_amount < 0 else dif_amount
        user.experience_amount -= amount if dif_amount < 0 else exp_amount
        back_amount = amount if dif_amount < 0 else exp_amount

        info = ('[注册体验金-收回] 项目:«{pname}» id:{pid}, 还款本金: {amount}, '
                '操作前体验金:{exp_amount}元, 操作后体验金:{now_exp_amount}, '
                '收回:{back_amount}, 剩余可得:{balance_amount}')
        desc = info.format(
            pname=investment.project.name,
            pid=investment.project.id,
            back_amount=float_quantize_by_two(back_amount),
            balance_amount=float_quantize_by_two(balance_amount),
            amount=float_quantize_by_two(amount),
            exp_amount=float_quantize_by_two(exp_amount),
            now_exp_amount=float_quantize_by_two(user.experience_amount)
        )
        Log.create_log(investment,
                       amount=float_quantize_by_two(back_amount),
                       description=desc)

        logger.info(desc)

    return balance_amount
