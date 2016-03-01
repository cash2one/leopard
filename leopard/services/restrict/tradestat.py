from redis import Redis
from sqlalchemy import func

from leopard.orm import User, Investment, Plan, Log
from leopard.helpers import get_enum
from leopard.core.orm import db_session
from leopard.comps.redis import pool

redis = Redis(connection_pool=pool)


# 成交量
def turnover():
    if not redis.get('trade_stat:turnover'):
        pending = get_enum('INVESTMENT_PENDING')
        failed = get_enum('INVESTMENT_FAILED')
        notin = [pending, failed]
        investments = db_session.query(func.sum(Investment.amount)).filter(
            Investment.status.notin_(notin)).scalar() or 0

        investments += 54140000         # 旧平台数据
        redis.set('trade_stat:turnover', investments, 3600)
        return investments
    else:
        return redis.get('trade_stat:turnover').decode()


# 注册量
def register_quantity():
    if not redis.get('trade_stat:register_quantity'):
        users = db_session.query(
            func.count(User.id)).filter(User.username != 'su').scalar()
        redis.set('trade_stat:register_quantity', users, 3600)
        return users
    else:
        return redis.get('trade_stat:register_quantity').decode()


# 待还金额
def gross_income():
    if not redis.get('trade_stat:gross_income'):

        gross_income = db_session.query(func.sum(Plan.amount)).filter(
            Plan.status == get_enum('PLAN_PENDING')
        ).scalar()

        gross_income = gross_income if gross_income else 0

        total_income = gross_income
        redis.set('trade_stat:gross_income', total_income, 3600)
        return total_income
    else:
        return redis.get('trade_stat:gross_income').decode()


# 累计为客户赚取收益
def users_income():
    if not redis.exists('trade_stat:users_income'):
        plan_amounts = db_session.query(func.sum(Plan.interest)).filter(
            Plan.status == get_enum('PLAN_DONE')
        ).scalar()
        reward_amounts = db_session.query(func.sum(Log.amount)).filter(
            Log.description.like(u'%奖励%')
        ).scalar()

        plan_amounts = plan_amounts if plan_amounts else 0
        reward_amounts = reward_amounts if reward_amounts else 0
        total_users_income = plan_amounts + reward_amounts

        total_users_income += 1109870       # 旧平台数据
        redis.set('trade_stat:users_income', total_users_income, 3600)

        return total_users_income
    else:
        return redis.get('trade_stat:users_income').decode()
