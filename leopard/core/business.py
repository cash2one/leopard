import logging
from decimal import Decimal

from leopard.core.orm import db_session
from leopard.helpers.exceptions import FlowOperationException
from leopard.core.project_type import tender_func, CommonTender

alogger = logging.getLogger('admin')
logger = logging.getLogger('rotate')


def tender(*args, **kwargs):
    return tender_func(*args, **kwargs)


def common_full_tender(project, session):
    """ 普通标 满标审核操作 """
    logfmt = '===== 满标审核操作 开始 {}, {} ====='
    loginfo = logfmt.format(project.id, project.name)
    alogger.info(loginfo)

    CommonTender.full_tender(project, session)

    logfmt = '===== 满标审核操作 结束 {}, {} ====='
    loginfo = logfmt.format(project.id, project.name)
    alogger.info(loginfo)


def flow_borrow(ids, current_user, session):
    """流标操作，后台操作"""
    from leopard.orm import Project
    message = None
    for i in ids:
        project = Project.query.get(i)
        if project.type.logic == 'flow':
            message = '流转标不能流标'
            raise FlowOperationException(message)
        logfmt = '[后台管理] 流标操作 project: {} 操作人: {}'
        loginfo = logfmt.format(project, current_user)
        alogger.info(loginfo)
        message = flow_borrow_one(project, current_user, session)
        if message:
            raise FlowOperationException(message)

    return message


def flow_borrow_one(project, current_user, session):
    """流标操作 根据id"""
    if project.type.logic == 'flow':
        return '流转标不能流标'
    return CommonTender.flow_borrow(project, current_user, session)


def friend_invest_award(user, investment, amount, periods=None):
    """
    :函数名: 好友投资奖励
    :功能: 每期生成一个红包，给投资人和邀请人(生成的红包不足一分钱则不发放)
    """
    from leopard.orm import Config
    from dateutil.relativedelta import relativedelta
    if not user.invited:
        return

    invitation_award = Config.get_bool('FRIEND_INVITATION_AWARD_ENABLE')
    if not invitation_award:
        return

    if user.invited.friend_invest_award_level == 'A':
        award_expires = Config.get_int('FRIEND_INVITATION_AWARD_EXPIRES_A')
        own_award_rate = Config.get_decimal('FRIEND_INVITATION_OWN_AWARD_RATE_A')
        award_rate = Config.get_decimal('FRIEND_INVITATION_AWARD_RATE_A')
    elif user.invited.friend_invest_award_level == 'B':
        award_expires = Config.get_int('FRIEND_INVITATION_AWARD_EXPIRES_B')
        own_award_rate = Config.get_decimal('FRIEND_INVITATION_OWN_AWARD_RATE_B')
        award_rate = Config.get_decimal('FRIEND_INVITATION_AWARD_RATE_B')
    else:
        award_expires = Config.get_int('FRIEND_INVITATION_AWARD_EXPIRES')
        own_award_rate = Config.get_decimal('FRIEND_INVITATION_OWN_AWARD_RATE')
        award_rate = Config.get_decimal('FRIEND_INVITATION_AWARD_RATE')
        
    if user.added_at + relativedelta(days=award_expires) < investment.added_at:
        return

    # 自己投资的奖励比率
    # own_award_rate = Config.get_decimal('FRIEND_INVITATION_OWN_AWARD_RATE')
    own_award_rate = Decimal(str(own_award_rate / 10000))

    # 邀请人的奖励比率
    # award_rate = Config.get_decimal('FRIEND_INVITATION_AWARD_RATE')
    award_rate = Decimal(str(award_rate / 10000))

    award_amount = amount * award_rate
    own_award_amount = amount * own_award_rate

    if periods:
        # 一次付息到期还款就将  奖励金额 x 期数 在第一次发放
        award_amount = award_amount * periods
        own_award_amount = own_award_amount * periods

    fmt = ('[回款-好友投资奖励] 用户:{} id:{}, amount:{} '
           'periods:{} 投资人能获得奖励:{} 推荐人奖励:{}')
    logger.info(fmt.format(user, user.id, amount, periods,
                own_award_amount, award_amount))

    if award_amount >= Decimal('0.01'):
        _create_award_redpacket(user.invited.id, award_amount)

    own_award_expires = Config.get_int('FRIEND_INVITATION_AWARD_EXPIRES')
    if user.added_at + relativedelta(days=own_award_expires) < investment.added_at:
        return
    elif own_award_amount >= Decimal('0.01'):
        _create_award_redpacket(user.id, own_award_amount)


def _create_award_redpacket(user_id, amount):
    """ 生成好友投资奖励红包 """
    from leopard.orm import RedPacket, RedPacketType
    packet_type = RedPacketType.query.get(1)        # 普通红包

    redpacket = RedPacket()
    redpacket.name = '好友投资奖励红包'
    redpacket.amount = amount
    redpacket.never_expire = True
    redpacket.is_use = False
    redpacket.is_available = True
    redpacket.user_id = user_id
    redpacket.type = packet_type
    db_session.add(redpacket)
    db_session.commit()
