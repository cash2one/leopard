import json
import datetime
import factory
from redis import Redis
from decimal import Decimal
from sqlalchemy import (Column, DateTime, ForeignKey, Integer, Unicode,
                        UnicodeText, Boolean)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import relationship, backref

from factory.alchemy import SQLAlchemyModelFactory

from leopard.core.orm import Base, db_session
from leopard.helpers import (get_enum, generate_order_number,
                             float_quantize_by_two)
from leopard.orm.social import Message
from leopard.orm.system import Config
from leopard.comps.redis import pool

redis = Redis(connection_pool=pool)


class DepositPlatform(Base):
    __tablename__ = 'account_deposit_platform'

    id = Column(Integer, primary_key=True)

    name = Column(Unicode(32), nullable=False)
    description = Column(UnicodeText)
    innerHTML = Column(UnicodeText, default='', nullable=False)
    is_show = Column(Boolean, default=True, nullable=False)
    is_pc = Column(Boolean, default=True)
    is_mobile = Column(Boolean, default=True)
    _dataset = Column(UnicodeText, default=[], nullable=False)
    logic = Column(Unicode(128), nullable=False)
    priority = Column(Integer, default=0, nullable=False)

    @property
    def dataset(self):
        return json.loads(self._dataset)

    @dataset.setter
    def dataset(self, value):
        self._dataset = json.dumps(value)

    def __repr__(self):
        return '{}'.format(self.name)


class Deposit(Base):
    __tablename__ = 'account_deposit'

    id = Column(Integer, primary_key=True)

    amount = Column(postgresql.NUMERIC(19, 2), nullable=False)
    commission = Column(
        postgresql.NUMERIC(19, 2), default=Decimal('0.0'), nullable=False)
    status = Column(
        Integer, default=get_enum('DEPOSIT_PENDING'), nullable=False)

    description = Column(UnicodeText)
    comment = Column(UnicodeText)

    user_id = Column(Integer, ForeignKey('auth_user.id'), nullable=False)
    user = relationship('User', backref='deposits')

    platform_order = Column(
        Unicode(80), default=generate_order_number, unique=True)
    platform_id = Column(
        Integer, ForeignKey('account_deposit_platform.id'), nullable=False)
    platform = relationship('DepositPlatform', backref='deposits')

    added_at = Column(DateTime, default=datetime.datetime.now, nullable=False)
    processed_at = Column(DateTime)
    bankcard_id = Column(Integer)

    def __repr__(self):
        return '<Deposit "{}">'.format(self.id)

    def award(self):
        award_ratio = Config.get_decimal('OFFLINE_AWARD_RATIO') / 1000
        award_amount = award_ratio * self.amount
        self.user.deposit_amount += award_amount

        fundstr = '[线下充值奖励] 订单号:‹{order_number}›, 奖励:{amount}'
        description = fundstr.format(
            order_number=self.platform_order,
            amount=award_amount)
        Log.create_log(self, amount=award_amount, description=description)

        title = '系统信息 - 线下充值奖励通知'
        contentfmt = ('尊敬的用户，您于{}提交的线下充值请求({}元), 已经审核完毕, '
                      '您将获得{}元的奖励。')
        content = contentfmt.format(
            self.added_at.strftime('%Y年%m月%d日 %H:%M:%S'),
            self.amount, float_quantize_by_two(award_amount))

        Message.system_inform(to_user=self.user, title=title, content=content)

    def accept(self):
        if self.status == get_enum('DEPOSIT_PENDING'):
            now = datetime.datetime.now()
            self.status = get_enum('DEPOSIT_SUCCESSED')
            self.user.deposit_amount += self.amount - self.commission
            self.processed_at = now

            fundstr = ('[充值成功] 订单号:‹{order_number}›,'
                       '充值平台:«{platform}», 充值:{amount}')
            description = fundstr.format(
                order_number=self.platform_order,
                platform=self.platform.name,
                amount=self.amount)

            Log.create_log(self, description=description)
            if self.commission:
                fundstr = ('[充值手续费] 订单号:‹{order_number}›, '
                           '充值平台:«{platform}», 手续费:{commission}')
                description = fundstr.format(
                    order_number=self.platform_order,
                    platform=self.platform.name,
                    commission=self.commission)
                Log.create_log(self, amount=self.commission,
                               description=description)

            title = '系统信息 - 充值成功通知'
            cfmt = '尊敬的用户，您于{}提交的充值请求({}元)，已经成功充值。'
            content = cfmt.format(
                self.added_at.strftime('%Y年%m月%d日 %H:%M:%S'), self.amount)
            Message.system_inform(to_user=self.user, title=title,
                                  content=content)

            offline_award = Config.get_bool('OFFLINE_AWARD_RATIO')
            if self.platform.logic == 'Offline' and offline_award:
                self.award()

    def reject(self):
        if self.status == get_enum('DEPOSIT_PENDING'):
            self.status = get_enum('DEPOSIT_FAILED')
            self.processed_at = datetime.datetime.now()

            title = '系统信息 - 充值失败通知'
            contentfmt = '尊敬的用户，您于{}提交的充值请求({}元)，充值失败。'
            content = contentfmt.format(
                self.added_at.strftime('%Y年%m月%d日 %H:%M:%S'), self.amount)
            Message.system_inform(to_user=self.user, title=title,
                                  content=content)


class DepositFactory(SQLAlchemyModelFactory):
    FACTORY_FOR = Deposit
    FACTORY_SESSION = db_session

    amount = factory.Sequence(lambda n: n * 100)
    commission = factory.LazyAttribute(lambda e: e.amount * 0.001)
    description = factory.Sequence(lambda n: '模拟充值记录{}'.format(n))
    added_at = factory.Sequence(
        lambda n: datetime.datetime.now() - datetime.timedelta(hours=n))


class Withdraw(Base):
    __tablename__ = 'account_withdraw'

    id = Column(Integer, primary_key=True)
    order_number = Column(Unicode(80), unique=True)

    amount = Column(postgresql.NUMERIC(19, 2), nullable=False)
    commission = Column(
        postgresql.NUMERIC(19, 2), default=Decimal('0.0'), nullable=False)
    status = Column(Integer, default=get_enum('WITHDRAW_PENDING'),
                    nullable=False)

    description = Column(UnicodeText)

    user_id = Column(Integer, ForeignKey('auth_user.id'), nullable=False)
    user = relationship('User', backref='withdraws')

    added_at = Column(DateTime, default=datetime.datetime.now, nullable=False)
    processed_at = Column(DateTime)

    def __repr__(self):
        return '<Withdraw "{}">'.format(self.id)

    def start(self):
        if self.status == get_enum('WITHDRAW_PENDING'):
            self.status = get_enum('WITHDRAW_START')
            self.processed_at = datetime.datetime.now()

    def accept(self):
        if self.status == get_enum('WITHDRAW_START'):
            self.status = get_enum('WITHDRAW_SUCCESSED')
            self.user.blocked_amount -= self.amount + self.commission
            self.processed_at = datetime.datetime.now()

            fundstr = '[提现成功] 订单号:‹{}›, 金额:{}'
            description = fundstr.format(self.order_number, self.amount)
            Log.create_log(self, description=description)

            if self.commission:
                fundstr = '[提现手续费] 订单号:‹{}›, 手续费:{}'
                description = fundstr.format(
                    self.order_number, self.commission)
                Log.create_log(self, amount=self.commission,
                               description=description)

            title = '系统信息 - 提现成功通知'
            contentfmt = '尊敬的用户，您于{time}提交的提现请求({amount}元)，提现成功。'
            content = contentfmt.format(
                time=self.added_at.strftime('%Y年%m月%d日 %H:%M:%S'),
                amount=self.amount + self.commission)

            Message.system_inform(to_user=self.user, title=title,
                                  content=content)
            redis.delete('withdraw:{}:active_amount'.format(self.order_number))
            redis.delete('withdraw:{}:deposit_amount'.format(
                         self.order_number))
            redis.delete('withdraw:{}:income_amount'.format(self.order_number))

            Bankcard.accept(self.order_number)

    def reject(self):
        withdraw_start = get_enum('WITHDRAW_START')
        withdraw_pending = get_enum('WITHDRAW_PENDING')

        if self.status in [withdraw_start, withdraw_pending]:
            active_amount = Decimal(
                redis.get('withdraw:{}:active_amount'.format(
                          self.order_number)).decode())
            deposit_amount = Decimal(
                redis.get('withdraw:{}:deposit_amount'.format(
                          self.order_number)).decode())
            income_amount = Decimal(
                redis.get('withdraw:{}:income_amount'.format(
                          self.order_number)).decode())

            self.status = get_enum('WITHDRAW_FAILED')
            self.user.blocked_amount -= self.amount + self.commission
            self.user.active_amount += active_amount
            self.user.deposit_amount += deposit_amount
            self.user.income_amount += income_amount
            self.processed_at = datetime.datetime.now()

            fundstr = ('[提现失败] 解冻资金 订单号:‹{order_number}›,'
                       '金额:{amount}, 手续费:{commission}')
            description = fundstr.format(
                order_number=self.order_number,
                amount=self.amount,
                commission=self.commission)
            Log.create_log(self, amount=self.commission,
                           description=description)

            title = '系统信息 - 提现失败通知'
            contentfmt = '尊敬的用户，您于{time}提交的提现请求({amount}元)，提现失败。'
            content = contentfmt.format(
                time=self.added_at.strftime('%Y年%m月%d日 %H:%M:%S'),
                amount=self.amount + self.commission)

            Message.system_inform(to_user=self.user, title=title,
                                  content=content)
            redis.delete('withdraw:{}:active_amount'.format(self.order_number))
            redis.delete('withdraw:{}:deposit_amount'.format(
                         self.order_number))
            redis.delete('withdraw:{}:income_amount'.format(self.order_number))

            Bankcard.cancel(self.order_number)

    def cancel(self):
        if self.status == get_enum('WITHDRAW_PENDING'):
            active_amount = Decimal(
                redis.get('withdraw:{}:active_amount'.format(
                          self.order_number)).decode())
            deposit_amount = Decimal(
                redis.get('withdraw:{}:deposit_amount'.format(
                          self.order_number)).decode())
            income_amount = Decimal(
                redis.get('withdraw:{}:income_amount'.format(
                          self.order_number)).decode())
            self.status = get_enum('WITHDRAW_FAILED')
            self.user.blocked_amount -= self.amount + self.commission
            self.user.active_amount += active_amount
            self.user.deposit_amount += deposit_amount
            self.user.income_amount += income_amount
            self.processed_at = datetime.datetime.now()

            fundstr = ('[提现取消] 解冻资金 订单号:‹{order_number}›, 金额:'
                       '{amount}, 手续费:{commission}')
            description = fundstr.format(
                order_number=self.order_number,
                amount=self.amount,
                commission=self.commission)
            Log.create_log(self, amount=self.commission,
                           description=description)
            redis.delete('withdraw:{}:active_amount'.format(self.order_number))
            redis.delete('withdraw:{}:deposit_amount'.format(
                         self.order_number))
            redis.delete('withdraw:{}:income_amount'.format(self.order_number))

            Bankcard.cancel(self.order_number)


class WithdrawFactory(SQLAlchemyModelFactory):
    FACTORY_FOR = Withdraw
    FACTORY_SESSION = db_session

    amount = factory.Sequence(lambda n: n * 100)
    commission = factory.LazyAttribute(lambda e: e.amount * 0.001)
    description = factory.Sequence(lambda n: '模拟提现记录{}'.format(n))
    added_at = factory.Sequence(
        lambda e: datetime.datetime.now() - datetime.timedelta(hours=e.id))


class Log(Base):
    __tablename__ = 'account_log'

    id = Column(Integer, primary_key=True)

    amount = Column(postgresql.NUMERIC(19, 2), nullable=False)
    active_amount = Column(postgresql.NUMERIC(19, 2), nullable=False)
    deposit_amount = Column(postgresql.NUMERIC(19, 2), nullable=False)
    income_amount = Column(postgresql.NUMERIC(19, 2), nullable=False)
    blocked_amount = Column(postgresql.NUMERIC(19, 2), nullable=False)
    guarded_amount = Column(postgresql.NUMERIC(19, 2), nullable=False)

    description = Column(UnicodeText)

    user_id = Column(Integer, ForeignKey('auth_user.id'), nullable=False)
    user = relationship('User', backref='logs')

    added_at = Column(DateTime, default=datetime.datetime.now, nullable=False)

    def __repr__(self):
        return '<Log "{}">'.format(self.id)

    @property
    def available_amount(self):
        return self.deposit_amount + self.income_amount + self.active_amount

    @staticmethod
    def create_log(entity=None, **kwargs):
        log = Log()
        log.user = kwargs['user'] if kwargs.get('user') else entity.user
        log.amount = kwargs['amount'] if 'amount' in kwargs else entity.amount
        log.active_amount = log.user.active_amount
        log.deposit_amount = log.user.deposit_amount
        log.income_amount = log.user.income_amount
        log.blocked_amount = log.user.blocked_amount
        log.guarded_amount = log.user.guarded_amount
        log.description = kwargs['description']
        return log


class Adjustment(Base):
    __tablename__ = 'account_adjustment'

    id = Column(Integer, primary_key=True)

    amount = Column(postgresql.NUMERIC(19, 2), nullable=False)

    description = Column(UnicodeText)

    user_id = Column(Integer, ForeignKey('auth_user.id'), nullable=False)
    user = relationship('User', backref='adjustment_historys',
                        foreign_keys=[user_id])

    adjustor_id = Column(Integer, ForeignKey('auth_user.id'), nullable=False)
    adjustor = relationship('User', backref='adjustment_operations',
                            foreign_keys=[adjustor_id])

    added_at = Column(DateTime, default=datetime.datetime.now, nullable=False)

    def __repr__(self):
        return '<Adjustment "{}">'.format(self.id)


class AdjustmentFactory(SQLAlchemyModelFactory):
    FACTORY_FOR = Adjustment
    FACTORY_SESSION = db_session

    amount = factory.Sequence(lambda n: n * 100)
    description = factory.Sequence(lambda n: '模拟人工调额{}'.format(n))


class Bankcard(Base):
    __tablename__ = 'account_bankcard'

    id = Column(Integer, primary_key=True)
    card = Column(Unicode(64), nullable=False)
    bank = Column(Unicode(64), nullable=False)
    user_id = Column(Integer, ForeignKey('auth_user.id'), nullable=False)
    user = relationship('User', backref=backref('bankcards'))
    is_show = Column(Boolean, default=True)
    need_amount = Column(postgresql.NUMERIC(19, 2), default=Decimal('0.0'))


    def __str__(self):
        return self.card

    def __repr__(self):
        return '<Bankcard "{}">'.format(self.id)

    @staticmethod
    def cancel(order_number):

        try:
            if redis.exists('withdraw:{}:bankcard_id'.format(
                              order_number)):
                bankcard = Bankcard.query.get(
                    int(redis.get('withdraw:{}:bankcard_id'.format(
                                  order_number)).decode()))
                if bankcard:
                    bankcard.need_amount += Decimal(
                        redis.get('withdraw:{}:need_amount'.format(
                                  order_number)).decode())
            redis.delete('withdraw:{}:bankcard_id'.format(order_number))
            redis.delete('withdraw:{}:need_amount'.format(order_number))
        except Exception as e:
            pass

    @staticmethod
    def accept(order_number):
        redis.delete('withdraw:{}:bankcard_id'.format(order_number))
        redis.delete('withdraw:{}:need_amount'.format(order_number))


class RedPacket(Base):
    __tablename__ = 'account_redpacket'

    id = Column(Integer, primary_key=True)
    name = Column(Unicode(32), nullable=True)
    amount = Column(postgresql.NUMERIC(19, 2), nullable=False)

    # 是否显示
    is_show = Column(Boolean, nullable=False, default=True,
                     server_default='1')
    invest_amount = Column(postgresql.NUMERIC(19, 2), nullable=True)
    never_expire = Column(Boolean, nullable=False, default=False,
                          server_default='0')

    added_at = Column(
        DateTime, default=datetime.datetime.now, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    use_at = Column(DateTime, nullable=True)       # 使用时间
    description = Column(Unicode(128), nullable=True)

    is_use = Column(Boolean, nullable=False, default=False)
    is_available = Column(Boolean, nullable=False, default=False)

    user_id = Column(Integer, ForeignKey('auth_user.id'), nullable=False)
    user = relationship('User', backref='redpackets')

    type_id = Column(
        Integer, ForeignKey('account_redpacket_type.id'), nullable=False)
    type = relationship('RedPacketType', backref='redpackets')

    def __str__(self):
        return self.added_at

    def __repr__(self):
        return '<RedPacket "{}">'.format(self.id)

    @property
    def is_expiry(self):
        if self.type.valid == 0 or self.is_use:
            return False
        else:
            now = datetime.datetime.now()
            if self.expires_at:
                return self.expires_at < now

            due_time = self.added_at + datetime.timedelta(days=self.type.valid)
            return now > due_time

    def calc_expires_at(self, valid):
        now = datetime.datetime.now()
        self.expires_at = now + datetime.timedelta(days=valid)

    @property
    def have_expired(self):
        """ 是否过期 """
        if not self.expires_at:
            return self.is_expiry

        now = datetime.datetime.now()
        return now > self.expires_at

    def refund(self):
        """ 红包退还 """
        self.is_use = False
        self.is_available = False


class RedPacketType(Base):
    __tablename__ = 'account_redpacket_type'

    id = Column(Integer, primary_key=True)
    name = Column(Unicode(128), nullable=False)
    logic = Column(Unicode(32))
    valid = Column(Integer, nullable=False)
    is_show = Column(Boolean, nullable=False, default=True)
    invest_amount = Column(postgresql.NUMERIC(19, 2), nullable=True)
    description = Column(UnicodeText)

    def __str__(self):
        return '{}类型'.format(self.name)

    def __repr__(self):
        return '<RedPacketType "{}">'.format(self.id)


class CodeRedPacket(Base):
    __tablename__ = 'account_code_redpacket'

    id = Column(Integer, primary_key=True)
    name = Column(Unicode(32), nullable=False)
    amount = Column(postgresql.NUMERIC(19, 2), nullable=False)
    invest_amount = Column(postgresql.NUMERIC(19, 2), nullable=True)
    code = Column(Unicode(16), unique=True, nullable=False)
    valid = Column(Integer, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    enabled = Column(Boolean, default=True)
    logic = Column(Unicode(16), nullable=False)
    description = Column(Unicode(128))
    added_at = Column(
        DateTime, default=datetime.datetime.now, nullable=False)

    def __str__(self):
        return '{}'.format(self.name)

    def __repr__(self):
        return '<CodeRedPacket "{}">'.format(self.id)

    def calc_expires_at(self, valid):
        now = datetime.datetime.now()
        self.expires_at = now + datetime.timedelta(days=valid)

    @property
    def have_expired(self):
        """ 是否过期  """
        now = datetime.datetime.now()
        return now > self.expires_at


class CodeRedPacketLog(Base):
    __tablename__ = 'account_code_redpacket_log'

    id = Column(Integer, primary_key=True)
    code = Column(Unicode(16), nullable=False)
    added_at = Column(
        DateTime, default=datetime.datetime.now, nullable=False)

    redpacket_id = Column(Integer, ForeignKey('account_code_redpacket.id'),
                          nullable=False)
    redpacket = relationship('CodeRedPacket', backref='logs')

    user_id = Column(Integer, ForeignKey('auth_user.id'), nullable=False)
    user = relationship('User', backref='codepacketlogs')

    def __str__(self):
        return '{}'.format(self.code)

    def __repr__(self):
        return '<CodeRedPacketLog "{}">'.format(self.id)


class RedPacketTypeFactory(SQLAlchemyModelFactory):
    FACTORY_FOR = RedPacketType
    FACTORY_SESSION = db_session

    name = factory.Sequence(lambda n: '模拟红包类型{}'.format(n))
    valid = 30
    description = factory.Sequence(lambda n: '模拟红包解释{}'.format(n))


class GiftPoint(Base):
    __tablename__ = 'account_giftpoint'

    id = Column(Integer, primary_key=True)
    points = Column(postgresql.NUMERIC(19, 2),
                    default=Decimal('0.0'), nullable=False)
    description = Column(UnicodeText)
    added_at = Column(DateTime, default=datetime.datetime.now,
                      nullable=False)
    toatl = Column(postgresql.NUMERIC(19, 2))
    user_id = Column(Integer, ForeignKey('auth_user.id'), nullable=False)
    user = relationship('User', backref='giftpoints')

    @staticmethod
    def add(user, points, description):
        giftpoint = GiftPoint()
        giftpoint.user = user
        giftpoint.points = points
        giftpoint.description = description
        giftpoint.toatl = user.gift_points

    def __str__(self):
        return self.id

    def __repr__(self):
        return '<GiftPoint "{}">'.format(self.id)
