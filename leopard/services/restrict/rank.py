import json
import datetime

from redis import Redis
from sqlalchemy import cast, func, Date
from sqlalchemy.sql import label
from dateutil.relativedelta import relativedelta

from leopard.orm import User, Investment
from leopard.comps.redis import pool
from leopard.core.orm import db_session

redis = Redis(connection_pool=pool)

def totalList():
    if not redis.llen('rank:total'):
        total_row = db_session.query(
            User.id,
            User.username,
            label('number', func.count(Investment.amount)),
            label('total_amount', func.sum(Investment.amount))
        ).filter(
            Investment.user_id == User.id,
        ).group_by(User.id).order_by(
            func.sum(Investment.amount).desc()
        ).limit(15).all()

        total_list = []

        for i in total_row:
            i = dict(zip(i.keys(), i))
            data = {
                'id': i['id'],
                'username': i['username'],
                'total_amount': float(i['total_amount']),
                'number': i['number']
            }
            total_list.append(data)
            redis.rpush('rank:total', json.dumps(data))
        redis.expire('rank:total', 3600)
    else:
        total_list = [json.loads(i.decode()) for i in redis.lrange('rank:total', 0, redis.llen('rank:total'))]

    return total_list


def dayList():
    if not redis.llen('rank:day'):
        rows = db_session.query(
            User.id,
            User.username,
            label('number', func.count(Investment.amount)),
            label('total_amount', func.sum(Investment.amount))
        ).filter(
            Investment.user_id == User.id,
            cast(Investment.added_at, Date) == datetime.date.today()
        ).group_by(User.id).order_by(
            func.sum(Investment.amount).desc()
        ).limit(15).all()

        rank_list = []

        for i in rows:
            i = dict(zip(i.keys(), i))
            data = {
                'id': i['id'],
                'username': i['username'],
                'total_amount': float(i['total_amount']),
                'number': i['number']
            }
            rank_list.append(data)
            redis.rpush('rank:day', json.dumps(data))
        redis.expire('rank:day', 3600)
    else:
        rank_list = [json.loads(i.decode()) for i in redis.lrange('rank:day', 0, redis.llen('rank:day'))]

    return rank_list


def weekList():
    if not redis.llen('rank:week'):
        rows = db_session.query(
            User.id,
            User.username,
            label('number', func.count(Investment.amount)),
            label('total_amount', func.sum(Investment.amount))
        ).filter(
            Investment.user_id == User.id,
            cast(Investment.added_at, Date) <= datetime.datetime.today(),
            cast(Investment.added_at, Date) >= datetime.datetime.today() -
            datetime.timedelta(weeks=1)
        ).group_by(User.id).order_by(
            func.sum(Investment.amount).desc()
        ).limit(15).all()

        rank_list = []

        for i in rows:
            i = dict(zip(i.keys(), i))
            data = {
                'id': i['id'],
                'username': i['username'],
                'total_amount': float(i['total_amount']),
                'number': i['number']
            }
            rank_list.append(data)
            redis.rpush('rank:week', json.dumps(data))
        redis.expire('rank:week', 3600)
    else:
        rank_list = [json.loads(i.decode()) for i in redis.lrange('rank:week', 0, redis.llen('rank:week'))]

    return rank_list


def monthList():
    if not redis.llen('rank:month'):
        rows = db_session.query(
            User.id,
            User.username,
            label('number', func.count(Investment.amount)),
            label('total_amount', func.sum(Investment.amount))
        ).filter(
            Investment.user_id == User.id,
            cast(Investment.added_at, Date) <= datetime.datetime.today(),
            cast(Investment.added_at, Date) >= datetime.datetime.today() -
            relativedelta(months=1)
        ).group_by(User.id).order_by(
            func.sum(Investment.amount).desc()
        ).limit(15).all()

        rank_list = []

        for i in rows:
            i = dict(zip(i.keys(), i))
            data = {
                'id': i['id'],
                'username': i['username'],
                'total_amount': float(i['total_amount']),
                'number': i['number']
            }
            rank_list.append(data)
            redis.rpush('rank:month', json.dumps(data))
        redis.expire('rank:month', 3600)
    else:
        rank_list = [json.loads(i.decode()) for i in redis.lrange('rank:month', 0, redis.llen('rank:month'))]

    return rank_list


