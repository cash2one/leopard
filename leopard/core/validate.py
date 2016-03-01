# -*- coding: utf-8 -*-
"""
leopard.core.validate
====================

模块介绍
-----------------------

本模块定义了 投标时候的合法性检查

开发责任人
-----------------------

* mzj@abstack.com

评审责任人
-----------------------

模块成员
-----------------------

"""
import logging
from decimal import Decimal
from leopard.orm import Authentication, AuthenticationType, Config, RedPacket
from leopard.helpers import get_enum
from leopard.helpers.exceptions import TenderCheckException
from leopard.helpers.auth import get_user_realname_and_card

logger = logging.getLogger('tender')


def general_check(user, project, amount, **kwargs):
    """
    :功能描述: 投标常规检查
    :责任人: mzj@abstack.com
    :最后修改时间: 2015-05-26 17:08:26

    :param User user: 当前登录用户实例
    :param Decimal amount: 所投金额
    :param Project project: 当前用户所投标
    :param str password: 定向密码错误
    :param str trade_password: 交易密码
    :param int redpacket_id: 红包id
    """
    session = kwargs.get('session')
    password = kwargs.get('password')
    trade_password = kwargs.get('trade_password')
    redpacket_id = kwargs.get('redpacket_id')

    authenticate = session.query(
        Authentication).join(Authentication.type).filter(
        Authentication.user == user,
        AuthenticationType.logic == 'idcard'
    ).first()

    if not authenticate or not authenticate.status:
        raise TenderCheckException('实名认证后才能投资, 请先认证')

    if Config.get_bool('TRADE_PASSWORD_ENABLE'):
        if not user.trade_password_enable:
            raise TenderCheckException('请先设置交易密码!')
        if not user.check_trade_password(trade_password):
            raise TenderCheckException('错误的交易密码!')

    if project.has_password and not project.password == password:
        raise TenderCheckException('定向密码错误!')

    if user == project.user:
        raise TenderCheckException('投资人不能为项目发起人')

    if project.status != get_enum('PROJECT_INVESTING'):
        raise TenderCheckException('此项目当前不能进行投资')

    if user.available_amount < amount:
        raise TenderCheckException('可用资金不足!')

    if project.category == get_enum('STUDENT_PROJECT'):
        if project.lack_amount > 100 and (amount % 100 > 0 or amount < 100):
            raise TenderCheckException('学仕贷投标100元起，必须是100元的整数倍')

    if redpacket_id:
        redpacket = RedPacket.query.filter_by(id=redpacket_id,
                                              user=user).first()
        if not redpacket:
            raise TenderCheckException('不存在的投资红包!')
        if redpacket.have_expired:
            raise TenderCheckException('投资红包已过期！')
        if redpacket.is_use:
            raise TenderCheckException('投资红包已使用！')

        if redpacket.invest_amount and redpacket.invest_amount > amount:
            raise TenderCheckException('投资金额不满足红包使用金额！')


def check_investment_amount(user, project, amount):
    """
    :功能描述: 投标资金检查
    :责任人: mzj@abstack.com
    :最后修改时间: 2014-10-16 22:56:01

    :param User user: 当前登录用户实例
    :param Decimal amount: 所投金额
    :param Project project: 当前用户所投标
    """
    if project.lack_amount < Decimal('0.01'):
        raise TenderCheckException('项目已经投满')

    if isinstance(amount, str) or amount <= 0:
        raise TenderCheckException('投资金额不合法')

    if user.available_amount == Decimal('0'):
        raise TenderCheckException('用户余额不足')

    if isinstance(amount, float) and len(str(amount).split('.')[-1]) > 2:
        raise TenderCheckException('投资金额不能小于小数点后两位')

    if project.lack_amount <= project.min_lend_amount:
        # 可投金额 小于 最小投资金额
        if amount < project.lack_amount:
            raise TenderCheckException('投资金额太小')
        amount = project.lack_amount
    else:
        if amount < project.min_lend_amount:
            raise TenderCheckException('投资金额太小')
        if amount > project.lack_amount:
            amount = project.lack_amount

    total_amount = user.invested_project_amount(project) + amount
    if total_amount > project.max_lend_amount:
        message = '您投资的金额超出项目最大投资金额, 您还能投资{}元'
        message = message.format(project.max_lend_amount -
                                 user.invested_project_amount(project))
        raise TenderCheckException(message)

    loginfo = ('[投标检查] 用户:<{user}, 可用资金: {available_amount}>;'
               '项目:<{project}, 已借资金:{borrowed_amount}>;'
               '投资:<amount:{amount}, 真实投资:{real_amount} >')

    logger.info(loginfo.format(
        user=user,
        project=project,
        amount=amount,
        real_amount=amount,
        available_amount=user.available_amount,
        borrowed_amount=project.borrowed_amount))

    can_use_expe = True          # 可以使用注册体验金
    if user.experience_amount > 0:
        expe_limit_amount = Config.get_decimal('EXPE_LIMIT_AMOUNT')
        if user.total_deposit < expe_limit_amount:
            if user.income_amount + user.deposit_amount < amount:
                message = '您的充值总额不满足使用注册体验金的要求'
                loginfo = ('[投标检查] 用户:<{user}, 可用资金:{available_amount}>'
                           '充值金额:{deposit_amount} 回款资金:{income_amount};'
                           '项目:<{project}, 已借资金:{borrowed_amount}>;'
                           '投资:<amount:{amount}, 真实投资:{real_amount} >,'
                           '注册体验金限额:{expe_limit_amount}')
                logger.info(loginfo.format(
                    user=user,
                    project=project,
                    amount=amount,
                    deposit_amount=user.deposit_amount,
                    income_amount=user.income_amount,
                    real_amount=amount,
                    available_amount=user.available_amount,
                    borrowed_amount=project.borrowed_amount,
                    expe_limit_amount=expe_limit_amount)
                )
                raise TenderCheckException(message)
            else:
                can_use_expe = False
    return amount, can_use_expe


def exist_realname_auth(user_id):
    """ 是否已存在改该实名认证 """
    from leopard.orm import (Authentication, AuthenticationFieldType,
                             AuthenticationField)
    realname, idcard = get_user_realname_and_card(user_id)
    if not realname or not idcard:
        return False

    auth = AuthenticationField.query.filter(
        Authentication.is_edit == False,       # NOQA
        AuthenticationField.authentication_id == Authentication.id,
        AuthenticationField.value == idcard,
        AuthenticationField.authentication_id == Authentication.id,
        AuthenticationField.type_id == AuthenticationFieldType.id,
        AuthenticationFieldType.name == "身份证号码"
    ).first()
    if not auth:
        return False

    return auth.authentication.user_id != user_id
