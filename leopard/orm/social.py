import datetime

import factory

from factory.alchemy import SQLAlchemyModelFactory

from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Integer, Unicode,
                        UnicodeText)
from sqlalchemy.orm import relationship

from leopard.core.orm import Base, db_session


class Message(Base):
    __tablename__ = 'social_message'

    id = Column(Integer, primary_key=True)

    title = Column(Unicode(256), nullable=False)
    content = Column(UnicodeText)
    is_read = Column(Boolean, default=False, nullable=False)
    to_user_show = Column(Boolean, default=True, nullable=False)

    to_user_id = Column(Integer, ForeignKey('auth_user.id'), nullable=False)
    to_user = relationship('User', backref='inbox')

    added_at = Column(DateTime, default=datetime.datetime.now, nullable=False)

    def __repr__(self):
        return '<Message "{}">'.format(self.title)


    @staticmethod
    def system_inform(to_user, title, content):
        message = Message()
        message.from_user_id = 2
        message.to_user = to_user
        message.title = title
        message.content = content


class MessageFactory(SQLAlchemyModelFactory):
    FACTORY_FOR = Message
    FACTORY_SESSION = db_session

    title = factory.Sequence(lambda n: '模拟站内信{}'.format(n))
    content = factory.LazyAttribute(lambda e: '{}的内容'.format(e.title))
    added_at = factory.Sequence(lambda n: datetime.datetime.now() - datetime.timedelta(hours=n))
