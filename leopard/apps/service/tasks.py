import time
import logging
import datetime
import traceback
from decimal import Decimal
from redis import Redis
from sqlalchemy import func, or_, and_

from leopard.core.logging import setup_logging
from leopard.core.red_packet import first_deposit
from leopard.apps.service import celery
from leopard.comps import email, sms, strange_land
from leopard.comps.redis import pool
from leopard.core.automatic_invest import auto_invest_start
from leopard.core.orm import create_engine, db_session
from leopard.helpers import (get_enum, get_config, generate_custom_config,
                             build_front)
from leopard.conf import consts


redis = Redis(connection_pool=pool)
FLOW_GAP_MINUTES = 35            # 流转标自动还款扫描间隔
setup = get_config('project')


@celery.task()
def async_accept_deposit(platform_order, amount):
    """ 第三方支付 服务器通知 """
    from leopard.orm import Deposit, Bankcard

    setup_logging()
    logger = logging.getLogger('celery_task')
    engine = create_engine('database')
    db_session.configure(bind=engine)
    fmt = '-- Celery task [async_accept_deposit] 开始 order:{} amount:{}--'

    logger.info(fmt.format(platform_order, amount))

    recharge = Deposit.query.filter(
        Deposit.platform_order == platform_order
    ).first()

    deposit_key = consts.ASYNC_DESPOSIT_USER_KEY.format(recharge.user_id)

    # 当存在key 则sleep
    while(not redis.set(deposit_key, 1, 5, nx=True)):
        time.sleep(0.1)

    if recharge.status == get_enum('DEPOSIT_PENDING'):
        recharge.amount = amount
        recharge.accept()

        #  认证充值银行卡提现金额调整
        if recharge.bankcard_id:
            bankcard = Bankcard.query.get(recharge.bankcard_id)
            if bankcard:
                bankcard.need_amount += amount
                
                fmt = '-- Celery task [async_accept_deposit] 提现银行卡资金调整 bankcard_id:{} amount:{}--'
                logger.info(fmt.format(recharge.bankcard_id, amount))

        db_session.commit()

    redis.delete(deposit_key)

    fmt = '-- Celery task [async_accept_deposit] 结束 order:{} amount:{}--'
    logger.info(fmt.format(platform_order, amount))


@celery.task()
def generate_config():
    engine = create_engine('database')
    db_session.configure(bind=engine)
    generate_custom_config()
    build_front()


@celery.task()
def send_email(title, content, to_email):
    setup_logging()
    email.send(title, content, to_email=to_email)


@celery.task()
def send_sms(content, to_phone):
    setup_logging()
    sms.sms_send(content, to_phone=to_phone)


@celery.task()
def strange_land_inspect(last_login_ip, current_login_ip):
    setup_logging()
    strange_land.inpsect(last_login_ip, current_login_ip)


@celery.task()
def inspect_overdue_transferring_investments():
    """ 逾期债权转让检查 """
    from leopard.orm import Investment, Log

    setup_logging()
    logger = logging.getLogger('celery_task')
    engine = create_engine('database')
    db_session.configure(bind=engine)

    logger.info(
        '-- Celery task [Inspect Overdue Transferring Investments] 开始 --')

    now = datetime.datetime.now()
    investments = Investment.query.filter(
        Investment.status == get_enum('INVESTMENT_TRANSFERING'),
        Investment.transfering_end_time < now
    ).all()

    for investment in investments:
        if investment.transfering_end_time < now:
            investment.status = get_enum('INVESTMENT_SUCCESSED')
            user = investment.user

            # 贴现金额
            discount = investment.discount or 0
            if discount > 0:
                user.blocked_amount -= discount         # 冻结资金解冻
                user.income_amount += discount

                fmt = '[债权转让撤销] 贴现金额退回 用户:{} 冻结资金解冻:{}'
                loginfo = fmt.format(user, discount)
                Log.create_log(user=user, amount=discount, description=loginfo)

            logger.info(
                'Celery task [Inspect Overdue Transferring Investments] '
                'Investment: {}'.format(investment.id))

    db_session.commit()
    db_session.close()
    logger.info('-- Celery task [Inspect Overdue Transferring Investments]'
                ' 结束 --')


@celery.task()
def inspect_auto_repay_flow():
    from leopard.orm import Investment, Plan, Project, Message, ProjectType
    from leopard.helpers import float_quantize_by_two
    setup_logging()
    logger = logging.getLogger('celery_task')
    logger.info('-- Celery task [Inspect Auto Repay Flow] 开始 --')

    try:
        engine = create_engine('database')
        db_session.configure(bind=engine)

        now = datetime.datetime.now()
        gap = datetime.timedelta(minutes=FLOW_GAP_MINUTES)
        plans = Plan.query.filter(
            Plan.status == get_enum('PLAN_PENDING'),
            Plan.plan_time <= now + gap,
            Plan.investment_id == Investment.id,
            Investment.project_id == Project.id,
            Project.type_id == ProjectType.id,
            ProjectType.logic == 'flow').all()

        logger.info('[Inspect Auto Repay Flow] Plans:{}'.format(plans))
        # FIXME　事务
        for plan in plans:
            logger.info('[Inspect Auto Repay Flow] Plan: {}'.format(plan.id))

            plan_key = consts.ASYNC_PLAN_KEY.format(plan.id)
            while(not redis.set(plan_key, 1, 10, nx=True)):
                time.sleep(0.1)

            user_key = consts.ASYNC_PLAN_USER_KEY.format(
                plan.investment.user.id)
            while(not redis.set(user_key, 1, 10, nx=True)):
                time.sleep(0.1)

            db_session.refresh(plan)
            db_session.refresh(plan.investment)
            db_session.refresh(plan.investment.repayment.user)
            db_session.refresh(plan.investment.user)

            project = plan.investment.project

            if plan.status != get_enum('PLAN_PENDING'):
                fmt = ('[Inspect Auto Repay Flow] Plan: {}, 状态不是等待还款, 停止还款.')
                logger.info(fmt.format(plan.id))
                continue

            if (project.user.available_repay_amount <
                    (plan.amount + plan.interest)):

                key = consts.ASYNC_PLAN_NO_AMOUNT.format(plan.id)
                if not redis.set(key, 1, 86400, nx=True):
                    continue

                logfmt = ('[Inspect Auto Repay Flow] Plan: {}, User'
                          '(id: {}): No Enough money')
                logger.info(
                    logfmt.format(plan.id, plan.investment.repayment.user.id))
                content = ('尊敬的客户，您的账户余额不足，无法偿还您的借款'
                           '项目，请尽快充值！')
                sms.sms_send(content=content,
                             to_phone=plan.investment.repayment.user.phone)
                title = '系统消息 - 自动还款余额不足通知!'
                content = ('尊敬的用户，您在偿还项目《{}》的第{}期还款时，'
                           '余额不足，请尽快充值。查看最近<a href="/#!/user/'
                           'repayment-detail?id={}">还款详情</a>。')
                content = content.format(project.name, plan.period, project.id)
                Message.system_inform(
                    to_user=plan.investment.repayment.user, title=title,
                    content=content)
                continue
            plan.repay()
            db_session.commit()
            plan.check_done()

            redis.delete(plan_key)
            redis.delete(user_key)

            # 回款短信通知
            fmt = ('尊敬的投资人：您好！您在中宝财富上的投资今日已回款 {}元，'
                   '请登录www.zhongbaodai.com查看详情！')
            returned_amount = float_quantize_by_two(plan.amount + plan.interest)
            content = fmt.format(returned_amount)
            sms.sms_send(content, to_phone=plan.investment.user.phone)
        logger.info('-- Celery task [Inspect Auto Repay Flow] 结束 --')
    except Exception as error:
        logfmt = '-- Celery task [Inspect Auto Repay Flow] 出错:{} --'
        logger.error(logfmt.format(error))
    finally:
        db_session.close()


@celery.task()
def automatic_investments(project_id):
    from leopard.orm import Project, AutoInvestment, User, AutoInvestIndex

    setup_logging()
    logger = logging.getLogger('celery_task')
    logger.info('-- Celery task [自动投标] 开始 --')

    engine = create_engine('database')
    db_session.configure(bind=engine)

    project = Project.query.get(project_id)

    if project.status != get_enum('PROJECT_AUTOINVEST'):
        logger.warning('Project is not in automatic state!')
        return False

    session = db_session()
    try:
        total_amount = (User.deposit_amount + User.active_amount +
                        User.income_amount - AutoInvestment.reserve_amount)
        autoinvest_list = db_session.query(AutoInvestIndex).join(
            AutoInvestment.user).filter(
            AutoInvestment.is_open == True,
            AutoInvestment.min_periods <= project.periods,
            AutoInvestment.max_periods >= project.periods,
            AutoInvestment.min_rate <= project.rate * 12,
            AutoInvestment.max_rate >= project.rate * 12,
            AutoInvestment.id == AutoInvestIndex.auto_id,
            total_amount >= AutoInvestment.min_amount
        ).order_by(AutoInvestIndex.id).all()
        logger.info('自动投标列表: {}'.format(autoinvest_list))
        auto_invest_start(session, project, autoinvest_list)
    except Exception as e:
        logger.error('Celery task(automatic_investments): {}'.format(e))
    finally:
        if project.amount - project.borrowed_amount < Decimal('0.01'):
            if project.type.logic == 'flow':
                project.status = get_enum('PROJECT_REPAYING')
            elif project.type.logic == 'mortgage':
                project.status = get_enum('PROJECT_PENDING')
        else:
            project.status = get_enum('PROJECT_INVESTING')
        session.commit()
        db_session.close()
        logger.info('-- Celery task [自动投标] 结束 --')


@celery.task()
def max_lend_amount_limit(project_id):
    """
    :功能描述: 标限额开放功能，标发出一定时间后，将最大投资额限制取消(设置未项目总额)
    :责任人: mzj@abstack.com
    :最后修改时间: 2014-10-21 13:33:16
    """
    from leopard.orm import Project
    setup_logging()
    logger = logging.getLogger('celery_task')
    logger.info('-- Celery task [投标上限定时任务] 开始 --')

    engine = create_engine('database')
    db_session.configure(bind=engine)

    try:
        project = Project.query.get(project_id)

        logfmt = '-- Celery task 项目:{}, id:{} 最大投资额 从:{} 调整为:{} --'
        loginfo = logfmt.format(project.name,
                                project.id,
                                project.max_lend_amount,
                                project.amount)
        logger.info(loginfo)
        project.max_lend_amount = project.amount

        db_session.commit()
    except Exception as e:
        logger.error('Celery task(max_lend_amount_limit): {}'.format(e))
    finally:
        logger.info('-- Celery task [投标上限定时任务] 结束 --')
        db_session.close()


@celery.task()
def check_first_record_time():

    setup_logging()
    logger = logging.getLogger('celery_task')
    logger.info('-- Celery task [首次记录时间检查] 开始 --')

    engine = create_engine('database')
    db_session.configure(bind=engine)

    try:
        real_first_record_time(db_session, logger)
    except Exception as e:
        logger.error('Celery task(首次记录时间检查): {}'.format(e))
    else:
        db_session.commit()
    finally:
        logger.info('-- Celery task [首次记录时间检查] 结束 --')
        db_session.close()


def real_first_record_time(db_session, logger):
    import re
    from leopard.conf.consts import IDCARD_PATTERN
    from leopard.orm import User, Config

    invest_status = get_enum('INVESTMENT_SUCCESSED')
    deposit_status = get_enum('DEPOSIT_SUCCESSED')
    users = User.query.all()

    for user in users:
        investments = user.investments
        if investments and not user.first_investment:
            investments.sort(key=lambda r: r.added_at)
            investments = [i for i in investments if i.status == invest_status]
            if investments:
                user.first_investment = investments[0].added_at

        deposits = user.deposits
        if deposits and not user.first_top_up:
            deposits.sort(key=lambda r: r.added_at)
            deposits = [i for i in deposits if i.status == deposit_status]
            if deposits:
                user.first_top_up = deposits[0].added_at

                #  首次充值奖励
                if Config.get_bool('CODEREDPACKET_FIRST_TENDER_ENABLE'):
                    first_deposit(db_session, user)

        if user.card and user.authentications and not user.birth_day:
            auths = user.authentications
            auths = [i for i in auths if i.type.logic == 'idcard']
            if auths and auths[0].status and re.match(IDCARD_PATTERN,
                                                      user.card):
                card = user.card[6:14]

                try:
                    time_str = time.strptime(card, '%Y%m%d')
                    birth = datetime.date(time_str.tm_year, time_str.tm_mon,
                                          time_str.tm_mday)
                    user.birth_day = birth
                except Exception as e:
                    error = traceback.print_exc()
                    error_fmt = 'Celery task(首次记录时间检查): {} {} {}'
                    logger.error(error_fmt.format(user.card, e, error))
    db_session.commit()


@celery.task()
def batch_send_sms(content, ids):
    setup_logging()
    logger = logging.getLogger('celery_task')

    engine = create_engine('database')
    db_session.configure(bind=engine)

    from leopard.orm import User

    users = User.query.filter(User.id.in_(ids))
    logger.info('-- Celery task [后台发送短信] 开始 --')
    content = '{}{}'.format(setup.get('SMS_SIGN_MESSAGE'), content)
    try:
        for user in users:
            sms.sms_send(content, to_phone=user.phone)
    except Exception as e:
        logger.error('-- Celery task [后台发送短信] {}'.format(e))
    finally:
        db_session.close()
        logger.info('-- Celery task [后台发送短信] 结束 --')


@celery.task()
def activity_project_repay_all(ids):
    setup_logging()
    logger = logging.getLogger('celery_task')
    logger_key = 'Activity Project Repay All'
    logger.info('-- Celery task [{}] 开始 --'.format(logger_key))

    engine = create_engine('database')
    db_session.configure(bind=engine)

    for project_id in ids:
        real_activity_project_repay_all(project_id, logger)
    db_session.close()
    logger.info('-- Celery task [{}] 结束 --'.format(logger_key))


def real_activity_project_repay_all(project_id, logger):
    from leopard.orm import Message, Project, RepaymentMethod
    logger_key = 'Real Activity Project Repay All'
    session = db_session()
    try:
        project = Project.query.\
            filter_by(id=project_id, status=get_enum('PROJECT_REPAYING')).\
            filter(Project.repaymentmethod_id == RepaymentMethod.id,
                   RepaymentMethod.logic == 'repayment_immediately').first()
        if not project:
            logger.warning('{}: Project is Empty'.format(logger_key))
            return False

        plan = project.project_plans[0]
        logger.info('[{}] ProjectPlan: {}'.format(logger_key, plan))

        if plan.user.available_amount < plan.amount_interest:
            fmt = ('[{}] ProjectPlan: {}, User(id: {}): No Enough money')
            logger.info(fmt.format(logger_key, plan.id, plan.user.id))
            content = ('尊敬的客户，您的账户余额不足，无法偿还您的借款项目，请尽快充值！')
            sms.sms_send(content=content, to_phone=plan.user.phone)
            title = '系统消息 - 还款余额不足通知!'
            cntfmt = ('尊敬的用户，您在偿还项目《{}》的第{}期还款时，余额'
                      '不足，请尽快充值。查看最近<a href="/#/user/repayme'
                      'nt-detail?id={}">还款详情</a>。')
            content = cntfmt.format(plan.project.name, plan.period,
                                    plan.project.id)
            Message.system_inform(to_user=plan.user, title=title,
                                  content=content)
        else:
            plan.repay()
            session.commit()
            plan.check_done()
    except Exception:
        session.rollback()
        traceback.print_exc()


@celery.task()
def check_project_plan_done(repayment_id):
    from leopard.orm import ProjectPlan

    setup_logging()
    logger = logging.getLogger('celery_task')
    engine = create_engine('database')
    db_session.configure(bind=engine)

    logger.info('-- Celery task [Check Project Plan Done] 开始 --')
    logfmt = '-- Celery task [Check Project Plan Done] ProjectPlan: {}'
    logger.info(logfmt.format(repayment_id))

    project_plan = ProjectPlan.query.get(repayment_id)
    project_plan.check_done()

    logger.info('-- Celery task [Check Project Plan Done] 结束 --')
    db_session.close()


@celery.task()
def repayment_success_sms(repayment_id):
    from leopard.orm import ProjectPlan, Plan

    setup_logging()
    logger = logging.getLogger('celery_task')
    engine = create_engine('database')
    db_session.configure(bind=engine)

    logger.info('-- Celery task [Repayment Success SMS] 开始 --')
    logfmt = '-- Celery task [Repayment Success SMS] ProjectPlan: {}'
    logger.info(logfmt.format(repayment_id))

    repayment = ProjectPlan.query.get(repayment_id)
    for i in repayment.project.investments:
            plan = Plan.query.filter(Plan.period == repayment.period,
                                     Plan.investment_id == i.id).first()
            phone = i.user.phone
            content = ('尊贵的客户，借款人对您({})的账户投资成功还款，'
                       '请查收！您可申请提现或享受千三的续投奖励！')
            content = content.format(plan.investment.user.username)
            sms.sms_send(content, to_phone=phone)

    logger.info('-- Celery task [Repayment Success SMS] 结束 --')
    db_session.close()


@celery.task()
def auto_auth_idcard(user_id):
    from leopard.orm import Authentication, AuthenticationType
    from leopard.comps.realname_auth import simple_check
    from leopard.helpers.auth import get_user_realname_and_card
    setup_logging()
    logger = logging.getLogger('celery_task')
    engine = create_engine('database')
    db_session.configure(bind=engine)

    realname, idcard = get_user_realname_and_card(user_id)

    logger.info('[实名认证检查] 开始 身份证:{} 姓名:{}'.format(idcard, realname))
    if not realname or not idcard:
        return False

    success, jsondata = simple_check(user_id, idcard, realname)

    auth_type = AuthenticationType.query.filter_by(
        logic='idcard').first()

    auth = Authentication.query.filter(
        Authentication.user_id == user_id,
        Authentication.type_id == auth_type.id
    ).first()
    try:
        if success:
            auth.accept(realname=realname, idcard=idcard)
        else:
            auth.reject()

        db_session.add(auth)
        db_session.commit()
    except Exception as e:
        logger.error(e, exc_info=True)
    finally:
        db_session.close()
        logger.info('[实名认证检查] 结束 是否成功:{}'.format(success))
        return True


@celery.task()
def student_loan_repay_remind():
    """
    :描述:学生还款提醒
    还款提醒为到期日3天前短信提醒一次，到期当天提醒一次，到期后2天未还款话短信提醒一次
    """

    import datetime
    from leopard.orm import FinApplicationPlan
    setup_logging()
    logger = logging.getLogger('celery_task')
    engine = create_engine('database')
    db_session.configure(bind=engine)
    logger.info('[学生还款提醒 还款计划检查] 开始 =========== ')
    d = datetime.datetime.now()

    fmt = ('亲爱的用户，您的账户应还金额为{}元，{}最后还款日为{}，请按时还款，如您已还款无需理会。')

    # 到期日3天前短信提醒一次
    three_morning = datetime.datetime(d.year, d.month, d.day, 0, 0, 0)
    three_morning = three_morning + datetime.timedelta(days=3)
    three_evening = three_morning + datetime.timedelta(days=1)

    plans = get_pendding_finplans(three_morning, three_evening)
    for plan in plans:
        content = fmt.format(plan.amount,
                             plan.plan_time.strftime('%m月'),
                             plan.plan_time.strftime('%m月%d日'))
        user = plan.application.user
        sms.sms_send(content, to_phone=user.phone)

    # 到期当天提醒一次
    today_morning = datetime.datetime(d.year, d.month, d.day, 0, 0, 0)
    today_evening = today_morning + datetime.timedelta(days=1)

    plans = get_pendding_finplans(today_morning, today_evening)
    for plan in plans:
        content = fmt.format(plan.amount,
                             plan.plan_time.strftime('%m月'),
                             plan.plan_time.strftime('%m月%d日'))
        user = plan.application.user
        sms.sms_send(content, to_phone=user.phone)

    # 到期后2天未还款话短信提醒一次
    before_morning = datetime.datetime(d.year, d.month, d.day, 0, 0, 0)
    before_morning = before_morning - datetime.timedelta(days=2)
    before_evening = before_morning + datetime.timedelta(days=1)

    plans = get_pendding_finplans(before_morning, before_evening)
    for plan in plans:
        content = fmt.format(plan.amount,
                             plan.plan_time.strftime('%m月'),
                             plan.plan_time.strftime('%m月%d日'))
        user = plan.application.user
        sms.sms_send(content, to_phone=user.phone)

    # 逾期两天后每天发一次
    overdue = datetime.datetime(d.year, d.month, d.day, 0, 0, 0)
    overdue = before_morning - datetime.timedelta(days=3)

    plans = FinApplicationPlan.query.filter(
        FinApplicationPlan.status == get_enum('FINAPPLICATION_PLAN_PENDING'),
        FinApplicationPlan.plan_time < overdue
    )

    plans = get_pendding_finplans(before_morning, before_evening)
    for plan in plans:
        content = fmt.format(plan.amount,
                             plan.plan_time.strftime('%m月'),
                             plan.plan_time.strftime('%m月%d日'))
        user = plan.application.user
        sms.sms_send(content, to_phone=user.phone)

    logger.info('[学生还款提醒 还款计划检查] 结束 =========== ')


def get_pendding_finplans(start_at, end_at):
    from leopard.orm import FinApplicationPlan
    plans = FinApplicationPlan.query.filter(
        FinApplicationPlan.status == get_enum('FINAPPLICATION_PLAN_PENDING'),
        FinApplicationPlan.plan_time >= start_at,
        FinApplicationPlan.plan_time < end_at
    )
    return plans


@celery.task()
def auto_adjust_user_level():
    """
    :描述:用户等级调整
    """
    setup_logging()
    logger = logging.getLogger('celery_task')
    logger.info('-- Celery task [用户等级检查] 开始 --')

    engine = create_engine('database')
    db_session.configure(bind=engine)

    try:
        real_adjust_user_level(db_session, logger)
    except Exception as e:
        logger.error('Celery task(用户等级检查): {}'.format(e))
    else:
        db_session.commit()
    finally:
        logger.info('-- Celery task [用户等级检查] 结束 --')
        db_session.close()


def real_adjust_user_level(db_session, logger):

    from dateutil.relativedelta import relativedelta
    from leopard.orm import User, UserLevel, UserLevelLog, Config, Message
    from leopard.core.ajust_level import adjust_user_level_check

    users = db_session.query(User).filter(
        or_(
            and_(UserLevel.is_auto_adjust == True, 
                    User.level_id == UserLevel.id),
            User.level_id == None
            )
        ).all()
    
    levels = UserLevel.query.filter_by(is_auto_adjust=True, 
        is_show=True).order_by('level_amount').all()

    logger_key = "Real Adjust User Level"

    now = datetime.datetime.now()

    for user in users:

        result = adjust_user_level_check(user, levels)

        if result.get('level'):

            level = result.get('level')
            user.level = level
            level_log = UserLevelLog()
            level_log.user_id = user.id
            level_log.level_id = level.id

            levelstr = '[等级变动] 投资人:{}, 待收金额:{}, 可用金额:{}'
            description = levelstr.format(user.username, user.repaying_amount, 
                    user.available_amount)

            level_log.description = description

            db_session.add(level_log)

            if result.get('reverse') and Config.get_bool('TRADE_PASSWORD_PHONE_CODE_ENABLE'):
                
                content = ('尊敬的投资人：您好！恭喜您升级为中宝财富{}会员，'
                       '请登录www.zhongbaodai.com查看详情！')
                content = content.format(level.name)

                sms.sms_send(content=content, to_phone=user.phone)


            fmt = ('[{}] UserLevelLog: {}, User(id: {}), UserLevel:{} : Adjust User  Level')
            logger.info(fmt.format(logger_key, level_log, user.id, level))

            title = '系统消息 - 会员等级变动通知!'
            cntfmt = ('尊敬的用户，根据中宝用户等级规则,于 {} 投资等级调整为 ({}) ')
            cntfmt = cntfmt.format(now.strftime('%Y-%m-%d %H:%M:%S'), level.name)
            Message.system_inform(to_user=user, title=title,
                                  content=cntfmt)
