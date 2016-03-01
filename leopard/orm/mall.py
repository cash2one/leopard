import json
import datetime
from decimal import Decimal
from sqlalchemy import (Column, DateTime, ForeignKey, Integer, Unicode,
                        UnicodeText, Boolean)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import relationship, backref

from leopard.core.orm import Base

class Commodity(Base):
    __tablename__ = 'mall_commodity'

    id = Column(Integer, primary_key=True)
    name = Column(Unicode(64), nullable=False)
    slogan = Column(Unicode(128))
    promotion = Column(Unicode(128))
    price = Column(postgresql.NUMERIC(19, 2), nullable=False)
    number = Column(Integer,default=0, nullable=False)
    category = Column(Integer)
    type = Column(Integer, nullable=False)
    priority = Column(Integer, nullable=False, default=0)
    is_show = Column(Boolean, nullable=False, default=True)
    src = Column(Unicode(128), nullable=False)
    details = Column(UnicodeText)
    amount = Column(postgresql.NUMERIC(19, 2))
    invest_amount = Column(postgresql.NUMERIC(19, 2))
    valid = Column(Integer, default=0)
    added_at = Column(DateTime, default=datetime.datetime.now, nullable=False)

    def __str__ (self):
        return self.name

    def __repr__ (self):
        return '<Commodity "{}">'.self.name


class CommodityOrder(Base):
    __tablename__ = 'mall_commodity_order'

    id = Column(Integer, primary_key=True)
    addressee = Column(Unicode(32))
    amount = Column(postgresql.NUMERIC(19, 2), nullable=False)
    number = Column(Integer, default=1, nullable=False)
    phone = Column(Unicode(32))
    address = Column(Unicode(128))
    status = Column(Integer, nullable=False)
    description = Column(Unicode(128))
    order_number = Column(Unicode(32))
    commodity_id = Column(Integer, ForeignKey('mall_commodity.id'), nullable=False)
    commodity = relationship('Commodity', backref='order')
    user_id = Column(Integer, ForeignKey('auth_user.id'), nullable=False)
    user = relationship('User', backref='commodity_order')
    added_at = Column(DateTime, default=datetime.datetime.now, nullable=False)
    process_at =Column(DateTime)

    def __str__ (self):
        return self.id

    def __repr__ (self):
        return '<CommodityOrder "{}">'.self.id