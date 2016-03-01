import datetime
import base64
import hashlib
import functools
import operator

import factory

from decimal import Decimal

from factory.alchemy import SQLAlchemyModelFactory
from leopard.core.config import get_config
from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Integer,
                        Unicode, func, UnicodeText, Table, event, or_, not_)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import relationship, backref

from leopard.core.orm import Base, MutableList, db_session
from leopard.helpers import get_enum, sign
from leopard.orm.lending import Investment, Project
from leopard.orm.account import Deposit, Log, Bankcard
from leopard.orm.social import Message
from leopard.orm.certification import Authentication

config = get_config(__name__)
service = get_config('leopard.apps.service')
setup = get_config('project')


m2m_groups_users = Table(
    'm2m_groups_users', Base.metadata,
    Column('auth_group_id', Integer, ForeignKey('auth_group.id')),
    Column('auth_user_id', Integer, ForeignKey('auth_user.id'))
)


class Group(Base):
    __tablename__ = 'auth_group'

    id = Column(Integer, primary_key=True)

    name = Column(Unicode(64), unique=True, nullable=False)
    description = Column(UnicodeText, default='', nullable=False)

    _permissions = Column(
        MutableList.as_mutable(postgresql.ARRAY(Unicode(64))), default=[])

    users = relationship('User', backref='groups', secondary=m2m_groups_users)

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<Group "{}">'.format(self.name)

    def has_permission(self, permission):
        return permission in self._permissions


class GroupFactory(SQLAlchemyModelFactory):
    FACTORY_FOR = Group
    FACTORY_SESSION = db_session


class User(Base):
    __tablename__ = 'auth_user'

    id = Column(Integer, primary_key=True)

    username = Column(Unicode(16), unique=True, nullable=False)
    _password = Column(Unicode(128), nullable=False)
    _trade_password = Column(Unicode(128))
    phone = Column(Unicode(32))
    email = Column(Unicode(64))

    icq = Column(Unicode(32))
    card = Column(Unicode(32))
    avatar = Column(Unicode(1024))
    realname = Column(Unicode(64))

    is_borrower = Column(Boolean, default=False)  # 是否是借款人
    address = Column(Unicode(128))
    age = Column(Integer, default='1')
    sex = Column(Unicode(128), default='男')  # 1为男，2为女
    education = Column(Unicode(128), default='小学')  # 教育情况
    marital_status = Column(Unicode(128), default='未婚')  # 婚姻情况
    certify_level = Column(Unicode(16), default='C')  # 信用等级

    active_amount = Column(
        postgresql.NUMERIC(19, 2), default=Decimal('0.0'), nullable=False)
    deposit_amount = Column(
        postgresql.NUMERIC(19, 2), default=Decimal('0.0'), nullable=False)
    income_amount = Column(
        postgresql.NUMERIC(19, 2), default=Decimal('0.0'), nullable=False)
    blocked_amount = Column(
        postgresql.NUMERIC(19, 2), default=Decimal('0.0'), nullable=False)
    guarded_amount = Column(
        postgresql.NUMERIC(19, 2), default=Decimal('0.0'), nullable=False)
    experience_amount = Column(
        postgresql.NUMERIC(19, 2), default=Decimal('0.0'), nullable=False)
    available_credit_points = Column(Integer, default=0, nullable=False)
    blocked_credit_points = Column(Integer, default=0, nullable=False)
    gift_points = Column(postgresql.NUMERIC(19, 2), default=Decimal('0.0'),
                         nullable=False)

    birth_day = Column(DateTime)
    first_investment = Column(DateTime)
    first_top_up = Column(DateTime)
    is_active = Column(Boolean, default=False, nullable=False)
    is_super = Column(Boolean, default=False, nullable=False)
    is_staff = Column(Boolean, default=False, nullable=False)
    is_server = Column(Boolean, default=False, nullable=False)
    is_guarantee = Column(Boolean, default=False, nullable=False)
    is_vip = Column(Boolean, default=False, nullable=False)
    is_bane = Column(Boolean, default=False, nullable=False)

    is_league = Column(Boolean, default=False, nullable=False)
    interest = Column(postgresql.NUMERIC(19, 2), default=Decimal('0.0'),
                      nullable=False)
    friend_invitation = Column(Unicode(1024), unique=True, nullable=False)
    # 短邀请码
    invite_code = Column(Unicode(16), unique=True, nullable=True)

    vip_end_at = Column(DateTime)

    server_id = Column(Integer, ForeignKey('auth_user.id'))
    server = relationship(
        'User', backref='clients', remote_side=[id], foreign_keys=[server_id])

    invited_id = Column(Integer, ForeignKey('auth_user.id'))
    invited = relationship(
        'User', backref='next_users', remote_side=[id],
        foreign_keys=[invited_id])
    friend_invest_award_level = Column(Unicode(2), default='', server_default='') #好友邀请奖励等级
    login_counter = Column(Integer, default=0, nullable=False)
    last_login_ip = Column(Unicode(16), default='0.0.0.0', nullable=False)
    current_login_ip = Column(Unicode(16), default='0.0.0.0', nullable=False)
    last_login_at = Column(
        DateTime, default=datetime.datetime.now, nullable=False)
    current_login_at = Column(
        DateTime, default=datetime.datetime.now, nullable=False)
    added_at = Column(DateTime, default=datetime.datetime.now, nullable=False)

    #是否同步给征信
    is_sync = Column(Boolean, default=False)

    #联盟提供用户注册来源
    source_website_id = Column(Integer, ForeignKey('auth_source_website.id'))
    source_website = relationship(
        'SourceWebsite', backref='source_users')
    source_code = Column(Unicode(16))

    level_id = Column(Integer, ForeignKey('auth_user_level.id'))
    level = relationship(
        'UserLevel', backref='auth_user_level')

    level_map = {
        '0': 'C',
        '1': 'C',
        '2': 'C',
        '3': 'C',
        '4': 'B',
        '5': 'B',
        '6': 'B',
        '7': 'A',
        '8': 'A',
        '9': 'A',
        '10': 'A',
        '11': 'AA',
        '12': 'AA',
        '13': 'AA',
        '14': 'AA',
        '15': 'AAA',
    }

    def __str__(self):
        return self.username

    def __repr__(self):
        return '<User "{}">'.format(self.username)

    def invested_project_amount(self, project):
        amount = db_session.query(func.sum(Investment.amount)).filter(
            Investment.user_id == self.id,
            Investment.project_id == project.id).first()[0]
        if not amount:
            return 0
        else:
            return amount

    @property
    def bankcard_need_amount(self):
        """ 同卡同出需要的总额 """
        amount = db_session.query(
                func.sum(Bankcard.need_amount)
            ).filter(
                Bankcard.user_id == self.id
            ).scalar()
        if not amount:
            return 0
        else:
            return amount

    @property
    def total_deposit(self):
        amount = db_session.query(
            func.sum(Deposit.amount)
        ).filter(
            Deposit.user_id == self.id,
            Deposit.status == get_enum('DEPOSIT_SUCCESSED')
        ).first()[0]
        if not amount:
            return 0
        else:
            return amount

    @property
    def password(self):
        return self._password

    @password.setter
    def password(self, value):
        self._password = hashlib.sha512(
            '{}.{}'.format(value,
                           service['SECRET_KEY']).encode('utf-8')).hexdigest()

    @property
    def trade_password(self):
        return self._trade_password

    @trade_password.setter
    def trade_password(self, value):
        self._trade_password = hashlib.sha512(
            '{}.{}'.format(value,
                           service['SECRET_KEY']).encode('utf-8')).hexdigest()

    @property
    def available_amount(self):
        return self.deposit_amount + self.income_amount + self.active_amount

    @property
    def investing_amount(self):
        """
            待收本金
        """
        data = [plan.amount
                for investment in self.investments
                if investment.status not in (get_enum('INVESTMENT_PENDING'),
                                             get_enum('INVESTMENT_FAILED'))
                for plan in investment.executing_plans]
        return functools.reduce(operator.add, data, Decimal('0.0'))

    @property
    def investing_interest(self):
        """
            待收利息
        """
        data = [plan.interest
                for investment in self.investments
                if investment.status not in (get_enum('INVESTMENT_PENDING'),
                                             get_enum('INVESTMENT_FAILED'))
                for plan in investment.executing_plans]
        return functools.reduce(operator.add, data, Decimal('0.0'))

    @property
    def invested_amount(self):
        """
            借出总额
        """
        data = [investment.amount
                if investment.status not in (get_enum('INVESTMENT_PENDING'),
                                             get_enum('INVESTMENT_FAILED'))
                else 0 for investment in self.investments]
        return functools.reduce(operator.add, data, Decimal('0.0'))

    @property
    def net_income(self):
        """ 累计净收益 """
        reward_amounts = db_session.query(func.sum(Log.amount)).filter(
            or_(
                Log.description.like('%奖励%'),
                Log.description.like('%红包提现%')
            ),
            not_(
                Log.description.contains('旧系统资金转移') |
                Log.description.contains('注册体验金')
            ),
            Log.user_id == self.id
        ).scalar()
        reward_amounts = reward_amounts if reward_amounts else 0
        return self.invested_interest + reward_amounts

    @property
    def invested_interest(self):
        """
            已赚利息
        """
        data = [plan.interest
                for investment in self.investments
                if investment.status not in (get_enum('INVESTMENT_PENDING'),
                                             get_enum('INVESTMENT_FAILED'))
                for plan in investment.executed_plans]
        return functools.reduce(operator.add, data, Decimal('0.0'))

    @property
    def repaying_amount(self):
        """
            待收总额
        """
        data = [plan.amount + plan.interest
                for investment in self.investments
                if investment.status not in (get_enum('INVESTMENT_PENDING'),
                                             get_enum('INVESTMENT_FAILED'))
                for plan in investment.executing_plans]
        return functools.reduce(operator.add, data, Decimal('0.0'))

    @property
    def repaid_amount(self):
        """
            已收总额
        """
        data = [plan.amount + plan.interest
                for investment in self.investments
                if investment.status not in (get_enum('INVESTMENT_PENDING'),
                                             get_enum('INVESTMENT_FAILED'))
                for plan in investment.executed_plans]
        return functools.reduce(operator.add, data, Decimal('0.0'))

    @property
    def available_repay_amount(self):
        """
            当前可用于还款的金额
        """
        if self.investing_amount >= self.experience_amount:
            available_amount = self.available_amount
        else:
            available_amount = (
                self.available_amount - self.experience_amount +
                self.investing_amount
            )
        return available_amount

    @property
    def applyingtimes(self):
        """
            当前申请中借款次数
        """
        data = [ 1 for applications in (self.published_applications + self.published_finapplications)
                if applications.status in (get_enum('APPLICATION_RISKCONTROL_TRIALING'),
                    get_enum('APPLICATION_GUARANTEE_TRIALING'))]

        return functools.reduce(operator.add, data, Decimal('0'))

    @property
    def applytime(self):
        """
            累计借款申请次数
        """
        data = len(self.published_applications)
        return data

    @property
    def refusetimes(self):
        """
            累计借款驳回次数
        """
        data = [ 1 for applications in self.published_applications
                if applications.status == get_enum('APPLICATION_RISKCONTROL_TRIAL_FAILED')]

        return functools.reduce(operator.add, data, Decimal('0'))

    @property
    def curloantimes(self):
        """
            当前成功借款笔数
        """
        data = [1 for project in self.published_projects
                if project.status in (get_enum('PROJECT_PENDING'),
                    get_enum('PROJECT_REPAYING'))]
        return functools.reduce(operator.add, data, Decimal('0'))

    @property
    def curloanmodey(self):
        """
            当前成功借款总额
        """
        data = [repayment.amount for repayment in self.repayments
                if repayment.status == get_enum('REPAYMENT_START')]
        return functools.reduce(operator.add, data, Decimal('0.0'))

    @property
    def curwaitpaymone(self):
        """
            当前待还本息总额
        """
        data = [(repayment.amount + repayment.interest - repayment.repaid_amount)
                for repayment in self.repayments
                if repayment.status == get_enum('REPAYMENT_START')]
        return functools.reduce(operator.add, data, Decimal('0.0'))

    @property
    def alllocaltime(self):
        """
            累计成功借款笔数
        """
        data = [1 for project in self.published_projects
                if project.status in (get_enum('PROJECT_PENDING'),
                    get_enum('PROJECT_REPAYING'), get_enum('PROJECT_DONE'),
                    get_enum('PROJECT_PREPAYMENT'))]
        return functools.reduce(operator.add, data, Decimal('0'))

    @property
    def alllocanmodey(self):
        """
            累计成功借款总额
        """
        data = [repayment.amount for repayment in self.repayments]
        return functools.reduce(operator.add, data, Decimal('0.0'))

    @property
    def allrepaymoney(self):
        """
            累计还款本息总额
        """
        data = [repayment.repaid_amount for repayment in self.repayments]
        return functools.reduce(operator.add, data, Decimal('0.0'))

    @property
    def total_amount(self):
        return (self.available_amount + self.investing_amount
                + self.investing_interest + self.blocked_amount)

    @property
    def trade_password_enable(self):
        return self.trade_password is not None

    def check_password(self, password):
        salt = '{}.{}'.format(password, service['SECRET_KEY']).encode('utf-8')
        return self.password == hashlib.sha512(salt).hexdigest()

    def check_trade_password(self, password):
        salt = '{}.{}'.format(password, service['SECRET_KEY']).encode('utf-8')
        return self.trade_password == hashlib.sha512(salt).hexdigest()

    def has_permission(self, permission):
        for group in self.groups:
            if group.has_permission(permission):
                return True
        return False

    def send_message(self, title, content, *, to_user):  # flake8: noqa
        message = Message()
        message.title = title
        message.content = content
        message.from_user = self
        message.to_user = to_user
        return message

    def calculate_cert_level(self):
        """
            1 - 3: C
            4 - 7: B
            8 - 10: A
            11 - 14: AA
            15: AAA
        """
        auths = Authentication.query.filter_by(user_id=self.id).all()
        auth_success = [i.id for i in auths if i.status]
        self.certify_level = self.level_map.get(str(len(auth_success)), 'AAA')

    def capital_deduct(self, amount, order=None, can_use_expe=True):
        """ 扣钱操作 """
        income_amount_invest = self.income_amount   # 回款金额使用了多少
        if can_use_expe:
            if self.active_amount >= amount:
                self.active_amount -= amount  # 活动资金扣费
            else:
                remain_amount = amount - self.active_amount
                self.active_amount = Decimal('0.00')
                self._deduct_amount_by_order(order, remain_amount)
        else:
            # 使用 充值金额 或回款金额
            self._deduct_amount_by_order(order, amount)

        income_amount_invest -= self.income_amount  # 回款金额差额（回款续投金额）
        return income_amount_invest

    def _deduct_amount_by_order(self, order, remain_amount):
        if not order:
            if self.deposit_amount >= remain_amount:
                self.deposit_amount -= remain_amount
            else:
                remain_amount -= self.deposit_amount
                self.deposit_amount = Decimal('0.00')
                self.income_amount -= remain_amount
        else:
            if self.income_amount >= remain_amount:
                self.income_amount -= remain_amount
            else:
                remain_amount -= self.income_amount
                self.income_amount = Decimal('0.00')
                self.deposit_amount -= remain_amount

    def capital_blocked(self, amount, order=None):
        self.capital_deduct(amount=amount, order=order)
        self.blocked_amount += amount


m2m_project_level_show = Table(
    'm2m_project_user_level_show', Base.metadata,
    Column('user_level_id', Integer, ForeignKey('auth_user_level.id')),
    Column('project_id', Integer, ForeignKey('lending_project.id'))
)


m2m_project_level_allow = Table(
    'm2m_project_user_level_allow', Base.metadata,
    Column('user_level_id', Integer, ForeignKey('auth_user_level.id')),
    Column('project_id', Integer, ForeignKey('lending_project.id'))
)



class UserLevel(Base):
    __tablename__ = 'auth_user_level'

    id = Column(Integer, primary_key=True)
    name = Column(Unicode(16), nullable=False)
    is_special = Column(Boolean, default=False)
    is_income_reward = Column(Boolean, default=False)
    is_invest_reward = Column(Boolean, default=False)
    is_friend_reward = Column(Boolean, default=False)
    is_first_deposit_reward = Column(Boolean, default=False)
    is_first_invest_reward = Column(Boolean, default=False)
    is_show = Column(Boolean, default=True)
    is_auto_adjust = Column(Boolean, default=False)
    level_amount = Column(
        postgresql.NUMERIC(19, 2), default=Decimal('0.0'), nullable=False)
    description = Column(UnicodeText)

    project_show = relationship('Project', secondary=m2m_project_level_show,
                            backref=backref('project_level_show',
                                            order_by='UserLevel.level_amount'))
    project_allow = relationship('Project', secondary=m2m_project_level_allow,
                            backref=backref('project_level_allow',
                                            order_by='UserLevel.level_amount'))

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<UserLevel "{}">'.format(self.name)


class UserLevelLog(Base):
    __tablename__ = 'auth_user_level_log'

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey('auth_user.id'))
    user = relationship('User', backref='level_log')

    level_id = Column(Integer, ForeignKey('auth_user_level.id'))
    level = relationship('UserLevel')

    is_auto_adjust = Column(Boolean, default=True)  # 是否自动调整

    description = Column(UnicodeText)
    added_at = Column(DateTime, default=datetime.datetime.now, nullable=False)



class SourceWebsite(Base):
    __tablename__ = 'auth_source_website'

    id = Column(Integer, primary_key=True)
    name = Column(Unicode(32), nullable=False)
    puthin = Column(Unicode(32), nullable=False)
    key = Column(Unicode(32))
    password = Column(Unicode(32), nullable=False)
    added_at = Column(DateTime, default=datetime.datetime.now, nullable=False)

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<SourceWebsite "{}">'.format(self.id)

    @property
    def total_user(self):
        """
            用户数量
        """
        return len(self.source_users)


class RealnameAuth(Base):
    __tablename__ = 'auth_realname_auth'

    id = Column(Integer, primary_key=True)
    realname = Column(Unicode(32), nullable=False)
    idcard = Column(Unicode(20), nullable=False)
    result = Column(Unicode(16), server_default='不一致', nullable=False)
    user_id = Column(Integer, ForeignKey('auth_user.id'))
    user = relationship('User', backref='realname_auths')
    added_at = Column(DateTime, default=datetime.datetime.now, nullable=False)


@event.listens_for(User, 'after_update')
def check_user_after_update(mapper, connection, user):
    if (
        user.blocked_amount < Decimal('0') or
        user.active_amount < Decimal('0') or
        user.income_amount < Decimal('0') or
        user.deposit_amount < Decimal('0')
    ):
        # 资金出现负数 发送邮件
        from leopard.apps.service.tasks import send_email

        title = '用户资金出现负数'
        content = '用户id:{}'.format(user.id)
        to_email = '314169744@qq.com'
        send_email.delay(title, content, to_email=to_email)


class UserFactory(SQLAlchemyModelFactory):
    FACTORY_FOR = User
    FACTORY_SESSION = db_session

    username = factory.Sequence(lambda n: '模拟用户{}'.format(n))
    phone = factory.Sequence(lambda n: '188{:08}'.format(n))
    friend_invitation = factory.LazyAttribute(
        lambda e: base64.b64encode(sign(e.username.encode('utf-8'),
                                        service['SECRET_KEY'],
                                        salt='friend')
                                   ).decode('utf-8').replace('=', ''))
    password = 'toor'
    trade_password = 'sdf'
    is_active = True
    deposit_amount = Decimal('800000')
