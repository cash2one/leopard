import logging
from leopard.core import business
from leopard.orm import Config, AutoInvestIndex
from leopard.helpers import get_enum
from decimal import Decimal
logger = logging.getLogger('rotate')


# 自动投标检查
def auto_invest_check(user, project, amount, max_allow_amount, remain_enable_amount):
    message = None
    if user.available_amount - amount < user.autoinvest.reserve_amount:
        amount = user.available_amount - user.autoinvest.reserve_amount

    amount = min(amount, project.max_lend_amount, max_allow_amount, remain_enable_amount)

    if remain_enable_amount <= 0:
        message = '项目当前可投金额为0元'
    elif user == project.user:
        message = '投资人不能为项目发起人'
    elif isinstance(amount, str) or amount <= 0:
        message = '投资金额不合法'
    elif amount < project.min_lend_amount:
        message = '投资金额小于项目的最小投资额'
    elif user.autoinvest.min_amount > amount:
        message = '投资最小金额大于投资金额'
    elif user.autoinvest.min_amount > max_allow_amount:
        message = '投资最小金额大于允许最大投资金额'

    logfmt = '\t(投资金额检查) 用户({}, {}) 可以投资:amount: {} 当前项目剩余自动可投金额:{}'
    loginfo = logfmt.format(user.id, user.username, amount, remain_enable_amount)
    logger.info(loginfo)
    return dict(amount=amount, message=message)


def choose_enable_list(autoinvest_list, project, project_enable_amount):
    autoinvest_enable_list = []
    sum_amount = Decimal('0')
    remain_enable_amount = project_enable_amount
    max_allow_amount = Config.get_config('AUTO_INVESTMENT_MAXAMOUNT')
    max_allow_amount = Decimal(str(max_allow_amount))
    for item in autoinvest_list:
        item = item.auto   # 索引表
        min_amount = min(item.user.available_amount, item.max_amount)
        result = auto_invest_check(item.user, project, amount=min_amount,
            max_allow_amount=max_allow_amount, remain_enable_amount=remain_enable_amount)
        logger.info('\t用户({}, {}, 可用资金:{}) min_amount:{}, 投标检查返回值:{}'.format(
            item.user.id,
            item.user.username,
            item.user.available_amount,
            min_amount,
            result
        ))
        if not result.get('message'):
            sum_amount += result.get('amount')
            remain_enable_amount -= result.get('amount')
            autoinvest_enable_list.append(dict(user=item.user,
                                          amount=result.get('amount')))
            logger.info('\t\t实际可投用户({}, {}, 可用资金:{}, 投资金额:{})'.format(
                item.user.id,
                item.user.username,
                item.user.available_amount,
                result.get('amount')
            ))
        else:
            logger.info('\t\t不可投用户({}, {}, 可用资金:{}, 投资金额:{}) 原因: {}'.format(
                item.user.id, item.user.username,
                item.user.available_amount,
                result.get('amount'),
                result.get('message')
            ))
    logger.info('实际的可投资的用户列表:{}'.format(autoinvest_enable_list))
    return autoinvest_enable_list, sum_amount


def autoinvest_tender(sum_amount, project_enable_amount, project,
                      autoinvest_enable_list, session):
    logger.info('[直接投资] 自动投标总额({}) ,项目的最大可投总额({}),  project: {}'.format(
        sum_amount, project_enable_amount, project))
    for item in autoinvest_enable_list:
        tender_user = item.get('user')
        tender_amount = item.get('amount')

        logfmt = ('[开始投标] 投资人({}, {}, 可用资金:{}, 预留资金: {}, '
                  '最大最小投资额({}, {})), 投资金额: {}')

        loginfo = logfmt.format(
            tender_user.id,
            tender_user.username,
            tender_user.available_amount,
            tender_user.autoinvest.reserve_amount,
            tender_user.autoinvest.min_amount,
            tender_user.autoinvest.max_amount, tender_amount
        )
        logger.info(loginfo)

        try:
            business.tender(tender_user, project, tender_amount,
                            session=session, invest_from=get_enum('MODE_AUTO'))
            session.delete(tender_user.autoindex)
            auto_index = AutoInvestIndex()
            auto_index.auto = tender_user.autoinvest
            auto_index.user = tender_user
            session.add(auto_index)
            session.commit()
            logger.info('[投标结束]')
        except Exception as e:
            session.rollback()
            logger.error('Celery task(autoinvest_tender): {}'.format(e))


def auto_invest_start(session, project, autoinvest_list):
    auto_investment_rate = Config.get_float('AUTO_INVESTMENT_RATE')
    # 自动投资可投的总额
    project_enable_amount = project.amount * \
        Decimal(str(auto_investment_rate / 100))
    logger.info('[自动投标开始] 项目({}, {}, 自动投标可投金额:{}) 投标的用户列表:{}'.format(
        project.id, project.name, project_enable_amount, autoinvest_list
    ))
    autoinvest_enable_list, sum_amount = choose_enable_list(autoinvest_list,
                                                            project, project_enable_amount)
    try:
        autoinvest_tender(
            sum_amount=sum_amount,
            autoinvest_enable_list=autoinvest_enable_list,
            project_enable_amount=project_enable_amount,
            project=project,
            session=session
        )
    except Exception as e:
        session.rollback()
        logger.error('Celery task(automatic_investments): {}'.format(e))
