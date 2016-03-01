import factory

from factory.alchemy import SQLAlchemyModelFactory

from sqlalchemy import Column, ForeignKey, Integer, Unicode, UnicodeText, Boolean
from sqlalchemy.orm import backref, relationship

from leopard.core.orm import Base, db_session


class Guarantee(Base):
    __tablename__ = 'credit_guarantee'

    id = Column(Integer, primary_key=True)
    name = Column(Unicode(64), unique=True, nullable=False)
    full_name = Column(Unicode(128), unique=True, nullable=False)
    logo = Column(Unicode(1024))
    address = Column(Unicode(128))
    license = Column(Unicode(128))
    legal = Column(Unicode(128))
    contact = Column(Unicode(256))
    description = Column(UnicodeText)

    is_active = Column(Boolean, default=True)

    user_id = Column(Integer, ForeignKey('auth_user.id'), nullable=False)
    user = relationship('User', backref=backref('guarantee', uselist=False))

    def __str__(self):
        return self.name


class GuaranteeFactory(SQLAlchemyModelFactory):
    FACTORY_FOR = Guarantee
    FACTORY_SESSION = db_session

    name = factory.Sequence(lambda n: '模拟担保机构{}'.format(n))
    full_name = factory.Sequence(lambda n: '模拟担保机构{}有限公司'.format(n))

