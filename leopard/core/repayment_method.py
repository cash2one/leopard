"""
leopard.core.repayment_method
====================

模块介绍
-----------------------

本模块定义了 投标的还款方式

开发责任人
-----------------------

* mzj@abstack.com

评审责任人
-----------------------

模块成员
-----------------------

"""
from decimal import Decimal


def quantize_func(data):
    if not isinstance(data, Decimal):
        data = Decimal(str(data))
    return data


def one_only(pv, nper, rate, now, time_func):
    """一次性还款"""
    interest = quantize_func(rate * nper * pv)
    datas = []

    datas.append({
        'period': 1,
        'amount': pv,
        'interest': interest,
        'plan_time': now + time_func(nper)
    })
    return datas


def interest_first(pv, nper, rate, now, time_func):
    """一次性付息到期还本"""

    amount = quantize_func(pv)
    interest = quantize_func(pv * nper * rate)
    datas = []

    nper_1 = {
        'period': 1,
        'amount': 0,
        'interest': interest,
        'plan_time': now
    }
    nper_2 = {
        'period': 2,
        'amount': amount,
        'interest': 0,
        'plan_time': now + time_func(nper)
    }
    datas.append(nper_1)
    datas.append(nper_2)
    return datas


def capital_final(pv, nper, rate, now, time_func):
    """每月付息到期还本"""
    interest = quantize_func(pv * rate)
    datas = []

    for i in range(1, nper + 1):
        nper_data = {
            'period': i,
            'amount': 0,
            'interest': interest,
            'plan_time': now + time_func(i)
        }
        datas.append(nper_data)
    datas[nper - 1]['amount'] = quantize_func(pv)
    return datas


def average_capital(pv, nper, rate, now, time_func):
    """等本等息"""
    amount = quantize_func(pv / nper)
    interest = quantize_func(pv * rate)

    datas = []
    for i in range(1, nper + 1):
        nper_data = {
            'period': i,
            'amount': amount,
            'interest': interest,
            'plan_time': now + time_func(i)
        }
        datas.append(nper_data)

    return datas


def average_captial_plus_interest(pv, nper, rate, now, time_func):
    """等额本息"""
    amount = Decimal(str(pv))
    temp_pow = Decimal(str((1 + rate) ** nper))
    amount_interest = amount * rate * temp_pow / (temp_pow - 1)
    data = []

    for i in range(1, nper + 1):
        interest = amount * rate
        amount = amount - amount_interest + interest

        data.append({
            'period': i,
            'amount': quantize_func(amount_interest - interest),
            'interest': quantize_func(interest),
            'plan_time': now + time_func(i)
        })

    return data


def get_total_interest(amount, project):
    """获得总利息"""
    pv = Decimal(str(amount))
    rate = Decimal(str(project.rate / 100))
    nper = project.periods

    if project.repaymentmethod.logic == 'average_captial_plus_interest':
        rv = Decimal(str((1 + rate) ** nper))
        total_interest = (pv * rate * rv / (rv - 1)) * nper - pv
    else:
        total_interest = rate * nper * pv
    return quantize_func(total_interest)
