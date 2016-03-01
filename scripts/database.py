from leopard.helpers.utils import init_config
import sqlalchemy

from redis import Redis
from sqlalchemy import event
from flask.ext.script import Manager

from leopard.orm import AutoInvestmentFactory, Guarantee
from leopard.orm import (User, DepositPlatform, FirendLink, Config, Banner,
                         RepaymentMethod, ProjectType, GroupFactory,
                         UserFactory, GuaranteeFactory, ApplicationFactory,
                         ProjectFactory, RedPacketTypeFactory)
from leopard.helpers import get_enum
from leopard.helpers import get_config
from leopard.core.orm import (create_all, create_engine, db_session, drop_all,
                              create_engine_with_binding)
from leopard.core import business
from leopard.orm.system import (receive_link_after, receive_config_after,
                                receive_banner_after)
from leopard.core.logging import setup_logging
from leopard.apps.service.tasks import automatic_investments

manager = Manager()
redis = Redis()


def remove_event():
    event.remove(FirendLink, 'after_insert', receive_link_after)
    event.remove(FirendLink, 'after_update', receive_link_after)
    event.remove(FirendLink, 'after_delete', receive_link_after)

    event.remove(Config, 'after_insert', receive_config_after)
    event.remove(Config, 'after_update', receive_config_after)

    event.remove(Banner, 'after_delete', receive_banner_after)
    event.remove(Banner, 'after_insert', receive_banner_after)
    event.remove(Banner, 'after_update', receive_banner_after)


@manager.command
def dci(config_id=None):
    remove_event()
    drop(config_id)
    create(config_id)
    init(config_id)


@manager.command
def deploy(config_id=None):
    remove_event()
    drop(config_id)
    create(config_id)
    base_init(config_id)


@manager.command
def create(config_id=None):
    engine = create_engine(config_id if config_id else 'database')
    create_all(engine)


@manager.command
def drop(config_id=None):
    engine = create_engine(config_id if config_id else 'database')
    drop_all(engine)


@manager.command
def dropcascade(config_id=None):
    from leopard.core.orm import drop_cascade, db_session
    engine = create_engine(config_id if config_id else 'database')
    db_session.configure(bind=engine)
    drop_cascade()


@manager.command
def base_init(config_id=None):
    redis.flushall()
    create_engine_with_binding(config_id if config_id else 'database')
    init_config('setup')
    common_init(config_id)  # 普通init
    authentication_init()
    post_init()


@manager.command
def init(config_id=None):
    redis.flushall()
    create_engine_with_binding(config_id if config_id else 'database')
    init_config('setup')
    common_init(config_id)  # 普通init
    tender_init(config_id)
    authentication_init()
    post_init()
    # auto_investment_init()  # 自动投标init


def common_init(config_id):
    setup_logging()
    permissions = get_config('permissions')

    repay_method_list = [
        # ('一次性还款', 'one_only'),
        # ('等本等息', 'average_capital'),
        ('一次性付息到期还本', 'interest_first'),
        ('等额本息', 'average_captial_plus_interest'),
        ('按月付息到期还本', 'capital_final')
    ]
    for name, logic in repay_method_list:
        repay_method = RepaymentMethod()
        repay_method.name = name
        repay_method.logic = logic
        db_session.add(repay_method)

    project_type_list = [
        ('企业贷', 'flow'),
        ('商户贷', 'flow'),
        ('汽车贷', 'flow'),
        ('抵押贷', 'flow'),
        ('网业贷', 'flow'),
        ('菁英贷', 'flow'),
        ('学仕贷', 'common')
    ]
    for name, logic in project_type_list:
        project_type = ProjectType()
        project_type.name = name
        project_type.logic = logic
        project_type.type = get_enum('PROJECT_TYPE_FLOW')
        db_session.add(project_type)

    admin_group = GroupFactory(name='超级管理员', description='超级管理员',
                               _permissions=permissions['staff_permissions'])
    guarantee_group = GroupFactory(
        name='担保机构', description='担保机构',
        _permissions=permissions['guarantee_permissions'])

    su = UserFactory(
        username='su', phone='18000000000', is_super=True, is_staff=True)
    su.password = 'abstack'

    UserFactory(username='admin', is_staff=True, groups=[admin_group])

    guarantee_user = UserFactory(username='某某', is_guarantee=True,
                                 groups=[guarantee_group])
    GuaranteeFactory(name='某某', full_name='某某担保有限公司',
                     user=guarantee_user, logo='img/guarantee_logo_1.jpg',
                     description="担保机构介绍")

    offline = DepositPlatform()
    offline.name = '线下充值账户 - 男一号'
    offline.description = """用户名：男一号
银行账号：6222000000000000
开户行：平安银行
开户支行：南山支行"""
    offline.dataset = {}
    offline.logic = 'Offline'
    db_session.add(offline)

    baofoo = DepositPlatform()
    baofoo.name = '线上充值平台 - 宝付'
    baofoo.description = ('银行卡在线支付网关是网银在线推出的基于银行卡在线支付的第三方'
                          '电子支付系统，通过整合各家银行的支付接口，支持国内18家银行'
                          '借记卡和信用卡的在线支付，致力于为国内外从事电子商务的企业或'
                          '个人提供安全、快捷、稳定的支付服务。')
    baofoo.dataset = {
        "action": "https://paygate.baofoo.com/PayReceive/bankpay.aspx",
        "MerchantID": "121710",
        "PayID": "1000",
        "Merchant_url": "/service/account/deposit/Baofoo/recv",
        "Return_url": "/service/account/deposit/Baofoo/front",
        "NoticeType": "1",
        "Md5Key": "83zckh5jdstq4tvl"
    }
    baofoo.logic = 'Baofoo'
    db_session.add(baofoo)

    ebatong = DepositPlatform()
    ebatong.name = '线上充值平台 - 贝付'
    ebatong.description = ('银行卡在线支付网关是网银在线推出的基于银行卡在线支付的第三方'
                           '电子支付系统，通过整合各家银行的支付接口，支持国内18家银行'
                           '借记卡和信用卡的在线支付，致力于为国内外从事电子商务的企业或'
                           '个人提供安全、快捷、稳定的支付服务。')
    ebatong.dataset = {
        "action": "https://www.ebatong.com/direct/gateway.htm",
        "certification": "J5GNQ6CANKZ7YF67MYF8O4EEEEW41Wltwvnl",
        "sign_type": "MD5",
        "service": "create_direct_pay_by_user",
        "partner": "201311271045297204",
        "input_charset": "utf-8",
        "notify_url": "/service/account/deposit/Ebatong/recv",
        "return_url": "/service/account/deposit/Ebatong/front",
        "subject": "直接消费",
        "payment_type": "1",
        "seller_id": "201311271045297204"
    }
    ebatong.logic = 'Ebatong'
    db_session.add(ebatong)

    RedPacketTypeFactory(name='普通红包', logic='',
                         description='平台方发布的普通奖励红包',
                         valid=30)
    RedPacketTypeFactory(name='注册红包', logic='REGISTER',
                         description='注册即送10元红包，完成首次投资后可提现。', valid=0)
    RedPacketTypeFactory(name='首次投资红包', logic='FIRST_TENDER',
                         description='新会员成功投资，既可获取投标金额的1%奖励，最高一百元。',
                         valid=0)
    RedPacketTypeFactory(name='注册体验金', logic='REGISTER_EXPERIENCE',
                         description='注册体验金。', valid=30)

    db_session.commit()


def tender_init(config_id):
    setup_logging()

    kefu = UserFactory(username='客服妹子', realname='客服妹子', is_staff=True,
                       is_server=True)
    guarantee_user = User.query.filter_by(is_guarantee=True).first()
    guarantee = Guarantee.query.first()

    UserFactory(username='我是借款人', is_borrower=True)
    UserFactory(username='我是投资人', trade_password='sdfsdf')
    UserFactory(username='xiaofuzi', phone='15605875511', password='sdf',
                trade_password='sdf')
    UserFactory(username='Chen', phone='15868870275', password='chen',
                trade_password='chen')

    db_session.flush()
    borrower = User.query.filter_by(username='我是借款人').first()
    lender = User.query.filter_by(username='我是投资人').first()
    borrower.invited = kefu
    lender.invited = kefu
    lender.capital_deduct_order = 0  # 投标扣费排序

    project_type = ProjectType.query.filter_by(logic='flow').first()
    repay_method = RepaymentMethod.query.get(1)

    session = db_session()

    for i in range(2):
        application = ApplicationFactory(user=borrower, guarantee=guarantee,
                                         auditor=guarantee_user,
                                         repay_method=repay_method)
        project = ProjectFactory(application=application, type=project_type)
        project.repaymentmethod_id = 1
        db_session.flush()
        # amount = Decimal.from_float(9999.0)
        business.tender(lender, project, project.amount, session=session)

    for i in range(2):
        application = ApplicationFactory(user=borrower, guarantee=guarantee,
                                         auditor=guarantee_user,
                                         repay_method=repay_method)
        project = ProjectFactory(application=application, type=project_type)
        project.repaymentmethod_id = 1
        db_session.flush()

        business.tender(lender, project, project.amount, session=session)

    for i in range(2):
        application = ApplicationFactory(user=borrower, guarantee=guarantee,
                                         auditor=guarantee_user,
                                         repay_method=repay_method)
        project = ProjectFactory(application=application, type=project_type)
        project.repaymentmethod_id = 1
        db_session.flush()

    application = ApplicationFactory(user=borrower, periods=3, amount=10000,
                                     rate=1, guarantee=guarantee,
                                     auditor=guarantee_user,
                                     repay_method=repay_method)
    project = ProjectFactory(application=application, type=project_type,
                             name='提前部分还款-等额本息')
    project.repaymentmethod_id = 1
    db_session.flush()

    business.tender(lender, project, project.amount, session=session)

    application = ApplicationFactory(user=borrower, periods=3, amount=10000,
                                     rate=1, guarantee=guarantee,
                                     auditor=guarantee_user,
                                     repay_method_id=2)
    project = ProjectFactory(application=application, type=project_type,
                             name='提前部分还款-按月付息到期还本',
                             repaymentmethod_id=2)
    db_session.flush()
    business.tender(lender, project, project.amount, session=session)

    application = ApplicationFactory(user=borrower, periods=3, amount=10000,
                                     rate=1, guarantee=guarantee,
                                     auditor=guarantee_user,
                                     repay_method_id=2)
    application = ApplicationFactory(user=borrower, periods=3, amount=10000,
                                     rate=1, guarantee=guarantee,
                                     auditor=guarantee_user,
                                     repay_method_id=2)
    application = ApplicationFactory(user=borrower, periods=3, amount=10000,
                                     rate=1, guarantee=guarantee,
                                     auditor=guarantee_user,
                                     repay_method_id=2)
    db_session.add(application)

    try:
        db_session.commit()
    except sqlalchemy.exc.IntegrityError as error:
        print(error)


def auto_investment_init():
    from leopard.orm import (UserFactory, User, ApplicationFactory,
                             Application, ProjectFactory, Project,
                             ProjectType, RepaymentMethod)
    from leopard.helpers import get_enum

    repay_method_list = [
        # ('一次性还款', 'one_only'),
        # ('一次性付息到期还本', 'interest_first'),
        ('等额本息', 'average_captial_plus_interest'),
        # ('等本等息', 'average_capital'),
        ('按月付息到期还本', 'capital_final')
    ]
    for name, logic in repay_method_list:
        repay_method = RepaymentMethod()
        repay_method.name = name
        repay_method.logic = logic
        db_session.add(repay_method)

    project_type_list = [
        ('企业贷', 'flow'),
        ('商户贷', 'flow'),
        ('汽车贷', 'flow'),
        ('抵押贷', 'flow'),
        ('网业贷', 'flow'),
        ('菁英贷', 'flow')
    ]
    for name, logic in project_type_list:
        project_type = ProjectType()
        project_type.name = name
        project_type.logic = logic
        project_type.type = get_enum('PROJECT_TYPE_FLOW')
        db_session.add(project_type)

    UserFactory(username='su', phone='18000000000', is_super=True,
                is_staff=True)

    borrower = UserFactory(username='我是借款人', is_borrower=True)
    borrower = UserFactory(username='我是投资人')
    db_session.flush()

    borrower = User.query.filter(User.username == '我是借款人').first()
    project_type = ProjectType.query.filter_by(logic='flow').first()
    User.query.get(5)
    repay_method = RepaymentMethod.query.get(1)

    # 自动投标 START
    UserFactory(username='自动投标人-1', deposit_amount=5000)
    UserFactory(username='自动投标人-2', deposit_amount=100000)
    UserFactory(username='自动投标人-3', deposit_amount=200000)
    UserFactory(username='自动投标人-4', deposit_amount=20000)
    UserFactory(username='自动投标人-5', deposit_amount=5000)
    db_session.flush()
    auto_user_1 = User.query.filter(User.username == '自动投标人-1').first()
    auto_user_2 = User.query.filter(User.username == '自动投标人-2').first()
    auto_user_3 = User.query.filter(User.username == '自动投标人-3').first()
    auto_user_4 = User.query.filter(User.username == '自动投标人-4').first()
    auto_user_5 = User.query.filter(User.username == '自动投标人-5').first()
    AutoInvestmentFactory(user=auto_user_1, min_rate=8, max_rate=10,
                          min_periods=1, max_periods=3, min_amount=2000,
                          max_amount=5000, reserve_amount=1000)
    AutoInvestmentFactory(user=auto_user_2, min_rate=8, max_rate=12,
                          min_periods=1, max_periods=3, min_amount=20000,
                          max_amount=50000, reserve_amount=1000)
    AutoInvestmentFactory(user=auto_user_3, min_rate=8, max_rate=14,
                          min_periods=1, max_periods=3, min_amount=6000,
                          max_amount=8000, reserve_amount=1000)
    AutoInvestmentFactory(user=auto_user_4, min_rate=8, max_rate=16,
                          min_periods=3, max_periods=6, min_amount=8000,
                          max_amount=20000, reserve_amount=5000)
    AutoInvestmentFactory(user=auto_user_5, min_rate=8, max_rate=18,
                          min_periods=6, max_periods=12, min_amount=0,
                          max_amount=100000, reserve_amount=10000000)

    db_session.flush()

    ApplicationFactory(user=borrower, repay_method=repay_method,
                       name='自动投标申请书-1', amount=80000, periods=1,
                       rate=9 / 12)
    ApplicationFactory(user=borrower, repay_method=repay_method,
                       name='自动投标申请书-2', amount=80000, periods=2,
                       rate=9 / 12)
    ApplicationFactory(user=borrower, repay_method=repay_method,
                       name='自动投标申请书-3', amount=80000, periods=3,
                       rate=9 / 12)
    ApplicationFactory(user=borrower, repay_method=repay_method,
                       name='自动投标申请书-4', amount=100000, periods=6,
                       rate=12 / 12)

    db_session.flush()
    application_1 = Application.query.filter_by(name='自动投标申请书-1').first()
    application_2 = Application.query.filter_by(name='自动投标申请书-2').first()
    application_3 = Application.query.filter_by(name='自动投标申请书-3').first()
    application_4 = Application.query.filter_by(name='自动投标申请书-4').first()

    ProjectFactory(application=application_1, type=project_type,
                   repaymentmethod=repay_method,
                   status=get_enum('PROJECT_AUTOINVEST'))
    ProjectFactory(application=application_2, type=project_type,
                   repaymentmethod=repay_method,
                   status=get_enum('PROJECT_AUTOINVEST'))
    ProjectFactory(application=application_3, type=project_type,
                   repaymentmethod=repay_method,
                   status=get_enum('PROJECT_AUTOINVEST'))
    ProjectFactory(application=application_4, type=project_type,
                   repaymentmethod=repay_method,
                   status=get_enum('PROJECT_AUTOINVEST'))

    db_session.flush()

    auto_invest_project = Project.query.filter_by(
        status=get_enum('PROJECT_AUTOINVEST')).all()

    for i in auto_invest_project:
        if i.application.name == '自动投标申请书-4':
            automatic_investments.delay(i.id)
            db_session.commit()


def authentication_init():
    from leopard.orm import AuthenticationFieldType, AuthenticationType

    authentications = [
        {
            'name': '实名认证',
            'logic': 'idcard',
            'description': ('请务必保证信息真实无误,（<span class="text-error">'
                            '请务必填写您的真实信息，一经录入无法修改</span>）'),
            'fields': [
                {
                    'name': '身份证号码',
                    'order': 1,
                    'score': 1,
                    'pattern': ('/^[1-9]\\d{5}[1-9]\\d{3}((0\\d)|(1[0-2]))'
                                '(([0|1|2]\\d)|3[0-1])[\\dX]{4}$/'),
                    'is_content': True
                },
                {
                    'name': '真实姓名',
                    'order': 1,
                    'score': 1,
                    'pattern': '/[\u4e00-\u9fa5]/gm',
                    'is_content': True
                }
            ]
        },
        {
            'name': '邮箱认证',
            'logic': 'email',
            'description': '请务必保证信息真实无误',
            'fields': [
                {
                    'name': '邮箱',
                    'order': 1,
                    'score': 1,
                    'pattern': '/\w+([-+.]\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*/',
                    'is_content': True
                }
            ]
        },
        {
            'name': '户口本',
            'logic': 'household',
            'description': '请务必保证信息真实无误',
            'fields': [
                {
                    'name': '正面',
                    'order': 1,
                    'score': 1,
                    'pattern': '',
                    'is_content': False
                }
            ]
        },
        {
            'name': '收入证明',
            'logic': 'income',
            'description': '请务必保证信息真实无误',
            'fields': [
                    {
                        'name': '正面',
                        'order': 1,
                        'score': 1,
                        'pattern': '',
                        'is_content': False
                    }
            ]
        },
        {
            'name': '征信报告',
            'logic': 'credit_reporting',
            'description': '请务必保证信息真实无误',
            'fields': [
                {
                    'name': '内容',
                    'order': 1,
                    'score': 1,
                    'pattern': '',
                    'is_content': False
                }
            ]
        },
        {
            'name': '房产证',
            'logic': 'house_property_card',
            'description': '请务必保证信息真实无误',
            'fields': [
                {
                    'name': '正面',
                    'order': 1,
                    'score': 1,
                    'pattern': '',
                    'is_content': False
                }
            ]
        },
        {
            'name': '行驶证',
            'logic': 'vehicle_license',
            'description': '请务必保证信息真实无误',
            'fields': [
                {
                    'name': '正面',
                    'order': 1,
                    'score': 1,
                    'pattern': '',
                    'is_content': False
                }
            ]
        },
        {
            'name': '担保合同',
            'logic': 'guarantee_contract',
            'description': '请务必保证信息真实无误',
            'fields': [
                {
                    'name': '正面',
                    'order': 1,
                    'score': 1,
                    'pattern': '',
                    'is_content': False
                }
            ]
        },
        {
            'name': '反担保合同',
            'logic': 'counter_guarantee_contract',
            'description': '请务必保证信息真实无误',
            'fields': [
                {
                    'name': '正面',
                    'order': 1,
                    'score': 1,
                    'pattern': '',
                    'is_content': False
                }
            ]
        },
        {
            'name': '营业执照',
            'logic': 'business_license',
            'description': '请务必保证信息真实无误',
            'fields': [
                {
                    'name': '正面',
                    'order': 1,
                    'score': 1,
                    'pattern': '',
                    'is_content': False
                }
            ]
        },
        {
            'name': '税务登记证',
            'logic': 'tax_registration_certificate',
            'description': '请务必保证信息真实无误',
            'fields': [
                {
                    'name': '正面',
                    'order': 1,
                    'score': 1,
                    'pattern': '',
                    'is_content': False
                }
            ]
        },
        {
            'name': '银行开户许可',
            'logic': 'bank_account_license',
            'description': '请务必保证信息真实无误',
            'fields': [
                {
                    'name': '正面',
                    'order': 1,
                    'score': 1,
                    'pattern': '',
                    'is_content': False
                }
            ]
        },
        {
            'name': '组织机构代码证',
            'logic': 'organization_code_certificate',
            'description': '请务必保证信息真实无误',
            'fields': [
                {
                    'name': '正面',
                    'order': 1,
                    'score': 1,
                    'pattern': '',
                    'is_content': False
                }
            ]
        },
        {
            'name': '抵押物认证',
            'logic': 'mortgaged_property_certification',
            'description': '请务必保证信息真实无误',
            'fields': [
                {
                    'name': '正面',
                    'order': 1,
                    'score': 1,
                    'pattern': '',
                    'is_content': False
                }
            ]
        },
        {
            'name': '实地认证',
            'logic': 'field_certification',
            'description': '请务必保证信息真实无误',
            'fields': [
                {
                    'name': '申请实地考察',
                    'order': 1,
                    'score': 1,
                    'pattern': '',
                    'is_content': True
                }
            ]
        },
    ]

    for i in authentications:
        auth_type = AuthenticationType()
        auth_type.name = i['name']
        auth_type.logic = i['logic']
        auth_type.description = i['description']
        for index, j in enumerate(i['fields']):
            auth_field_type = AuthenticationFieldType()
            auth_field_type.name = j['name']
            auth_field_type.order = j['order']
            auth_field_type.score = j['score']
            auth_field_type.pattern = j['pattern']
            auth_field_type.is_content = j['is_content']
            auth_field_type.bit_status = 2 ** index
            auth_field_type.authentication = auth_type
        db_session.add(auth_type)
    db_session.commit()


def post_init():
    from leopard.orm.board import PostFactory
    yihao = ('公司简介', "公司简介")

    erhao = ('联系我们', """联系我们""")

    sanhao = ('安全保障', """安全保障""")

    sihao = ('新闻一', """新闻一""")

    wuhao = ('新闻二', """新闻二""")

    liuhao = ('新闻三', """新闻三""")

    pingtaiyuanli = ("平台原理", """平台原理""")

    notice_1 = ("通知一", """通知一""")

    notice_2 = ("通知二", """通知二""")

    notice_3 = ('通知三', """通知三""")

    post_list = [
        (0, '公司简介', '公司简介', True, [yihao]),
        (2, '联系我们', '联系我们', True, [erhao]),
        (3, '网站公告', '网站公告', True, [notice_1, notice_2, notice_3]),
        (4, '媒体报道', '媒体报道', True, [sihao, wuhao, liuhao]),
        (10, '安全保障', '安全保障', True, [sanhao]),
        (12, '平台原理', '平台原理', True, [pingtaiyuanli]),
    ]

    # post = None
    for t, v, title, b, c in post_list:
        if b:
            for i, sm in c:
                PostFactory(type=t, title=i, content=sm)
    db_session.commit()
