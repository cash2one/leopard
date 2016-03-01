import logging

from flask.ext.restful import abort

from leopard.orm import Config, Log
from leopard.helpers import get_enum


logger = logging.getLogger('rotate')


def prepayment_all_check(project, args):
    current_period_amount = project.current_period_amount()
    remain_periods_capital = project.remain_periods_capital()
    rate = Config.get_decimal('COMMISSION_PROJECT_PREPAYMENT_RATE') / 100
    commission = project.amount * rate
    amount = current_period_amount + remain_periods_capital + commission

    logstr = ('[Project Prepayment All Check] User(id: {}): {}, Project(id): '
              '{}, Amount: {}, Project.period: {}, current_period_amount: {}, '
              'remain_periods_capital: {}, rate: {}, commission: {}')
    logger.info(logstr.format(project.user.id, project.user, project.id,
                amount, project.paid_periods, current_period_amount,
                remain_periods_capital, rate, commission))
    if project.user.available_amount < amount:
        logstr = ('[Project Prepayment All Check Failed(User have no enough '
                  'money)] User(id: {}): {}')
        logger.info(logstr.format(project.user.id, project.user))
        abort(400, message='你的可用余额不足，还清本项目需要{}元，请先充值！'.format(amount))
    return current_period_amount, remain_periods_capital, commission


def prepayment_all(project, data):
    """ 全部还款 """
    logstr = '[Project Prepayment All] Project(id): {}, Current Period: {}'
    logger.info(logstr.format(project.id, project.paid_periods))
    project.status = get_enum('PROJECT_PREPAYMENT')
    current_period_amount, remain_periods_capital, commission = data
    amount = remain_periods_capital

    if len(project.investments[0].repayment.executing_plans) != 1:
        project.repay(period=0)
    else:
        amount = current_period_amount + remain_periods_capital
    for i in project.investments:
        executing_plans = i.executing_plans[1:]
        i.status = get_enum('INVESTMENT_PREPAYMENT')
        i.repayment.status = get_enum('REPAYMENT_PREPAYMENT')
        i.repayment.prepayment_all(executing_plans)

    if Config.get_bool('COMMISSION_PROJECT_PREPAYMENT_FINE_OWNER'):
        project.prepay_fine()
    project.user.capital_deduct(amount)

    fundstr = '[提前还款本金] {}'.format(project.get_project_url())
    description = fundstr.format(project.id, project.name)
    Log.create_log(project, amount=remain_periods_capital,
                   description=description)
    project.user.capital_deduct(commission)

    fundstr = '[提前还款违约金] {}'.format(project.get_project_url())

    description = fundstr.format(project.id, project.name)
    Log.create_log(project, amount=commission, description=description)

    logstr = ('[Project Prepayment All] User(id: {}): {}, Project(id): {}, '
              'remain_periods_capital: {}元')
    logger.info(logstr.format(project.user.id, project.user, project.id,
                remain_periods_capital))

    logstr = ('[Project Prepayment All] User(id: {}): {}, Project(id): {}, '
              'remain_periods_capital: {}元')
    logger.info(logstr.format(project.user.id, project.user, project.id,
                              remain_periods_capital))
