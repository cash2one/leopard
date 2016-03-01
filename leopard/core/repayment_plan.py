"""
leopard.core.repayment_plan
====================

模块介绍
-----------------------

本模块定义了 还款计划的生成方法

开发责任人
-----------------------

* mzj@abstack.com

评审责任人
-----------------------

模块成员
-----------------------

"""
import datetime
import logging
from decimal import Decimal
from dateutil.relativedelta import relativedelta

from leopard.core import repayment_method
from leopard.core.repayment_method import get_total_interest
from leopard.helpers import get_enum
from leopard.orm import Plan, FinApplicationPlan, ProjectPlan

alogger = logging.getLogger('admin')


def get_day_project_plan_time(period):
    return relativedelta(days=period)


def get_months_project_plan_time(period):
    return relativedelta(months=period)


def get_time_func(nper_type):
    if nper_type == get_enum('DAY_PROJECT'):
        return get_day_project_plan_time
    else:
        return get_months_project_plan_time


def generate_repayment_plans(user, amount, project, investment,
                             repayment_name):
    """
    :功能描述: 生成还款计划 (流转标)
    :责任人: mzj@abstack.com
    :最后修改时间: 2014-10-27 10:43:47
    """

    # 根据还款名称获得还款方法
    now = datetime.datetime.now()
    time_func = get_time_func(project.nper_type)
    rate = Decimal(str(project.rate / 100))
    nper = project.periods

    repayment_func = getattr(repayment_method, repayment_name)
    datas = repayment_func(amount, nper, rate, now, time_func)

    plans = []
    for item in datas:
        plan = Plan()
        plan.user = user
        plan.period = item['period']
        plan.amount = item['amount']
        plan.interest = item['interest']
        plan.plan_time = item['plan_time']
        plan.status = get_enum('PLAN_PENDING')
        plan.investment = investment

        plans.append(plan)
    return plans


def generate_finapplication_plans(application, repayment_name):
    """
    :功能描述: 生成还款计划 (学仕贷申请书)
    :责任人: zjw@abstack.com
    :最后修改时间: 2015-03-15 22:29:51
    """

    # 根据还款名称获得还款方法
    now = datetime.datetime.now()
    time_func = get_months_project_plan_time
    rate = Decimal(str(application.rate)) / 12 / 100
    nper = application.periods
    amount = application.amount

    repayment_func = getattr(repayment_method, repayment_name)
    datas = repayment_func(amount, nper, rate, now, time_func)

    plans = []
    for item in datas:
        plan = FinApplicationPlan()
        plan.period = item['period']
        plan.amount = item['amount']
        plan.interest = item['interest']
        plan.plan_time = item['plan_time']
        plan.status = get_enum('FINAPPLICATION_PLAN_PENDING')
        plan.application = application

        plans.append(plan)
    return plans


def generate_repayment_project_plans(project, repayment_name):
    """
    :功能描述: 生成还款计划 (普通标)
    :责任人: mzj@abstack.com
    :最后修改时间: 2014-10-24 16:48:02

    :warning:: 需要后台审核通过后执行
    """
    rate = Decimal(str(project.rate / 100))
    pv = Decimal(str(project.amount))
    nper = project.periods

    total_interest = get_total_interest(project.amount, project)
    total_amount_interest = total_interest + project.amount
    repay_plans = []
    now = datetime.datetime.now()
    time_func = get_time_func(project.nper_type)

    repayment_func = getattr(repayment_method, repayment_name)
    datas = repayment_func(pv, nper, rate, now, time_func)

    for item in datas:
        plan = ProjectPlan()
        plan.project = project
        plan.user = project.user
        plan.period = item['period']
        plan.amount = item['amount']
        plan.interest = item['interest']
        plan.status = get_enum('PROJECT_PLAN_PENDING')

        plan.amount_interest = plan.amount + plan.interest
        plan.plan_time = item['plan_time']

        total_amount_interest -= plan.amount_interest
        plan.remain_amount = total_amount_interest
        repay_plans.append(plan)

    if repayment_name == 'capital_final':
        repay_plans[nper - 1].amount = pv
        repay_plans[nper - 1].remain_amount = 0

    alogger.info('- 普通标 [还款计划] 项目:{}, {}'.format(
        project.id, project.name))
    return repay_plans
