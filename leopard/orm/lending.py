import datetime
import random
import factory
import dateutil
import dateutil.relativedelta
import logging
import sqlalchemy

from decimal import Decimal

from leopard.core.config import get_config

from factory.alchemy import SQLAlchemyModelFactory
from sqlalchemy import (Column, DateTime, Float, ForeignKey, Integer, Unicode,
                        UnicodeText, Boolean, func, Table)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import backref, relationship
from sqlalchemy.sql import func as sql_func
from leopard.core.orm import Base, db_session
from leopard.helpers import (get_enum, average_capital_plus_interest,
                             float_quantize_by_two)
from leopard.conf import consts
from leopard.comps.redis import get_redis
from leopard.orm.social import Message
from leopard.orm.account import Log
from leopard.orm.system import Config

from leopard.services.restrict.account import deduct_experience_amount

service = get_config('leopard.apps.service')
project_config = get_config('project')
logger = logging.getLogger('rotate')
redis = get_redis()


class FinMobileApplication(Base):
    __tablename__ = 'lending_mobile_finapplication'

    id = Column(Integer, primary_key=True)
    name = Column(Unicode(64))
    idcard = Column(Unicode(32))
    school = Column(Unicode(64))
    grade = Column(Unicode(8))
    phone = Column(Unicode(16))
    amount = Column(postgresql.NUMERIC(19, 2), default=0.0, nullable=False)
    term = Column(Unicode(64))

    user_id = Column(Integer, ForeignKey('auth_user.id'), nullable=False)
    user = relationship('User', backref='mobile_finapplication',
                        foreign_keys=[user_id])

    added_at = Column(DateTime, default=func.now(), nullable=False)

    def __str__(self):
        return self.name


class FinApplication(Base):
    __tablename__ = 'lending_finapplication'

    id = Column(Integer, primary_key=True)
    uid = Column(Unicode(64))
    status = Column(Integer, default=get_enum('FINAPPLICATION_PENDING'),
                    nullable=False)
    amount = Column(postgresql.NUMERIC(19, 2), default=0.0, nullable=False)
    periods = Column(Integer, nullable=False)
    rate = Column(Float)

    loan_use_for = Column(Unicode(64), nullable=False)
    realname = Column(Unicode(64))
    idcard = Column(Unicode(32))
    school_name = Column(Unicode(64))
    school_address = Column(Unicode(64))
    address = Column(Unicode(64))
    # 学制
    edu_system = Column(Unicode(8))
    # 学信网密码
    edu_passwd = Column(Unicode(32))
    student_code = Column(Unicode(32))
    qq = Column(Unicode(16))
    wechat = Column(Unicode(16))

    mobile = Column(Unicode(16))
    tel = Column(Unicode(64))
    composite_rank = Column(Integer)
    class_size = Column(Integer)
    pluses = Column(Unicode(128))

    dad = Column(Unicode(32))
    dad_phone = Column(Unicode(16))
    dad_unit = Column(Unicode(64))
    dad_unit_address = Column(Unicode(64))
    dad_unit_phone = Column(Unicode(16))

    mum = Column(Unicode(32))
    mum_phone = Column(Unicode(16))
    mum_unit = Column(Unicode(64))
    mum_unit_phone = Column(Unicode(16))
    mum_unit_address = Column(Unicode(64))

    coacher = Column(Unicode(32))
    coacher_phone = Column(Unicode(16))
    schoolmate = Column(Unicode(32))
    schoolmate_phone = Column(Unicode(16))
    roommate = Column(Unicode(32))
    roommate_phone = Column(Unicode(16))
    added_at = Column(DateTime, default=datetime.datetime.now, nullable=False)
    end_at = Column(DateTime, nullable=True)
    added_ip = Column(postgresql.INET, nullable=False)

    repay_method_id = Column(
        Integer, ForeignKey('lending_repaymentmethod.id'), nullable=False)
    repay_method = relationship('RepaymentMethod', backref='finapplication')

    user_id = Column(Integer, ForeignKey('auth_user.id'), nullable=False)
    user = relationship('User', backref='published_finapplications',
                        foreign_keys=[user_id])

    auditor_id = Column(Integer, ForeignKey('auth_user.id'))
    auditor = relationship('User', backref='auditor_finapplications',
                           foreign_keys=[auditor_id])

    claim_id = Column(Integer, ForeignKey('auth_user.id'))
    claim = relationship('User', backref='claim_finapplications',
                         foreign_keys=[claim_id])

    project_id = Column(
        Integer, ForeignKey('lending_project.id'), nullable=True)
    project = relationship('Project', backref=backref('finapplication'))

    def __str__(self):
        return self.uid

    def __repr__(self):
        return self.uid

    @property
    def executing_plans(self):
        return FinApplicationPlan.query.filter_by(
            application_id=self.id,
            status=get_enum('FINAPPLICATION_PENDING')
        ).order_by('period').all()

    @property
    def executed_plans(self):
        return FinApplicationPlan.query.filter_by(
            application_id=self.id,
            status=get_enum('FINAPPLICATION_VERIFY_SUCCESS')
        ).order_by('period').all()

    @property
    def paid_periods(self):
        return len(self.executed_plans)

    def generate_uid(self):
        date_str = datetime.datetime.today().strftime("%Y%m%d")
        key = consts.FINAPPLICATION_UID.format(date_str)
        index = redis.incr(key)
        if index == 1:
            redis.expire(key, 86400)
        self.uid = "{}{:04}".format(date_str, index)

    def success(self):
        self.user.income_amount += self.amount
        self.claim.capital_deduct(self.amount)
        fundstr = ('[学仕贷申请通过] 学仕贷申请书编号:{uid}')
        description = fundstr.format(uid=self.uid)
        Log.create_log(self, amount=self.amount, description=description)

        fundstr = ('[学仕贷申请书借款发放] 学仕贷申请书编号:{uid}')
        description = fundstr.format(uid=self.uid)
        Log.create_log(self, amount=self.amount, user=self.claim,
                       description=description)

        # 6个月扣4%，12个月8%，18个月12%，24个月16%
        fee_rate = (self.periods / 6) * 0.04
        loan_fee = self.amount * Decimal(str(fee_rate))
        self.user.income_amount -= loan_fee
        fundstr = ('[学仕贷借款手续费] 借款金额:{} 费用:{} 费率:{}')
        description = fundstr.format(self.amount,
                                     float_quantize_by_two(loan_fee),
                                     fee_rate)
        Log.create_log(self, amount=loan_fee, description=description)

    def generate_plan(self):
        from leopard.core.repayment_plan import generate_finapplication_plans
        generate_finapplication_plans(self, self.repay_method.logic)


class FinApplicationPlan(Base):
    __tablename__ = 'lending_finapplication_plan'

    id = Column(Integer, primary_key=True)
    period = Column(Integer, nullable=False)
    amount = Column(postgresql.NUMERIC(19, 2), nullable=False)
    interest = Column(postgresql.NUMERIC(19, 2), nullable=False)
    status = Column(Integer, default=get_enum('FINAPPLICATION_PLAN_PENDING'),
                    nullable=False)
    plan_time = Column(DateTime, nullable=False)
    executed_time = Column(DateTime)

    application_id = Column(
        Integer, ForeignKey('lending_finapplication.id'), nullable=False)
    application = relationship(
        'FinApplication', backref=backref(
            'plans', order_by='FinApplicationPlan.period'))

    def __str__(self):
        return "{} - {}".format(self.id, self.plan_time)

    def __repr__(self):
        return '学仕贷还款计划 "{} - {}">'.format(self.id, self.plan_time)

    @property
    def user(self):
        return self.application.user.username

    @property
    def amount_interest(self):
        return self.amount + self.interest

    @classmethod
    def create_plan(cls, rate, np, amount, func):
        today = datetime.date.today()
        for counter, (amount, interest) in enumerate(func(rate, np, amount)):
            plan = cls()
            plan.period = counter + 1
            plan.amount = amount
            plan.interest = interest
            plan.plan_time = today + \
                dateutil.relativedelta.relativedelta(months=counter + 1)
            yield plan

    def is_overdue(self):
        if self.status != get_enum('FINAPPLICATION_PLAN_PENDING'):
            return False

        if self.plan_time > datetime.datetime.today():
            return False

        return True

    def query_overdue_fee(self):
        fee = 0
        if self.is_overdue():
            today = datetime.date.today()
            plan_date = datetime.date(year=self.plan_time.year,
                                      month=self.plan_time.month,
                                      day=self.plan_time.day)
            difference = today - plan_date
            if difference.days > 0:
                rate = Config.get_decimal('FINAPPLICATION_OVERDUE_RATE')
                fee = self.amount_interest * rate * difference.days
        return fee

    def repay(self):
        logfmt = '[FinApplicationPlan Repay] Plan: {}'
        logger.info(logfmt.format(self.id))

        if self.status == get_enum('FINAPPLICATION_PLAN_PENDING'):
            now = datetime.datetime.now()

            self.repay_amount()
            self.repay_overdue_fee()
            self.executed_time = now
            self.status = get_enum('FINAPPLICATION_PLAN_DONE')
            self.repay_message()
            logger.info('[Plan Repay Success] Plan: {}'.format(self.id))
        else:
            logger.info('[Plan Repay Success] Plan: {}'.format(self.id))

    def repay_amount(self):
        amount = self.amount + self.interest
        user = self.application.user
        if user.investing_amount < user.experience_amount:
            diff_amount = user.experience_amount - user.investing_amount
            user.active_amount -= diff_amount
            user.capital_deduct(amount)
            user.active_amount += diff_amount
        else:
            user.capital_deduct(amount)
        fundstr = ('[还款操作] 学仕贷申请书编号:{uid}, 第{period}期, 本金:{a'
                   'mount}元, 利息:{interest}元')
        description = fundstr.format(
            uid=self.application.uid,
            period=self.period,
            amount=float_quantize_by_two(self.amount),
            interest=float_quantize_by_two(self.interest))
        Log.create_log(self.application, amount=amount,
                       description=description)

        self.application.claim.income_amount += amount
        fundstr = ('[收款操作] 用户: {user}, 学仕贷申请书编号'
                   ':{uid}, 第{period}期, 本金:{amount}元, 利息:{interest}元')
        description = fundstr.format(
            user=user.username,
            uid=self.application.uid,
            period=self.period,
            amount=float_quantize_by_two(self.amount),
            interest=float_quantize_by_two(self.interest)
        )
        Log.create_log(user=self.application.claim, amount=amount,
                       description=description)

    def repay_overdue_fee(self):
        if self.is_overdue():
            amount = self.query_overdue_fee()
            self.application.user.capital_deduct(amount)
            fundstr = ('[还款逾期费用操作] 学仕贷申请书编号:{uid}, 第{period}'
                       '期, 逾期费用:{amount}元')
            description = fundstr.format(
                uid=self.application.uid,
                period=self.period,
                amount=float_quantize_by_two(amount)
            )
            Log.create_log(self.application, amount=amount,
                           description=description)

            self.application.claim.income_amount += amount
            fundstr = ('[收取还款逾期费用操作] 用户: {user}, 学仕贷申请书编号'
                       ':{uid}, 逾期费用:{amount}元')
            description = fundstr.format(
                user=self.application.user.username,
                uid=self.application.uid,
                period=self.period,
                amount=float_quantize_by_two(amount)
            )
            Log.create_log(user=self.application.claim, amount=amount,
                           description=description)

    def repay_message(self):
        amount = self.amount + self.interest

        title = '系统信息 - 还款通知！'
        contentfmt = ('尊敬的用户，您收到来自用户:{user}, 学仕贷申请书编号:'
                      '{uid}, 第{period}期的还款，金额{amount}元')
        content = contentfmt.format(
            user=self.application.user.username,
            uid=self.application.uid,
            period=self.period,
            amount=float_quantize_by_two(amount)
        )
        Message.system_inform(
            to_user=self.application.claim,
            title=title,
            content=content
        )

        contentfmt = ('尊敬的用户，您偿还了一笔借款(学仕贷申请书编号:{uid}, '
                      '第{period}期)，金额{amount}元。')
        content = contentfmt.format(uid=self.application.uid,
                                    period=self.period,
                                    amount=float_quantize_by_two(amount))
        Message.system_inform(to_user=self.application.user,
                              title=title, content=content)


class Application(Base):
    __tablename__ = 'lending_application'

    id = Column(Integer, primary_key=True)

    name = Column(Unicode(128), nullable=False)
    status = Column(
        Integer, default=get_enum('APPLICATION_INIT'), nullable=False)

    description = Column(UnicodeText)

    amount = Column(postgresql.NUMERIC(19, 2), default=0.0, nullable=False)
    rate = Column(Float, nullable=False)
    periods = Column(Integer, nullable=False)
    nper_type = Column(Integer, default=get_enum('MONTH_PROJECT'),
                       nullable=False)

    user_id = Column(Integer, ForeignKey('auth_user.id'), nullable=False)
    user = relationship('User', backref='published_applications',
                        foreign_keys=[user_id])

    guarantee_id = Column(Integer, ForeignKey('credit_guarantee.id'))
    guarantee = relationship('Guarantee', backref='applications')

    auditor_id = Column(Integer, ForeignKey('auth_user.id'))
    auditor = relationship('User', backref='guaranteed_applications',
                           foreign_keys=[auditor_id])

    added_at = Column(DateTime, default=datetime.datetime.now, nullable=False)
    added_ip = Column(postgresql.INET, nullable=False)

    repay_method_id = Column(
        Integer, ForeignKey('lending_repaymentmethod.id'), nullable=False)
    repay_method = relationship('RepaymentMethod', backref='application')

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<Application "{}">'.format(self.name)


class ApplicationFactory(SQLAlchemyModelFactory):
    FACTORY_FOR = Application
    FACTORY_SESSION = db_session

    name = factory.Sequence(lambda n: '模拟资金流转项目申请书{}'.format(n))
    amount = factory.Sequence(lambda n: n * 10000)
    status = get_enum('APPLICATION_PROJECT_PUBLISHED')
    rate = factory.LazyAttribute(lambda e: random.randrange(10, 18) / 12)
    periods = factory.LazyAttribute(
        lambda e: random.choice([1, 3, 6, 9, 12, 24, 36]))
    added_at = factory.Sequence(
        lambda n: (datetime.datetime.now() -
                   dateutil.relativedelta.relativedelta(months=1) +
                   datetime.timedelta(hours=n)))
    added_ip = '127.0.0.1'
    description = factory.LazyAttribute(lambda e: '{}的简短描述'.format(e.name))


class ProjectImages(Base):
    __tablename__ = 'lending_project_image'

    id = Column(Integer, primary_key=True)
    name = Column(Unicode(128), nullable=False, default='补充材料')
    image = Column(Unicode(1024))
    project_id = Column(
        Integer, ForeignKey('lending_project.id'), nullable=False)
    project = relationship('Project', backref='images')

    @staticmethod
    def bulkcreate(project, image_list):
        for item in image_list:
            image = ProjectImages()
            image.name = item.get('name')
            image.image = item.get('image')
            image.project = project
        db_session.commit()


m2m_project_risk_controls = Table(
    'm2m_project_risk_controls', Base.metadata,
    Column('risk_control_id', Integer, ForeignKey('lending_risk_control.id')),
    Column('project_id', Integer, ForeignKey('lending_project.id'))
)


class RiskControl(Base):
    __tablename__ = 'lending_risk_control'
    id = Column(Integer, primary_key=True)

    title = Column(Unicode(128), nullable=False)
    content = Column(UnicodeText)
    is_show = Column(Boolean, default=True, nullable=False)
    priority = Column(Integer, default=0, server_default='0')

    projects = relationship('Project', secondary=m2m_project_risk_controls,
                            backref=backref('risk_controls',
                                            order_by='RiskControl.priority'))

    def __str__(self):
        return self.title


m2m_project_spec = Table(
    'm2m_project_spec', Base.metadata,
    Column('project_spec_id', Integer,
           ForeignKey('lending_project_spec.id')),
    Column('project_id', Integer, ForeignKey('lending_project.id'))
)


class ProjectSpec(Base):
    __tablename__ = 'lending_project_spec'
    id = Column(Integer, primary_key=True)

    title = Column(Unicode(128), nullable=False)
    desc = Column(Unicode(128), nullable=False)
    is_show = Column(Boolean, default=True, nullable=False)
    priority = Column(Integer, default=0, server_default='0')

    projects = relationship('Project', secondary=m2m_project_spec,
                            backref=backref('specs',
                                            order_by='ProjectSpec.priority'))

    def __str__(self):
        return self.title


class Project(Base):
    __tablename__ = 'lending_project'

    id = Column(Integer, primary_key=True)

    uid = Column(Unicode(128), default='', server_default='')

    name = Column(Unicode(128), nullable=False)
    status = Column(Integer, default=get_enum('PROJECT_READY'),
                    nullable=False)
    is_show = Column(Boolean, default=True, nullable=False)
    nper_type = Column(Integer, default=get_enum('MONTH_PROJECT'),
                       nullable=False)
    password = Column(Unicode(32))

    description = Column(UnicodeText, nullable=False)
    use_of_funds = Column(UnicodeText, nullable=False)  # 资金用途
    payment_from = Column(UnicodeText, nullable=False)  # 还款来源
    category = Column(Integer, default=get_enum('COMMON_PROJECT'),
                      nullable=False)                   # 项目类别

    guaranty = Column(UnicodeText, nullable=False, default='请填写')  # 抵押物
    guarantee_info = Column(UnicodeText, nullable=False, default='请填写')  # 担保意见
    invest_award = Column(postgresql.NUMERIC(19, 4), nullable=False,
                          default=Decimal('0.0'))  # 投标奖励
    # 资产说明
    asset_description = Column(UnicodeText, nullable=False, default='请填写')

    amount = Column(postgresql.NUMERIC(19, 2), nullable=False)
    borrowed_amount = Column(postgresql.NUMERIC(19, 2), default=Decimal('0.0'),
                             nullable=False)
    rate = Column(Float, nullable=False)

    min_lend_amount = Column(postgresql.NUMERIC(19, 2), nullable=False)
    max_lend_amount = Column(postgresql.NUMERIC(19, 2), nullable=False)

    controls = Column(UnicodeText)

    periods = Column(Integer, nullable=False)

    user_id = Column(Integer, ForeignKey('auth_user.id'), nullable=False)
    user = relationship('User', backref='published_projects',
                        foreign_keys=[user_id])

    guarantee_id = Column(Integer, ForeignKey('credit_guarantee.id'))
    guarantee = relationship('Guarantee', backref='projects')

    added_at = Column(DateTime, default=datetime.datetime.now, nullable=False)
    added_ip = Column(postgresql.INET, nullable=False)
    bid_at = Column(DateTime, default=datetime.datetime.now)

    application_id = Column(
        Integer, ForeignKey('lending_application.id'), nullable=True)
    application = relationship(
        'Application', backref=backref('project', uselist=False))

    repaymentmethod_id = Column(
        Integer, ForeignKey('lending_repaymentmethod.id'), nullable=False)
    repaymentmethod = relationship('RepaymentMethod', backref='projects')

    type_id = Column(Integer, ForeignKey(
        'lending_project_type.id'), nullable=False)
    type = relationship('ProjectType', backref='projects')

    # project_detail_authentication
    use_project_attestation = Column(Boolean, default=True, server_default='1')
    income = Column(Unicode(128), default='', server_default='')
    idcard = Column(Unicode(128), default='', server_default='')
    household = Column(Unicode(128), default='', server_default='')
    credit_reporting = Column(Unicode(128), default='', server_default='')
    house_property_card = Column(Unicode(128), default='', server_default='')
    vehicle_license = Column(Unicode(128), default='', server_default='')
    guarantee_contract = Column(Unicode(128), default='', server_default='')
    counter_guarantee_contract = Column(Unicode(128), default='',
                                        server_default='')
    business_license = Column(Unicode(128), default='', server_default='')
    tax_registration_certificate = Column(Unicode(128), default='',
                                          server_default='')
    bank_account_license = Column(Unicode(128), default='', server_default='')
    organization_code_certificate = Column(Unicode(128), default='',
                                           server_default='')
    mortgaged_property_certification = Column(Unicode(128), default='',
                                              server_default='')
    field_certification = Column(Unicode(128), default='', server_default='')

    login_show = Column(Boolean, default=True, nullable=True)
    grade = Column(Integer, default=0)

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<Project "{}">'.format(self.name)

    @property
    def progress(self):
        temp = str(self.borrowed_amount / self.amount)
        return temp[:temp.find('.') + 5]

    def get_project_url(self):
        if self.category == get_enum('COMMON_PROJECT'):
            return '《<a href="/#!/invest/{}" target="_blank">{}（{}）</a>》'
        return '《<a href="/#!/invest/student/{}" target="_blank">{}（{}）</a>》'

    @property
    def filter_risk_controls(self):
        objs = RiskControl.query.filter(
            RiskControl.projects.any(id=self.id),
        ).filter_by(
            is_show=True
        ).all()
        return objs

    @property
    def filter_specs(self):
        objs = ProjectSpec.query.filter(
            ProjectSpec.projects.any(id=self.id),
        ).filter_by(
            is_show=True
        ).all()
        return objs

    @property
    def has_password(self):
        return self.password is not None and self.password is not ''

    @property
    def paid_periods(self):
        if not self.investments:
            return 0
        return len(self.investments[0].executed_plans)

    @property
    def certify(self):
        certifys = {}
        for i in self.user.authentications:
            certifys.update({i.type.logic: i.status})
        return certifys

    @property
    def lack_amount(self):
        return self.amount - self.borrowed_amount

    @property
    def remain_day(self):
        now = datetime.datetime.now()
        remain = self.valid_time - (now - self.added_at).days
        if remain < 0:
            return 0
        return remain

    @property
    def remain_bid_time(self):
        """投标剩余时间"""
        now = datetime.datetime.now()
        if self.bid_at > now and self.bid_at > self.added_at:
            remain = (self.bid_at - now).total_seconds()
            return remain
        else:
            return 0

    def current_period_amount(self):
        current = self.paid_periods + 1
        amount, = db_session.query(
            sql_func.sum(Plan.amount + Plan.interest)).filter(
            Investment.project_id == self.id,
            Plan.investment_id == Investment.id,
            Plan.period == current).first()
        return amount if amount else 0

    def current_period_capital(self):
        current = self.paid_periods + 1
        amount, = db_session.query(sql_func.sum(Plan.amount)).filter(
            Investment.project_id == self.id,
            Plan.investment_id == Investment.id,
            Plan.period == current).first()
        return amount if amount else 0

    def specify_period_amount(self, period):
        amount, = db_session.query(
            sql_func.sum(Plan.amount + Plan.interest)).filter(
            Investment.project_id == self.id,
            Plan.investment_id == Investment.id,
            Plan.period == period).first()
        return amount if amount else 0

    def remain_periods_capital(self):
        current = self.paid_periods + 1
        amount, = db_session.query(
            sql_func.sum(Plan.amount)).filter(
            Investment.project_id == self.id,
            Plan.investment_id == Investment.id,
            Plan.period > current).first()
        return amount if amount else 0

    def repay(self, period=0):
        for i in self.repayments:
            i.repay(period)

    def prepay_fine(self):
        rate = Config.get_decimal('COMMISSION_PROJECT_PREPAYMENT_RATE') / 100
        for i in self.investments:
            fine = i.amount * rate
            i.user.deposit_amount += fine

            title = '系统消息 - 提前还款违约金到达通知!'
            contentfmt = ('尊敬的用户，您投资的项目《{}》提前还款, 您投资了{}元, '
                          '您收到违约金{}元')
            content = contentfmt.format(
                self.name, float_quantize_by_two(i.amount),
                float_quantize_by_two(fine))
            Message.system_inform(to_user=i.user, title=title, content=content)

            fundstr = ('[提前还款]-违约金 项目:«{name}» id:{pid}, 违约金:{fine},'
                       '投资记录 id:{invest_id}')
            description = fundstr.format(
                pid=i.project.id, name=i.project.name,
                invest_id=i.id, fine=fine)
            Log.create_log(i, amount=fine, description=description)

    def extend_images(self):
        images = [
            {'image': getattr(self, i),
             'name': project_config['PROJECT_CERTIFY'][i]}
            for i in project_config['PROJECT_CERTIFY_LIST'] if getattr(self, i)
        ]
        self.relation_images = [
            {'image': i.image, 'name': i.name} for i in self.images
        ]
        self.relation_images.extend(images)


class ProjectType(Base):
    __tablename__ = 'lending_project_type'

    id = Column(Integer, primary_key=True)
    name = Column(Unicode(128), nullable=False)
    description = Column(UnicodeText)
    is_show = Column(Boolean, default=True, nullable=False)
    logic = Column(Unicode(128), nullable=False)
    type = Column(Integer)

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<ProjectType "{}">'.format(self.name)


class ProjectFactory(SQLAlchemyModelFactory):
    FACTORY_FOR = Project
    FACTORY_SESSION = db_session

    name = factory.Sequence(lambda n: '模拟资金流转项目{}'.format(n))
    guarantee = factory.LazyAttribute(lambda e: e.application.guarantee)
    use_of_funds = '资金用途'
    payment_from = '还款来源'
    # type = factory.LazyAttribute(lambda e: get_enum("PROJECT_TYPE_FLOW"))
    user = factory.LazyAttribute(lambda e: e.application.user)
    status = factory.LazyAttribute(lambda e: get_enum("PROJECT_INVESTING"))
    amount = factory.LazyAttribute(lambda e: e.application.amount)
    rate = factory.LazyAttribute(lambda e: e.application.rate)
    periods = factory.LazyAttribute(lambda e: e.application.periods)
    description = factory.LazyAttribute(lambda e: '{}的简短描述'.format(e.name))
    added_ip = '127.0.0.1'
    added_at = factory.Sequence(
        lambda n: (datetime.datetime.now() - datetime.timedelta(6)))
    min_lend_amount = 50
    max_lend_amount = factory.LazyAttribute(lambda e: e.amount)
    controls = '股权80% 劳斯莱斯幻影汽车 汤臣一品500方别墅'


class Plan(Base):
    __tablename__ = 'lending_plan'

    id = Column(Integer, primary_key=True)
    period = Column(Integer, nullable=False)
    amount = Column(postgresql.NUMERIC(19, 2), nullable=False)
    interest = Column(postgresql.NUMERIC(19, 2), nullable=False)
    status = Column(Integer, default=get_enum('PLAN_PENDING'), nullable=False)
    plan_time = Column(DateTime, nullable=False)
    is_advance = Column(Boolean, default=False)
    executed_time = Column(DateTime)

    investment_id = Column(
        Integer, ForeignKey('lending_investment.id'), nullable=False)
    investment = relationship(
        'Investment', backref=backref('plans', order_by='Plan.period'))

    def __str__(self):
        return self.investment.project.name

    def __repr__(self):
        return '<Plan "{}">'.format(self.plan_time)

    @property
    def project_category(self):
        return self.investment.project.category

    @property
    def project_id(self):
        return self.investment.project.id

    @property
    def project_name(self):
        return self.investment.project.name

    @property
    def nper_type(self):
        return self.investment.project.nper_type

    @staticmethod
    def create_plan(rate, np, amount, func):
        today = datetime.date.today()
        for counter, (amount, interest) in enumerate(func(rate, np, amount)):
            plan = Plan()
            plan.period = counter + 1
            plan.amount = amount
            plan.interest = interest
            plan.plan_time = today + \
                dateutil.relativedelta.relativedelta(months=counter + 1)
            yield plan

    def repay(self):
        """ 还款计划 还款 """
        from leopard.core import business

        now = datetime.datetime.now()
        user = self.investment.repayment.user
        amount = self.amount + self.interest
        logger.info(
            '[Plan Repay Start] Plan: {}, Amount: {}'.format(self.id, amount))
        interest_management_fee_rate = Config.get_decimal(
            'COMMISSION_INVEST_LENDER_RATE') / 100
        interest_management_fee_fixed = Config.get_decimal(
            'COMMISSION_INVEST_LENDER_FIXED')
        commission = self.interest * \
            interest_management_fee_rate + interest_management_fee_fixed

        logfmt = '[Plan Repay] Plan: {}, Amount: {} ,Commission: {}'
        logger.info(logfmt.format(self.id, amount, commission))

        if self.status != get_enum('PLAN_PENDING'):
            return

        if user.investing_amount < user.experience_amount:
            diff_amount = user.experience_amount - user.investing_amount
            user.active_amount -= diff_amount
            user.capital_deduct(amount)
            user.active_amount += diff_amount
        else:
            user.capital_deduct(amount)

        fundstr = ('[还款操作] 项目:«{pname}» id:{pid}, 本金:{amount}元,'
                   '利息:{interest}元, 查看'
                   '<a href="/#!/account/funding/repayment">还款记录</a>')
        description = fundstr.format(
            pname=self.investment.project.name,
            pid=self.investment.project.id,
            amount=float_quantize_by_two(self.amount),
            interest=float_quantize_by_two(self.interest))

        Log.create_log(self.investment.repayment, amount=amount,
                       description=description)

        # 还款发放好友投资奖励
        # 一次付息到期还款就将  奖励金额 x 期数 在第一次发放 其他方式每次还息的时候给一次奖励
        project = self.investment.project
        fmt = ('[还款操作-好友投资奖励] 投资人:{} id:{}, '
               'Plan.repay 项目:{} 还款方式:{} 当前Plan期数:{} investment.amount:{}')
        logger.info(fmt.format(
                    self.investment.user,
                    self.investment.user.id,
                    project, project.repaymentmethod.logic,
                    self.period, self.investment.amount))

        if project.repaymentmethod.logic == 'interest_first':
            if self.period == 1 and not self.investment.previous:
                business.friend_invest_award(self.investment.user,
                                             self.investment,
                                             self.investment.amount,
                                             periods=project.periods)
        elif not self.investment.previous:
            business.friend_invest_award(self.investment.user,
                                         self.investment,
                                         self.investment.amount)

        self.investment.repayment.repaid_amount += amount
        self.investment.return_amount += amount

        balance_amount = deduct_experience_amount(self.investment, self.amount)
        self.investment.user.income_amount += balance_amount
        self.investment.user.deposit_amount += self.interest

        fundstr = ('[收款操作] 项目:«{pname}» id:{pid}, 本金:{amount}元,'
                   '利息:{interest}。查看<a href="/#!/account/funding/lending">'
                   '待收记录</a>。')

        description = fundstr.format(
            pname=self.investment.project.name,
            pid=self.investment.project.id,
            amount=float_quantize_by_two(balance_amount),
            interest=float_quantize_by_two(self.interest))

        Log.create_log(self.investment,
                       amount=balance_amount + self.interest,
                       description=description)
        self.investment.user.deposit_amount -= commission

        fundstr = '[利息管理费] 项目:«{pname}» id:{pid}, 费用:{commission}'
        description = fundstr.format(
            pname=self.investment.project.name,
            pid=self.investment.project.id,
            commission=float_quantize_by_two(commission))
        Log.create_log(self.investment,
                       amount=float_quantize_by_two(commission),
                       description=description)

        self.executed_time = now
        self.status = get_enum('PLAN_DONE')

        title = '系统信息 - 自动还款通知！'
        contentfmt = ('尊敬的用户，您收到来自《{}》的还款，金额{}元，扣除利息管理费{}元。'
                      '查看最近<a href="/#!/user/investment">待收详情</a>。')
        content = contentfmt.format(
            self.investment.project.name, float_quantize_by_two(amount),
            float_quantize_by_two(commission))
        Message.system_inform(
            to_user=self.investment.user, title=title, content=content)

        contentfmt = ('尊敬的用户，您偿还了《{}》的一笔借款，金额{}元。查看最近'
                      '<a href="/#!/user/repayment-detail?id={}">还款详情</a>。')
        content = contentfmt.format(
            self.investment.project.name,
            float_quantize_by_two(amount), self.investment.project.id)
        Message.system_inform(to_user=self.investment.repayment.user,
                              title=title, content=content)

        logger.info('[Plan Repay Success] Plan: {}'.format(self.id))

    def check_done(self):
        logger.info('[Plan Check Done Start] Plan: {}'.format(self.id))

        has_plan = Plan.query.filter(
            Plan.status == get_enum('PLAN_PENDING'),
            Plan.investment_id == Investment.id,
            Investment.id == self.investment.id
        ).all()
        is_repaying = self.investment.project.status == \
            get_enum('PROJECT_REPAYING')
        logfmt = ('[Plan Check Done Ready] Plan: {}, has_plan: {}, '
                  'is_repaying: {}')
        logger.info(logfmt.format(self.id, has_plan, is_repaying))

        if is_repaying and not has_plan:
            self.investment.repayment.status = get_enum('REPAYMENT_SUCCESSED')
            logfmt = ('[Plan Check Done Repayment Complete] Plan: {}, '
                      'Repayment: {}')
            logger.info(logfmt.format(self.id, self.investment.repayment.id))
            db_session.commit()

        project = Project.query.get(self.investment.project.id)
        flag = True
        for repayment in project.repayments:
            if repayment.status != get_enum('REPAYMENT_SUCCESSED'):
                flag = False
                break

        if flag:
            project.status = get_enum('PROJECT_DONE')
            logfmt = ('[Plan Check Done Project Complete] Plan: {}, '
                      'Project: {}')
            logger.info(logfmt.format(self.id, project.id))
            db_session.commit()
        logger.info('[Plan Check Done Success] Plan: {}'.format(self.id))


class Investment(Base):
    __tablename__ = 'lending_investment'

    id = Column(Integer, primary_key=True)

    status = Column(Integer, default=get_enum(
        'INVESTMENT_PENDING'), nullable=False)
    description = Column(UnicodeText)

    amount = Column(postgresql.NUMERIC(19, 2), nullable=False)
    origin_amount = Column(postgresql.NUMERIC(19, 2), default=Decimal('0.0'),
                           server_default='0')

    interest = Column(postgresql.NUMERIC(19, 2), nullable=False)
    commission = Column(postgresql.NUMERIC(19, 2), default=Decimal('0.0'))
    return_amount = Column(postgresql.NUMERIC(19, 2), default=Decimal('0.0'))
    discount = Column(postgresql.NUMERIC(19, 2), default=Decimal('0.0'),
                      server_default='0')

    rate = Column(Float, nullable=False)
    periods = Column(Integer, nullable=False)

    redpacket_id = Column(Integer, nullable=True)

    #  投资方式
    invest_from = Column(Integer, default=get_enum('MODE_OTHER'))

    user_id = Column(Integer, ForeignKey('auth_user.id'), nullable=False)
    user = relationship('User', backref='investments')

    project_id = Column(
        Integer, ForeignKey('lending_project.id'), nullable=False)
    project = relationship('Project', backref='investments')

    previous_id = Column(Integer, ForeignKey('lending_investment.id'))
    previous = relationship(
        'Investment', backref=backref('next', uselist=False), remote_side=[id])

    transfering_start_time = Column(DateTime)
    transfering_end_time = Column(DateTime)
    transfering_remain_periods = Column(Integer, default=0)

    added_at = Column(DateTime, default=datetime.datetime.now, nullable=False)
    # 最初投资记录添加时间
    origin_added_at = Column(DateTime, default=datetime.datetime.now)

    processed_at = Column(DateTime)
    added_ip = Column(postgresql.INET, nullable=False)

    def __str__(self):
        return self.project.name

    def __repr__(self):
        return '<Investment "{}">'.format(self.id)

    func_map = {
        'capital_final': 'common',
        'average_captial_plus_interest': 'common',
        'interest_first': 'special',
        'average_capital': 'common'
    }

    @property
    def transfer_expected_return(self):
        """ 债权转让预期收益 """
        discount = self.discount or 0
        if self.status == get_enum('INVESTMENT_TRANSFERED'):
            interest = self.interest
        else:
            interest = self.transfer_interest
        return discount + interest + self.transfer_invest_award

    @property
    def can_apply_transfer(self):
        """ 是否能够申请转让 """
        flag = True
        now = datetime.datetime.now()
        hold_limit = Config.get_int('TRANSFERING_HOLD_LIMIT')
        if now <= (self.added_at + datetime.timedelta(days=hold_limit)):
            flag = False
        return flag

    @property
    def has_previous(self):
        return True if self.previous else False

    @property
    def is_transfer(self):
        flag = False
        transfer_statue = [get_enum('INVESTMENT_TRANSFERING'),
                           get_enum('INVESTMENT_TRANSFERED')]
        if self.previous or self.next or self.status in transfer_statue:
            flag = True
        return flag

    @property
    def project_info(self):
        return self.project

    @property
    def received_interest(self):
        amount = 0
        for i in self.executed_plans:
            amount += i.interest
        return amount

    @property
    def category(self):
        return self.project.category

    @property
    def nper_type(self):
        return self.project.nper_type

    @staticmethod
    def create_investment(amount, project, user, status, commission,
                          total_interest, redpacket_id, invest_from=get_enum('MODE_OTHER')):
        investment = Investment()
        investment.amount = amount
        investment.status = status
        investment.commission = commission
        investment.rate = project.rate
        investment.user = user
        investment.interest = total_interest
        investment.periods = project.periods
        investment.project = project
        investment.redpacket_id = redpacket_id
        investment.added_ip = user.current_login_ip
        investment.invest_from = invest_from
        return investment

    def create_plan(self):
        plans = list(Plan.create_plan(self.rate, self.periods,
                     float(self.amount), average_capital_plus_interest))
        for plan in plans:
            self.plans.append(plan)

    @property
    def transfer_invest_award(self):
        invest_award_amount = self.origin_amount * \
            self.project.invest_award
        invest_award_amount = invest_award_amount * self._transfer_radio()
        return invest_award_amount.quantize(Decimal('1.00'))

    @property
    def remain_periods_capital(self):
        """ 剩余期数本金 """
        if self.status == get_enum('INVESTMENT_TRANSFERED'):
            return self.next.amount
        amount = Decimal('0')
        for i in self.executing_plans:
            amount += i.amount
        return amount

    @property
    def transfer_interest(self):
        """ 预期转让利息 """
        interest = 0
        if len(self.executing_plans) == 0:
            return 0

        now = datetime.date.today()
        repayment_logic = self.project.repaymentmethod.logic
        current_interest = 0
        remain_interest = 0

        if repayment_logic == 'interest_first':
            """ 一次付息到期还本只有两条plan """
            plans = Plan.query.filter_by(
                investment_id=self.id
            ).order_by('period')
            start_time = datetime.date(plans[0].plan_time.year,
                                       plans[0].plan_time.month,
                                       plans[0].plan_time.day)
            end_time = datetime.date(plans[1].plan_time.year,
                                     plans[1].plan_time.month,
                                     plans[1].plan_time.day)
            current_interest = self.interest

        elif repayment_logic in {'capital_final',
                                 'average_capital',
                                 'average_captial_plus_interest'}:
            """ 有多条plan, 取未还第一条 """
            plans = self.executing_plans
            end_time = datetime.date(plans[0].plan_time.year,
                                     plans[0].plan_time.month,
                                     plans[0].plan_time.day)
            start_time = end_time + dateutil.relativedelta.relativedelta(
                months=-1)
            current_interest = plans[0].interest
            remain_interest = sum([i.interest for i in plans[1:]])

        ratio = (end_time - now).days / (end_time - start_time).days
        interest = current_interest * Decimal(str(ratio)) + remain_interest
        return interest.quantize(Decimal('1.00'))

    @property
    def transfer_service_fee(self):
        """ 债权转让服务费 """
        if Config.get_bool('COMMISSION_ASSIGNER_ENABLE'):
            assigner_rate = Config.get_decimal('COMMISSION_ASSIGNER_RATE')
            fixed = Config.get_decimal('COMMISSION_ASSIGNER_FIXED')
            fee = '固额 {} 元，利率 {} %'.format(fixed, assigner_rate)
        else:
            fee = '0 元（活动期间免费）'
        return fee

    def common(self, current, investment, repayment, total_interest,
               executing_plans, current_interest, now):
        """ 债权转让还款利息 通用 """
        plan = Plan()
        plan.period = 1
        plan.amount = current.amount
        plan.interest = current.interest - current_interest
        plan.plan_time = current.plan_time
        plan.investment = investment
        current.amount = 0
        current.interest = current_interest
        for index, i in enumerate(executing_plans[1:]):
            i.period = index + 2
            i.investment = investment
            total_interest += i.interest
        investment.interest = total_interest
        repayment.interest = total_interest
        return Decimal('0')

    def special(self, current, investment, repayment, total_interest,
                executing_plans, current_interest, now):
        """ 债权转让还款利息 特殊 一次付息到期还本"""
        plans = Plan.query.filter(
            Plan.investment_id == self.id
        ).order_by('period')

        last_plan = self.executed_plans[0]
        start_time = plans[0].plan_time
        end_time = plans[1].plan_time
        start_time = datetime.date(start_time.year, start_time.month,
                                   start_time.day)
        end_time = datetime.date(end_time.year, end_time.month, end_time.day)
        d = datetime.date.today()
        ratio = (end_time - d).days / (end_time - start_time).days
        fixed_amount = last_plan.interest * Decimal(str(ratio))

        last_plan.interest = last_plan.interest - fixed_amount

        plan = Plan()
        plan.period = 1
        plan.amount = 0
        plan.interest = fixed_amount
        plan.plan_time = now
        plan.investment = investment

        self.executing_plans[0].investment = investment
        current.investment = investment
        investment.interest = plan.interest
        repayment.interest = plan.interest
        return fixed_amount

    def transfer(self, to_user, capital_deduct_order):
        """ 债权转让 """
        prefix = '[债权转让] investment: {}, to_user: {};'.format(
            self.id, to_user.id)
        logger.info('{} 开始.'.format(prefix))

        executing_plans, remain_periods_capital, last_plan_time, \
            current_interest, total_interest, now,\
            current = self._transfer_calculate()
        fmt = ('{} executing_plans: {}, remain_periods_capital: {}, '
               'last_plan_time: {}, current_interest: {}, '
               'total_interest: {}, current: {}')
        logger.info(fmt.format(prefix, executing_plans, remain_periods_capital,
                               last_plan_time, current_interest,
                               total_interest, current))

        # 创建投资记录
        investment = Investment.create_investment(
            remain_periods_capital, self.project, to_user,
            get_enum('INVESTMENT_SUCCESSED'), Decimal('0'), total_interest,
            redpacket_id=None)

        if self.previous:
            logger.info('{} 二次债权转让'.format(prefix))
            investment.origin_added_at = self.origin_added_at
            self.origin_amount = self.previous.origin_amount
            investment.origin_amount = self.origin_amount
        else:
            logger.info('{} 首次债权转让'.format(prefix))
            investment.origin_added_at = self.added_at
            self.origin_amount = self.amount
            investment.origin_amount = self.origin_amount

        # 原项目已还金额增加
        self.return_amount += remain_periods_capital

        investment.added_at = now
        investment.previous = self
        investment.added_ip = to_user.current_login_ip
        repayment = Repayment.create_repayment(
            remain_periods_capital, get_enum('REPAYMENT_START'),
            self.project, investment.project.user, investment, total_interest)

        logger.info('{} 本项目还款方法是{}'.format(
            prefix, self.project.repaymentmethod.logic))
        # 转移plan，并计算利息
        func = getattr(self, self.func_map[self.project.repaymentmethod.logic])
        fixed_amount = func(current, investment, repayment, total_interest,
                            executing_plans, current_interest, now)
        logger.info('{} fixed_amount: {}.'.format(prefix, fixed_amount))

        description = '[债权转让]-购买操作'
        Log.create_log(investment, description=description)

        # 债权转让 本金回收到 充值金额，防止转让人去投资其他项目获得 续投奖励
        self.user.deposit_amount += remain_periods_capital
        description = '[债权转让]-转让人收款操作 金额:{amount}'.format(
            amount=remain_periods_capital)
        Log.create_log(self, description=description,
                       amount=remain_periods_capital)

        self._transfor_invest_award(investment, to_user,
                                    remain_periods_capital,
                                    capital_deduct_order)

        if fixed_amount != Decimal('0'):
            # 扣除首月利息 (一次付息到期还本)
            self.user.deposit_amount -= fixed_amount

            fundstr = '[债权转让]-扣除首月利息 (一次付息到期还本), 利息:{:.2f}'
            description = fundstr.format(fixed_amount)
            Log.create_log(self, amount=fixed_amount, description=description)

        self.status = get_enum('INVESTMENT_TRANSFERED')

        self._assigner_commission(remain_periods_capital)

        logger.info('[债权转让] 结束')
        return investment

    def _transfer_calculate(self):
        """ 债权转让计算 """
        executing_plans = Plan.query.filter(
            Plan.investment_id == self.id,
            Plan.status == get_enum('PLAN_PENDING')).order_by('period').all()
        now = datetime.datetime.now()
        remain_periods_capital = self.remain_periods_capital

        current = executing_plans[0]
        end_time = current.plan_time
        start_time = end_time + dateutil.relativedelta.relativedelta(
            months=-1)

        start_time = datetime.date(start_time.year, start_time.month,
                                   start_time.day)
        end_time = datetime.date(end_time.year, end_time.month, end_time.day)
        d = datetime.date.today()

        ratio = (d - start_time).days / (end_time - start_time).days
        ratio = Decimal(str(ratio))

        current_interest = ratio * current.interest
        total_interest = current.interest - current_interest

        return (executing_plans, remain_periods_capital, start_time,
                current_interest, total_interest, now, current)

    def _transfer_radio(self):
        if len(self.executing_plans) == 0:
            return 0
        now = datetime.date.today()
        start_time = self.origin_added_at
        end_time = self.executing_plans[-1].plan_time
        start_time = datetime.date(start_time.year, start_time.month,
                                   start_time.day)
        end_time = datetime.date(end_time.year, end_time.month, end_time.day)

        if now > end_time:
            return 0

        denominator = (end_time - start_time).days
        if denominator == 0:
            return 0
        ratio = (end_time - now).days / denominator
        return Decimal(str(ratio))

    def _transfor_invest_award(self, investment, to_user,
                               remain_periods_capital, capital_deduct_order):
        """ 转让投标奖励 """
        # 投标奖励(投资金额 * 百分比)

        invest_award_amount = self.origin_amount * \
            self.project.invest_award
        invest_award_amount = invest_award_amount * self._transfer_radio()
        invest_award_amount = invest_award_amount.quantize(Decimal('1.00'))

        logfmt = ('[FlowTender - capital_change] 计算回款续投奖励开始：User({}):'
                  'active_amount:{}, income_amount:{}, deposit_amount:{}')
        logger.info(logfmt.format(to_user.id, to_user.active_amount,
                    to_user.income_amount, to_user.deposit_amount))

        to_user.capital_deduct(remain_periods_capital, capital_deduct_order)
        logfmt = ('[FlowTender - capital_change] 计算回款续投奖励结束：User({}):'
                  'active_amount:{}, income_amount:{}, deposit_amount:{}')
        logger.info(logfmt.format(to_user.id, to_user.active_amount,
                    to_user.income_amount, to_user.deposit_amount))

        if invest_award_amount != Decimal('0.0'):
            to_user.deposit_amount += invest_award_amount
            self.user.deposit_amount -= invest_award_amount

            description = '[债权转让]-扣除投标奖励 奖励:{:.2f}'.format(
                invest_award_amount)
            Log.create_log(self, amount=invest_award_amount,
                           description=description)

            description = '[债权转让]-获得投标奖励 奖励:{:.2f}'.format(
                invest_award_amount)
            Log.create_log(investment, amount=invest_award_amount,
                           description=description)

    def _assigner_commission(self, remain_periods_capital):
        """ 转让人手续费 """
        if Config.get_bool('COMMISSION_ASSIGNER_ENABLE'):
            assigner_rate = Config.get_decimal('COMMISSION_ASSIGNER_RATE')
            rate = assigner_rate / 100
            fixed = Config.get_decimal('COMMISSION_ASSIGNER_FIXED')
            commission = rate * remain_periods_capital + fixed
            self.user.deposit_amount -= commission

            description = '[债权转让]-服务费 费用:{:.2f}'.format(commission)
            Log.create_log(self, description=description, amount=commission)

    @property
    def executing_plans(self):
        return Plan.query.filter_by(
            investment_id=self.id,
            status=get_enum('PLAN_PENDING')).order_by('period').all()

    @property
    def executed_plans(self):
        return Plan.query.filter(
            Plan.investment_id == self.id,
            Plan.status != get_enum('PLAN_PENDING')).order_by('period').all()

    @property
    def expiration_time(self):
        """投资到期时间"""
        return self.origin_added_at + dateutil.relativedelta.relativedelta(
            months=self.project.periods) if self.project.nper_type == \
            get_enum('MONTH_PROJECT') else self.origin_added_at + \
            datetime.timedelta(days=self.project.periods)


class Repayment(Base):
    __tablename__ = 'lending_repayment'

    id = Column(Integer, primary_key=True)

    status = Column(Integer, default=get_enum('REPAYMENT_PENDING'))
    description = Column(UnicodeText)

    amount = Column(postgresql.NUMERIC(19, 2), nullable=False)
    interest = Column(postgresql.NUMERIC(19, 2), nullable=False)
    repaid_amount = Column(postgresql.NUMERIC(19, 2), default=Decimal('0.0'))

    rate = Column(Float, nullable=False)
    periods = Column(Integer, nullable=False)

    user_id = Column(Integer, ForeignKey('auth_user.id'), nullable=False)
    user = relationship('User', backref='repayments')

    project_id = Column(
        Integer, ForeignKey('lending_project.id'), nullable=False)
    project = relationship('Project', backref='repayments')

    investment_id = Column(
        Integer, ForeignKey('lending_investment.id'), nullable=False)
    investment = relationship('Investment',
                              backref=backref('repayment', uselist=False))

    added_at = Column(DateTime, default=datetime.datetime.now, nullable=False)

    def __str__(self):
        return self.project.name

    def __repr__(self):
        return '<Repayment "{}">'.format(self.id)

    @staticmethod
    def create_repayment(amount, status, project, user, investment,
                         total_interest):
        repayment = Repayment()
        repayment.amount = amount
        repayment.status = status
        repayment.project = project
        repayment.rate = project.rate
        repayment.periods = project.periods
        repayment.interest = total_interest
        repayment.user = user
        repayment.investment = investment
        return repayment

    @property
    def project_category(self):
        return self.project.category

    @property
    def plans(self):
        return self.investment.plans

    @property
    def nper_type(self):
        return self.project.nper_type

    @property
    def executing_plans(self):
        return self.investment.executing_plans

    @property
    def executed_plans(self):
        return self.investment.executed_plans

    def repay(self, period=0):
        if not self.executing_plans:
            return None
        plan = self.executing_plans[period]
        amount = plan.amount + plan.interest
        now = datetime.datetime.now()
        rate = Config.get_decimal('COMMISSION_INVEST_LENDER_RATE') / 100
        fixed = Config.get_decimal('COMMISSION_INVEST_LENDER_FIXED')
        commission = plan.interest * rate + fixed
        self.user.capital_deduct(amount)
        self.repaid_amount += amount

        fundsfmt = ('还款操作, 《{}（{}）》, 查看'
                    '<a href="/#!/account/funding/repayment">最近还款</a>。')

        description = fundsfmt.format(
            self.investment.project.name, self.investment.project.id)
        Log.create_log(self, amount=amount, description=description)
        self.investment.user.income_amount += plan.amount
        self.investment.user.deposit_amount += plan.interest

        fundsfmt = ('收款操作, 《{}（{}）》, 本金：{}元，利息：{}；查看'
                    '<a href="/#!/account/funding/lending">代收记录</a>。')
        description = fundsfmt.format(
            self.investment.project.name, self.investment.project.id,
            float_quantize_by_two(plan.amount),
            float_quantize_by_two(plan.interest))

        Log.create_log(self.investment, amount=amount, description=description)

        self.investment.user.income_amount -= commission

        fundstr = '[利息管理费] 项目:«{pname}» id:{pid}, 费用:{commission}'
        description = fundstr.format(
            pname=self.investment.project.name,
            pid=self.investment.project.id,
            commission=float_quantize_by_two(commission))
        Log.create_log(self.investment,
                       amount=float_quantize_by_two(commission),
                       description=description)
        self.investment.return_amount += amount

        plan.executed_time = now
        plan.status = get_enum('PLAN_DONE')
        if len(self.executing_plans) == 0:
            self.status = get_enum('REPAYMENT_SUCCESSED')
            self.investment.status = get_enum('INVESTMENT_DONE')
        return plan

    def prepayment_all(self, executing_plans=None):
        now = datetime.datetime.now()
        amount = 0

        if not executing_plans:
            executing_plans = self.executing_plans

        for plan in executing_plans:
            amount += plan.amount
            plan.interest = 0
            plan.executed_time = now
            plan.status = get_enum('PLAN_PREPAYMENT_DONE')

        # 注册体金判断
        balance_amount = deduct_experience_amount(self.investment, amount)
        self.investment.user.income_amount += balance_amount

        self.investment.return_amount += amount
        title = '系统信息 - 提前全额还款通知！'

        contentfmt = ('尊敬的用户，您对《{}》项目投资的{}元，项目所有人已经申请了'
                      '提前全款还款，您收到退回的本金{}元')
        content = contentfmt.format(self.project, self.amount, balance_amount)
        Message.system_inform(to_user=self.investment.user, title=title,
                              content=content)

        fundsfmt = '[提前还款] 收回本金:{} {}'.format(
            self.project.get_project_url()
        )
        description = fundsfmt.format(balance_amount, self.project.id,
                                      self.project.name)
        Log.create_log(self.investment, amount=balance_amount,
                       description=description)


class RepaymentMethod(Base):
    __tablename__ = 'lending_repaymentmethod'

    id = Column(Integer, primary_key=True)
    name = Column(Unicode(64), nullable=True)
    logic = Column(Unicode(64), nullable=True)
    is_show = Column(Boolean, default=True, nullable=True)
    priority = Column(Integer, default=0)

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<RepaymentMethod "{}">'.format(self.name)


class AutoInvestment(Base):
    __tablename__ = 'lending_autoinvestment'

    id = Column(Integer, primary_key=True)
    is_open = Column(Boolean, default=False, nullable=False)
    min_rate = Column(Integer, default=0, nullable=False)
    max_rate = Column(Integer, default=0, nullable=False)
    min_periods = Column(Integer, default=0, nullable=False)
    max_periods = Column(Integer, default=0, nullable=False)
    min_amount = Column(
        postgresql.NUMERIC(19, 2), default=Decimal('0.0'), nullable=False)
    max_amount = Column(
        postgresql.NUMERIC(19, 2), default=Decimal('0.0'), nullable=False)
    reserve_amount = Column(
        postgresql.NUMERIC(19, 2), default=Decimal('0.0'), nullable=False)

    user_id = Column(Integer, ForeignKey('auth_user.id'), nullable=False)
    user = relationship('User', backref=backref('autoinvest', uselist=False))

    def __str__(self):
        return self.id

    def __repr__(self):
        return '<AutoInvestment "{}">'.format(self.id)

    @property
    def max_allow_amount(self):
        max_allow_amount = Config.get_config('AUTO_INVESTMENT_MAXAMOUNT')
        max_allow_amount = Decimal(str(max_allow_amount))
        return max_allow_amount


    @property
    def sort_rownum(self):
        select_sql = sqlalchemy.select([AutoInvestIndex.id,
                                        func.row_number().over(
                                            order_by=AutoInvestIndex.id
                                        ).label('rownum')])
        auto_invest_rank = db_session.query(
            AutoInvestIndex, 'rownum').select_entity_from(
            select_sql).filter(AutoInvestIndex.id == self.auto_index.id).first()
        auto_rank = auto_invest_rank[1] if auto_invest_rank \
            else None
        return auto_rank


class AutoInvestmentFactory(SQLAlchemyModelFactory):
    FACTORY_FOR = AutoInvestment
    FACTORY_SESSION = db_session

    is_open = True


class AutoInvestIndex(Base):
    __tablename__ = 'lending_autoinvestindex'

    id = Column(Integer, primary_key=True)
    description = Column(UnicodeText)
    user_id = Column(Integer, ForeignKey('auth_user.id'), nullable=False)
    user = relationship('User', backref=backref('autoindex', uselist=False))
    auto_id = Column(Integer, ForeignKey('lending_autoinvestment.id'),
                     nullable=False)

    auto = relationship('AutoInvestment', backref=backref('auto_index',
                        uselist=False))

    def __str__(self):
        return self.id

    def __repr__(self):
        return '<AutoInvestIndex "{}">'.format(self.id)


class FinApplicationFactory(SQLAlchemyModelFactory):
    FACTORY_FOR = FinApplication
    FACTORY_SESSION = db_session

    amount = factory.Sequence(lambda n: n * 10000)
    rate = factory.LazyAttribute(lambda e: random.randrange(10, 18))
    periods = factory.LazyAttribute(
        lambda e: random.choice([1, 3, 6, 9, 12, 24, 36]))
    added_at = factory.Sequence(
        lambda n: (datetime.datetime.now() -
                   dateutil.relativedelta.relativedelta(weeks=1) +
                   datetime.timedelta(hours=n)))
    added_ip = '127.0.0.1'

    loan_use_for = factory.Sequence(lambda n: '贷款用途 - {}'.format(n))
    realname = factory.Sequence(lambda n: '真实姓名 - {}'.format(n))
    idcard = factory.Sequence(lambda n: '身份证 - {}'.format(n))
    school_name = factory.Sequence(lambda n: '学校名称 - {}'.format(n))
    school_address = factory.Sequence(lambda n: '学校地址 - {}'.format(n))
    address = factory.Sequence(lambda n: '居住地址 - {}'.format(n))
    edu_system = factory.Sequence(lambda n: '学籍 - {}'.format(n))
    edu_passwd = factory.Sequence(lambda n: '学信网 - {}'.format(n))
    student_code = factory.Sequence(lambda n: '学籍号 - {}'.format(n))
    qq = factory.Sequence(lambda n: 'qq号码 - {}'.format(n))
    wechat = factory.Sequence(lambda n: '微信号 - {}'.format(n))
    mobile = factory.Sequence(lambda n: '手机号码 - {}'.format(n))
    tel = factory.Sequence(lambda n: '家庭固话 - {}'.format(n))
    composite_rank = factory.Sequence(lambda n: n)
    class_size = factory.Sequence(lambda n: n)
    pluses = factory.Sequence(lambda n: '加分项 - {}'.format(n))

    dad = factory.Sequence(lambda n: '父亲姓名 - {}'.format(n))
    dad_phone = factory.Sequence(lambda n: '父亲手机 - {}'.format(n))
    dad_unit = factory.Sequence(lambda n: '父亲单位 - {}'.format(n))
    dad_unit_address = factory.Sequence(lambda n: '父亲单位地址 - {}'.format(n))
    dad_unit_phone = factory.Sequence(lambda n: '父亲单位电话 - {}'.format(n))

    mum = factory.Sequence(lambda n: '母亲姓名 - {}'.format(n))
    mum_phone = factory.Sequence(lambda n: '母亲手机 - {}'.format(n))
    mum_unit = factory.Sequence(lambda n: '母亲单位 - {}'.format(n))
    mum_unit_address = factory.Sequence(lambda n: '母亲单位地址 - {}'.format(n))
    mum_unit_phone = factory.Sequence(lambda n: '母亲单位电话 - {}'.format(n))

    coacher = factory.Sequence(lambda n: '辅导员姓名 - {}'.format(n))
    coacher_phone = factory.Sequence(lambda n: '辅导员手机 - {}'.format(n))

    schoolmate = factory.Sequence(lambda n: '同学姓名 - {}'.format(n))
    schoolmate_phone = factory.Sequence(lambda n: '同学手机 - {}'.format(n))

    roommate = factory.Sequence(lambda n: '舍友姓名 - {}'.format(n))
    roommate_phone = factory.Sequence(lambda n: '舍友手机 - {}'.format(n))

    repay_method_id = 2

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        session = cls.FACTORY_SESSION
        obj = target_class(*args, **kwargs)
        session.add(obj)
        obj.generate_uid()

        if obj.status == get_enum('FINAPPLICATION_VERIFY_SUCCESS'):
            db_session.commit()
            obj.success()
            obj.generate_plan()
        return obj


class ProjectPlan(Base):
    __tablename__ = 'lending_project_plan'

    id = Column(Integer, primary_key=True)
    status = Column(Integer, default=get_enum(
        'PROJECT_PLAN_PENDING'), nullable=False)
    period = Column(Integer, nullable=False)
    amount_interest = Column(postgresql.NUMERIC(19, 4), nullable=False)
    amount = Column(postgresql.NUMERIC(19, 4), nullable=False)
    interest = Column(postgresql.NUMERIC(19, 4), nullable=False)
    remain_amount = Column(postgresql.NUMERIC(19, 4), nullable=False)
    plan_time = Column(DateTime, nullable=False)
    executed_time = Column(DateTime)

    project_id = Column(
        Integer, ForeignKey('lending_project.id'), nullable=False)
    project = relationship('Project', backref='project_plans')

    user_id = Column(Integer, ForeignKey('auth_user.id'), nullable=False)
    user = relationship('User', backref='repay_plans')

    def __str__(self):
        return self.project.name

    def __repr__(self):
        return '<ProjectPlan "{}">'.format(self.id)

    def repay(self):
        for i in self.project.investments:
            plan = Plan.query.filter(Plan.status == get_enum('PLAN_PENDING'),
                                     Plan.period == self.period,
                                     Plan.investment_id == i.id).first()
            plan.repay()
        self.executed_time = datetime.datetime.now()
        self.status = get_enum('PROJECT_PLAN_DONE')

    def check_done(self):
        for i in self.project.investments:
            plan = Plan.query.filter(Plan.status == get_enum('PLAN_DONE'),
                                     Plan.period == self.period,
                                     Plan.investment_id == i.id).first()
            plan.check_done()

    def prepayment(self):
        self.executed_time = datetime.datetime.now()
        self.status = get_enum('PROJECT_PLAN_PREPAYMENT')
