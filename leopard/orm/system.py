from decimal import Decimal

from redis import Redis
from sqlalchemy import Column, event, Integer, Unicode, UnicodeText, Boolean

from leopard.core.orm import Base
from leopard.comps.redis import pool
from leopard.helpers.utils import generate_index_html, get_enum

redis = Redis(connection_pool=pool)


class Config(Base):
    __tablename__ = 'system_config'

    _configs = {}
    _configs_loaded = False

    id = Column(Integer, primary_key=True)

    key = Column(Unicode(64), nullable=False)
    value = Column(UnicodeText, nullable=False)

    name = Column(Unicode(64), nullable=False)
    description = Column(UnicodeText)

    @classmethod
    def get_config(cls, key, default=''):
        result = redis.get('leopard_config:{}'.format(key))
        if result:
            return result.decode()
        obj = cls.query.filter_by(key=key).first()
        result = obj.value if obj else default
        redis.set('leopard_config:{}'.format(key), result)
        return result

    @classmethod
    def get_bool(cls, key, default=0):
        result = cls.get_config(key, default=default)
        return bool(int(float(result)))

    @classmethod
    def get_float(cls, key, default=0.0):
        result = cls.get_config(key, default=default)
        return float(result)

    @classmethod
    def get_int(cls, key, default=0):
        result = cls.get_config(key, default=default)
        return int(float(result))

    @classmethod
    def get_decimal(cls, key, default=Decimal('0')):
        result = cls.get_config(key, default=default)
        return Decimal(result)


def receive_config_after(mapper, connection, target):
    redis.set('leopard_config:{}'.format(target.key), target.value)
    from leopard.apps.service import tasks
    tasks.generate_config.delay()
event.listen(Config, 'after_insert', receive_config_after)
event.listen(Config, 'after_update', receive_config_after)


class Banner(Base):
    __tablename__ = 'system_banner'

    id = Column(Integer, primary_key=True)
    src = Column(Unicode(128), nullable=False)
    link = Column(Unicode(128), nullable=False, default='javascript:;')
    priority = Column(Integer, nullable=False, default=0)
    is_show = Column(Boolean, nullable=False, default=True)
    location = Column(Integer, nullable=False,
                      default=get_enum('BANNER_WEB'),
                      server_default=str(get_enum('BANNER_WEB')))


def receive_banner_after(mapper, connection, target):
    from leopard.apps.service import tasks
    tasks.generate_config.delay()
event.listen(Banner, 'after_insert', receive_banner_after)
event.listen(Banner, 'after_update', receive_banner_after)
event.listen(Banner, 'after_delete', receive_banner_after)


class FirendLink(Base):
    __tablename__ = 'system_firend_link'

    id = Column(Integer, primary_key=True)
    name = Column(Unicode(32), nullable=False)
    link = Column(Unicode(128), nullable=False)
    img = Column(Unicode(128))
    priority = Column(Integer, nullable=False, default=0)
    is_show = Column(Boolean, nullable=False, default=True)
    logic = Column(Unicode(32), nullable=False)


def receive_link_after(mapper, connection, target):
    from leopard.apps.service import tasks
    tasks.generate_config.delay()
    generate_index_html()
event.listen(FirendLink, 'after_insert', receive_link_after)
event.listen(FirendLink, 'after_update', receive_link_after)
event.listen(FirendLink, 'after_delete', receive_link_after)
