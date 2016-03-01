import random
from leopard.orm import Config
from redis import Redis
from leopard.comps.redis import pool

redis = Redis(connection_pool=pool)


def identifying_code():
    return "{}".format(random.randint(100000, 999999))
