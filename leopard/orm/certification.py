import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, Unicode,
    BigInteger
)
from sqlalchemy.orm import relationship

from leopard.core.orm import Base
from leopard.orm.social import Message
from leopard.helpers import generate_order_number


class AuthenticationFieldType(Base):
    __tablename__ = 'certification_field_type'

    id = Column(Integer, primary_key=True)
    name = Column(Unicode(64), nullable=False)
    pattern = Column(Unicode(512), default='')
    order = Column(Integer, default=0, nullable=False)
    is_content = Column(Boolean, default=True)
    required = Column(Boolean, default=True)
    score = Column(Integer, default=0)
    bit_status = Column(BigInteger)

    authentication_id = Column(
        Integer, ForeignKey('certification_type.id'), nullable=False)
    authentication = relationship('AuthenticationType', backref='fields')

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<AuthenticationFieldType "{}">'.format(self.name)


class AuthenticationField(Base):
    __tablename__ = 'certification_field'

    id = Column(Integer, primary_key=True)
    value = Column(Unicode(512), nullable=False)
    bit_status = Column(Integer, default=0)

    type_id = Column(
        Integer, ForeignKey('certification_field_type.id'), nullable=False)
    type = relationship('AuthenticationFieldType', backref='fields')

    authentication_id = Column(Integer, ForeignKey(
        'certification_authentication.id'), nullable=False)
    authentication = relationship('Authentication', backref='fields')

    def accept(self):
        self.bit_status = self.type.bit_status

    def reject(self):
        self.bit_status = 0

    @property
    def is_content(self):
        return self.type.is_content

    def __str__(self):
        return self.id

    def __repr__(self):
        return '<AuthenticationField "{}">'.format(self.id)


class AuthenticationType(Base):
    __tablename__ = 'certification_type'

    id = Column(Integer, primary_key=True)
    name = Column(Unicode(64), nullable=False)
    score = Column(Integer, nullable=False, default=0)
    logic = Column(Unicode(64), default='')
    description = Column(Unicode(256), default='请务必保证信息真实无误')

    @property
    def done_status(self):
        result = 0
        for i in self.fields:
            result |= i.bit_status
        return result

    def get_authentication(self, user_id):
        return Authentication.query.filter(Authentication.user_id == user_id,
                                           Authentication.type_id == self.id
                                           ).first()

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<AuthenticationType "{}">'.format(self.name)


class Authentication(Base):
    __tablename__ = 'certification_authentication'

    id = Column(Integer, primary_key=True)
    message = Column(Unicode(512), default='')
    is_edit = Column(Boolean, default=False)

    user_id = Column(Integer, ForeignKey('auth_user.id'), nullable=False)
    user = relationship('User', backref='authentications')

    type_id = Column(Integer, ForeignKey(
        'certification_type.id'), nullable=False)
    type = relationship('AuthenticationType', backref='authentications')
    added_at = Column(DateTime, default=datetime.datetime.now, nullable=False)

    @property
    def status(self):
        result = 0
        for i in self.fields:
            result |= i.bit_status
        return result == self.type.done_status

    def accept(self, realname=None, idcard=None):
        for i in self.fields:
            i.accept()
        self.is_edit = False

        if not realname:
            realname = AuthenticationField.query.filter(
                Authentication.id == self.id,
                AuthenticationField.authentication_id == Authentication.id,
                AuthenticationField.type_id == AuthenticationFieldType.id,
                AuthenticationFieldType.name == "真实姓名"
            ).first()
            if realname:
                self.user.realname = realname.value
        else:
            self.user.realname = realname

        if not idcard:
            idcard = AuthenticationField.query.filter(
                Authentication.id == self.id,
                AuthenticationField.authentication_id == Authentication.id,
                AuthenticationField.type_id == AuthenticationFieldType.id,
                AuthenticationFieldType.name == "身份证号码"
            ).first()
            if idcard:
                self.user.card = idcard.value
        else:
            self.user.card = idcard
        # 认证审核站内信
        title = '系统消息 - 认证安全!'.format(self.type.name)
        content = '尊敬的用户，您的 ({}) 已通过审核!'.format(self.type.name)
        Message.system_inform(to_user=self.user, title=title, content=content)

    def reject(self):
        for i in self.fields:
            i.reject()
        self.is_edit = True
        # 认证审核站内信
        title = '系统消息 - 认证安全!'.format(self.type.name)
        content = '尊敬的用户，您的 ({}) 未通过审核!'.format(self.type.name)
        Message.system_inform(to_user=self.user, title=title, content=content)

    @staticmethod
    def get_or_create_object_with_accept(user, type_id):
        auth = Authentication.query.filter_by(user_id=user.id,
                                              type_id=type_id).first()
        if not auth:
            auth_type = AuthenticationType.query.get(type_id)
            auth = Authentication()
            auth.type = auth_type
            auth.user = user
            for i in auth_type.fields:
                field = AuthenticationField()
                field.type = i
                field.authentication = auth
                field.value = ' '
        auth.accept()

    @staticmethod
    def get_or_create_object_with_reject(user, type_id):
        auth = Authentication.query.filter_by(user_id=user.id,
                                              type_id=type_id).first()
        if not auth:
            auth_type = AuthenticationType.query.get(type_id)
            auth = Authentication()
            auth.type = auth_type
            auth.user = user
            for i in auth_type.fields:
                field = AuthenticationField()
                field.type = i
                field.authentication = auth
                field.value = ' '
        auth.reject()

    def __str__(self):
        return self.id

    def __repr__(self):
        return '<Authentication "{}">'.format(self.id)


class IdCardLog(Base):
    __tablename__ = 'certification_id_card_log'

    id = Column(Integer, primary_key=True)
    name = Column(Unicode(16))
    id_card = Column(Unicode(32))
    order = Column(Unicode(80), default=generate_order_number, unique=True)
    status = Column(Integer)
    error_code = Column(Unicode(16))
    error_message = Column(Unicode(16))

    user_id = Column(Integer, ForeignKey('auth_user.id'), nullable=False)
    user = relationship('User', backref='id_card_log')
