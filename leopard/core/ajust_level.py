import logging
import datetime
from dateutil.relativedelta import relativedelta

from leopard.orm import UserLevelLog, Config

logger = logging.getLogger('rotate')

def judge_level(levels, amount):
    new_level = None
    for level in levels:
        if level.level_amount <= amount:
            new_level = level
            continue
        break

    if new_level == None and levels:
        new_level = levels[0]

    return new_level


def down_level_check(user, levels, courrent_level_amount):

    user_level_log = UserLevelLog.query.filter_by(
            user_id = user.id).order_by('id desc').first()
    if user_level_log:
        level_expires = user_level_log.added_at + relativedelta(
                        months = Config.get_int('ADJUST_USER_LEVEL_EXPIRES'))
        now = datetime.datetime.now()

        if level_expires > now:
            return None

    down_level_amount = user.repaying_amount + user.available_amount
    new_level = judge_level(levels, down_level_amount)
    new_level_amount = new_level.level_amount

    if courrent_level_amount > new_level_amount:
        return new_level

    return None


def adjust_user_level_check(user, levels):

    up_level_amount = user.repaying_amount

    new_level = judge_level(levels, up_level_amount)

    logfmt = '\t(等级调整检查) 用户({}) 待收金额:{}, 可用金额:{}, 等级: {}'
    loginfo = logfmt.format(user.id, user.repaying_amount, user.available_amount, 
            new_level)
    logger.info(loginfo)

    if not new_level:
        return dict(message='未找到等级')

    if user.level:
        courrent_level_amount = user.level.level_amount
        new_level_amount = new_level.level_amount
        logfmt = '\t(等级上调检查) 用户({}), 可用金额:{}, 上调要求金额:{},  当前等级金额要求:{} '
        loginfo = logfmt.format(user.id, user.available_amount, new_level_amount, 
            courrent_level_amount)
        logger.info(loginfo)
        if courrent_level_amount < new_level_amount:
            return dict(level=new_level, reverse=True)
        elif courrent_level_amount > new_level_amount:
            logfmt = '\t(等级下调检查) 用户({}), 可用金额:{}, 下调要求金额:{}  '
            loginfo = logfmt.format(user.id, user.available_amount, new_level_amount)
            logger.info(loginfo)

            down_new_level = down_level_check(user, levels, courrent_level_amount)
            if down_new_level:
                return dict(level=down_new_level, reverse=False)
        else:
            pass
    else:
        return dict(level=new_level, reverse=True)

    return dict(message='不符合要求')

