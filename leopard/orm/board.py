import datetime

import factory

from factory.alchemy import SQLAlchemyModelFactory

from sqlalchemy import (Boolean, Column, DateTime, Integer, Unicode,
                        UnicodeText)

from leopard.core.orm import Base, db_session


class Post(Base):
    __tablename__ = 'board_post'

    id = Column(Integer, primary_key=True)

    title = Column(Unicode(128), nullable=False)
    content = Column(UnicodeText)
    figure = Column(Unicode(128), default='', nullable=False)
    type = Column(Integer, nullable=False)
    priority = Column(Integer, default=0)
    is_active = Column(Boolean, default=True, nullable=False)

    added_at = Column(DateTime, default=datetime.datetime.now, nullable=False)

    def __str__(self):
        return self.title

    def __repr__(self):
        return '<Post "{}">'.format(self.title)


class PostFactory(SQLAlchemyModelFactory):
    FACTORY_FOR = Post
    FACTORY_SESSION = db_session

    title = factory.Sequence(lambda n: '模拟文章{}'.format(n))
    content = factory.LazyAttribute(lambda e: '{}的内容'.format(e.title))
