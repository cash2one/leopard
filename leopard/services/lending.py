import os
import logging
import datetime
import sqlalchemy
from decimal import Decimal

from redis import Redis
from dateutil.relativedelta import relativedelta
from sqlalchemy import func, or_, and_
from flask import Blueprint, request
from flask.ext.restful import abort, marshal_with, Resource, marshal
from werkzeug.exceptions import HTTPException
from leopard.orm import (FinApplication, Application, Guarantee, Investment,
                         Project, AutoInvestment, Config, RepaymentMethod,
                         ProjectPlan, FinMobileApplication, Log,
                         Authentication, AuthenticationType, UserLevel, 
                         Plan, Repayment, AutoInvestIndex, FinApplicationPlan)
from leopard.helpers import (authenticate, filtering, get_enum,
                             get_current_user, get_field, get_parser,
                             pagination, sorting, get_current_user_id,
                             get_config, get_uwsgi, plan_filtering,
                             float_quantize_by_two)
from leopard.apps.service import tasks
from leopard.helpers.exceptions import (RepaymethodDoesNotexist,
                                        TenderCheckException)
from leopard.conf import consts
from leopard.core import business
from leopard.core.validate import general_check, check_investment_amount
from leopard.comps.redis import pool
from leopard.core.orm import db_session
from leopard.services.restrict import prepayment, rank, tradestat

lending = Blueprint('lending', __name__, url_prefix='/lending')

uwsgi = get_uwsgi()  # 获取uwsgi
redis = Redis(connection_pool=pool)
project_config = get_config('project')
logger = logging.getLogger('rotate')
tlogger = logging.getLogger('tender')


class FinProjectResource(Resource):

    urls = ['/finproject', '/finproject/<int:project_id>']
    endpoint = 'finproject'

    def get(self, project_id=None):
        if project_id:
            project = Project.query.filter_by(
                is_show=True,
                category=get_enum('STUDENT_PROJECT'),
                id=project_id
            ).first()

            if not project or project.status not in get_enum('PROJECT_SHOW'):
                abort(406)
            return marshal(project, get_field('finproject_detail'))
        projects = pagination(
            filtering(
                sorting(
                    Project.query.filter_by(
                        is_show=True,
                        category=get_enum('STUDENT_PROJECT')
                    ).filter(
                        Project.status.in_(get_enum('PROJECT_SHOW'))
                    )
                )
            )
        ).all()
        return marshal(projects, get_field('finproject_list'))


class PublicProjectResource(Resource):
    method_decorators = []

    urls = ['/public_project', '/public_project/<int:project_id>']
    endpoint = 'public_project'

    def get(self, project_id=None):
        user = get_current_user()
        if project_id:
            project = Project.query.get(project_id)
            if project.login_show:
                if not user:
                    abort(404)
                elif user.level not in project.project_level_show:
                    abort(406)
            if not project or project.category != get_enum('COMMON_PROJECT'):
                abort(406)
            if not project or project.status not in get_enum('PROJECT_SHOW'):
                abort(406)
            project.investments = Investment.query.filter_by(
                project_id=project.id, previous=None).order_by('id asc').all()
            project.extend_images()
            return marshal(project, get_field('project_detail'))

        if not user:
            project_list = Project.query.filter_by(
                    is_show=True, login_show=False,
                    category=get_enum('COMMON_PROJECT')
                ).filter(
                        Project.status.in_(get_enum('PROJECT_SHOW'))
                    )
        else:
            project_list = Project.query.filter_by(
                    is_show=True, category=get_enum('COMMON_PROJECT')
                ).filter(
                        Project.status.in_(get_enum('PROJECT_SHOW')),
                        or_(
                            Project.project_level_show.any(UserLevel.id == user.level_id),
                            Project.login_show == False
                        )
                    )

        projects = pagination(
            filtering(
                sorting(project_list)
            )
        ).all()

        return marshal(projects, get_field('project_list'))
    get.authenticated = False  # FIXME


class ProjectResource(Resource):
    method_decorators = []

    urls = ['/project', '/project/<int:project_id>']
    endpoint = 'project'

    def get(self, project_id=None):
        user_id = get_current_user_id()
        if project_id:
            project = Project.query.filter_by(
                is_show=True,
                category=get_enum('COMMON_PROJECT'),
                id=project_id,
                user_id=user_id).first()

            if not project or project.status not in get_enum('PROJECT_SHOW'):
                abort(406)
            return marshal(project, get_field('project_detail'))
        projects = pagination(
            filtering(
                sorting(
                    Project.query.filter_by(
                        is_show=True,
                        category=get_enum('COMMON_PROJECT'),
                        user_id=user_id
                    ).filter(
                        Project.status.in_(get_enum('PROJECT_SHOW'))
                    )
                )
            )
        ).all()
        return marshal(projects, get_field('project_list'))


class ProjectPrepaymentResoure(Resource):
    method_decorators = [authenticate]

    urls = ['/project/<int:project_id>/<string:prepayment_type>']
    endpoint = 'project_prepayment'

    def put(self, project_id, prepayment_type):
        if prepayment_type not in project_config['PREPAYMENT_TYPE']:
            abort(404, message='找不到该页面')
        args = get_parser('prepayment_put').parse_args()
        user = get_current_user()
        if Config.get_bool('TRADE_PASSWORD_ENABLE'):  # 是否开启交易密码功能
            if not user.trade_password_enable:
                abort(400, message='请先设置交易密码')
            if not user.check_trade_password(args['trade_password']):
                abort(400, message='错误的交易密码')
        project = Project.query.filter(Project.id == project_id,
                                       Project.user_id == user.id).first()
        logger.info(
            '[Project Prepayment Put] User(id: {}): {}, Project(id): {}'.
            format(user.id, user, project_id))
        if not project:
            abort(404, message='不存在的项目')
        if project.status != get_enum('PROJECT_REPAYING'):
            abort(400, message='该项目不处于可还款状态')

        check = getattr(prepayment, prepayment_type + '_check')
        data = check(project, args)
        prepayment_func = getattr(prepayment, prepayment_type)
        prepayment_func(project, data)
        db_session.commit()

        logfmt = ('[Project Prepayment Put Success] User(id: {}): {}, '
                  'Project(id): {}')
        loginfo = logfmt.format(user.id, user, project_id)
        logger.info(loginfo)
        return dict(message='提前还款成功')


class AccountInvestmentResource(Resource):
    """ 账户中心 investment 详情 """
    method_decorators = [authenticate]
    urls = ['/account_investment', '/account_investment/<int:investment_id>']
    endpoint = 'account_investment'

    def get(self, investment_id=None):
        user = get_current_user()
        if investment_id:
            investment = Investment.query.get(investment_id)
            if not investment or investment.user != user:
                abort(404)
            return marshal(investment, get_field('account_investment_detail'))
        else:
            investments = pagination(
                filtering(
                    sorting(
                        Investment.query.filter_by(user=user)
                    )
                )
            ).all()
            return marshal(investments, get_field('account_investment_list'))


class InvestmentResource(Resource):
    method_decorators = [authenticate]
    urls = ['/investment', '/investment/<int:project_id>']
    endpoint = 'investment'

    def get(self, project_id=None):
        user = get_current_user()
        investments = pagination(
            filtering(
                sorting(
                    Investment.query.filter_by(user=user)
                )
            )
        ).all()
        return marshal(investments, get_field('investment_list'))

    def _redis_repeat_post_limit(self, project_id, user_id):
        pattern = 'INVESTMENT:PROJECT_ID:{}:USER_ID:{}'.format(
            project_id, user_id)
        if redis.exists(pattern):
            abort(400, message='请求太频繁请稍后重试')
        else:
            redis.set(pattern, 0, 3)

    def post(self, project_id):
        args = get_parser('public_project').parse_args()
        project = Project.query.get(project_id)
        user = get_current_user()
        if not project:
            abort(404, message='不存在的项目')
        elif user.level not in project.project_level_allow:
            abort(404, message='等级不足')
        if project.remain_bid_time:
            abort(400, message='项目还剩余%s秒可投'%int(project.remain_bid_time))
        self._redis_repeat_post_limit(project.id, user.id)   # 防止重复提交

        amount = args['amount']
        amount = Decimal(str(amount))
        redpacket_id = args.get('redpacket_id') or 0
        session = db_session()

        try:
            general_check(user, project, amount, session=session,
                          redpacket_id=redpacket_id,
                          trade_password=args.get('trade_password'),
                          password=args.get('password'))
        except TenderCheckException as e:
            abort(400, message=e.args[0])

        logfmt = '===== [投标开始] uwsgi.lock before 投资人:{} pid:{} ====='
        loginfo = logfmt.format(user.username, os.getpid())
        tlogger.info(loginfo)

        uwsgi.lock()  # uwsgi锁
        db_session.refresh(user)
        db_session.refresh(project)

        try:
            amount = min(amount, user.available_amount)
            real_amount, can_use_expe = check_investment_amount(user,
                                                                project,
                                                                amount)

            deduct_order = args.get('capital_deduct_order')  # 投标扣费(排序)
            tender_data, message = business.tender(
                user, project, real_amount,
                session=session, can_use_expe=can_use_expe,
                deduct_order=deduct_order, redpacket_id=redpacket_id)

            session.commit()
            investment = tender_data.get('investment')

            logfmt = ('[Investment Post Success] User(id: {}): {}, '
                      'Investment(id): {}')
            loginfo = logfmt.format(user.id, user, investment.id)
            tlogger.info(loginfo)

            data = marshal(investment, get_field('tender_investment'))
            data.update(message=message)
            return data
        except TenderCheckException as e:
            tlogger.error('Investment Post Error: {}'.format(e), exc_info=1)
            abort(400, message=e.args[0])
        except RepaymethodDoesNotexist as e:
            tlogger.error('Investment Post Error: {}'.format(e), exc_info=1)
            session.rollback()
            abort(400, message='不存在的还款方式')
        except Exception as error:
            tlogger.error('Investment Post Error: {}'.format(error),
                          exc_info=1)
            session.rollback()
            abort(400, message='投标出现错误，请联系客服')
        finally:
            uwsgi.unlock()
            logfmt = '===== [投标结束] 投资人:{} pid:{} ====='
            loginfo = logfmt.format(user.username, os.getpid())
            tlogger.info(loginfo)


class AssigneeContractResource(Resource):
    """ 受让人查看债权合同 """
    urls = ['/investment/<int:investment_id>/assignee_contract']
    endpoint = 'assignee_contract'

    def get(self, investment_id):
        user = get_current_user()
        notin_status = (get_enum('INVESTMENT_PENDING'),
                        get_enum('INVESTMENT_FAILED'))
        investment = Investment.query.filter(
            Investment.id == investment_id,
            Investment.user == user,
            Investment.status.notin_(notin_status)
        ).first()

        if not investment or not investment.previous:
            abort(404)

        # 受让人
        data = {}
        borrower_realname = '{}**'.format(user.realname[0])
        borrower_card = '{}****'.format(user.card[:6])
        data['borrower'] = {
            'realname': borrower_realname,
            'username': user.username,
            'idcard': borrower_card
        }

        # 转让人
        lender_card, lender_realname = None, None
        from_user = investment.previous.user
        lender_card = '{}****'.format(from_user.card[:6])
        lender_realname = '{}**'.format(from_user.realname[0])

        data['lender'] = {
            'realname': lender_realname,
            'username': from_user.username,
            'idcard': lender_card
        }
        data['project_lender'] = investment.project.user.username
        now = datetime.datetime.now()
        last_plan = Plan.query.filter(
            Plan.investment_id == investment.id).order_by('period')

        processed_at = last_plan[-1].plan_time
        if processed_at:
            processed_at = processed_at.strftime('%Y-%m-%d %H:%M')
        else:
            processed_at = '-'

        data['remain_periods_capital'] = '{:.2f} 元'.format(investment.amount)
        data['processed_at'] = processed_at

        project = investment.previous.project
        if project.nper_type == get_enum('MONTH_PROJECT'):
            project_rate = float(project.rate * 12)
        else:
            project_rate = float(project.rate * 365)

        data['rate'] = '{:.2f} %'.format(project_rate)
        data['transfer_interest'] = '{:.2f} 元'.format(
            investment.interest)

        data['no'] = investment.previous.id
        data['now'] = now.strftime('%Y年%m月%d日')
        guarantee = investment.previous.project.guarantee
        if guarantee:
            guarantee_name = guarantee.name
            guarantee_id = guarantee.id
        else:
            guarantee_name = None
            guarantee_id = None
        data['guarantee_name'] = guarantee_name
        data['guarantee_id'] = guarantee_id

        return data


class TransferContractResource(Resource):
    """ 债权转让合同 """
    method_decorators = [authenticate]

    urls = ['/investment/<int:investment_id>/transfer_contract']
    endpoint = 'transfer_contract'

    def get(self, investment_id):
        notin_status = (get_enum('INVESTMENT_PENDING'),
                        get_enum('INVESTMENT_FAILED'))
        investment = Investment.query.filter(
            Investment.id == investment_id,
            Investment.status.notin_(notin_status)
        ).first()
        if not investment:
            abort(400, message='不存在的记录')

        user = get_current_user()

        if investment.next:
            if user != investment.user and investment.next.user != user:
                abort(404, message='您无权查看该合同!')

        # 受让人
        data = {}
        data['borrower'] = {
            'realname': None,
            'username': None,
            'idcard': None
        }

        borrower_realname, borrower_card = None, None

        # 有投资记录
        if investment.next:
            next_user = investment.next.user
            if next_user.realname:
                borrower_realname = '{}**'.format(next_user.realname[0])
            if next_user.card:
                borrower_card = '{}****'.format(next_user.card[:6])

            data['borrower'] = {
                'realname': borrower_realname,
                'username': next_user.username,
                'idcard': borrower_card
            }
        elif user != investment.user:
            next_user = user
            if next_user.realname:
                borrower_realname = '{}**'.format(next_user.realname[0])
            if next_user.card:
                borrower_card = '{}****'.format(next_user.card[:6])

            data['borrower'] = {
                'realname': borrower_realname,
                'username': next_user.username,
                'idcard': borrower_card
            }

        lender_card, lender_realname = None, None
        if investment.user.card:
            lender_card = '{}****'.format(investment.user.card[:6])
        if investment.user.realname:
            lender_realname = '{}**'.format(investment.user.realname[0])

        # 转让人
        data['lender'] = {
            'realname': lender_realname,
            'username': investment.user.username,
            'idcard': lender_card
        }
        data['project_lender'] = investment.project.user.username

        now = datetime.datetime.now()
        last_plan = Plan.query.filter(
            Plan.investment_id == investment.id).order_by('period')

        processed_at = last_plan[-1].plan_time
        if processed_at:
            processed_at = processed_at.strftime('%Y-%m-%d %H:%M')
        else:
            processed_at = '-'
        data['processed_at'] = processed_at

        if investment.next:
            data['remain_periods_capital'] = '{:.2f} 元'.format(
                investment.next.amount)
            data['transfer_interest'] = '{:.2f} 元'.format(
                investment.next.interest)
        else:
            data['remain_periods_capital'] = '{:.2f} 元'.format(
                investment.remain_periods_capital)
            data['transfer_interest'] = '{:.2f} 元'.format(
                investment.transfer_interest)

        project = investment.project
        if project.nper_type == get_enum('MONTH_PROJECT'):
            project_rate = float(project.rate * 12)
        else:
            project_rate = float(project.rate * 365)

        data['rate'] = '{:.2f} %'.format(project_rate)
        data['no'] = investment.id
        data['now'] = now.strftime('%Y年%m月%d日')
        guarantee = investment.project.guarantee
        if guarantee:
            guarantee_name = guarantee.name
            guarantee_id = guarantee.id
        else:
            guarantee_name = None
            guarantee_id = None
        data['guarantee_name'] = guarantee_name
        data['guarantee_id'] = guarantee_id

        return data


class InvestmentContractResource(Resource):
    """ 投资合同 """
    method_decorators = [authenticate]

    urls = ['/investment/<int:investment_id>/contract']
    endpoint = 'investment_contract'

    def get(self, investment_id):
        investment = Investment.query.\
            filter(Investment.id == investment_id,
                   Investment.status.notin_((get_enum('INVESTMENT_PENDING'),
                                             get_enum('INVESTMENT_FAILED')))
                   ).first()
        if not investment:
            abort(404)
        user = get_current_user()
        if investment.user != user:
            abort(404)

        data = {}
        data['borrower'] = {
            'name': investment.project.user.realname,
            'username': investment.project.user.username,
            'card': investment.project.user.card,
            'addr': investment.project.user.address,
            'contact': investment.project.user.phone,
        }

        data['lender'] = {
            'name': user.realname,
            'username': user.username,
            'card': user.card
        }

        if investment.project.guarantee:
            data['guarantee'] = {
                'name': investment.project.guarantee.name,
                'card': investment.project.guarantee.license,
                'legal': investment.project.guarantee.legal,
                'addr': investment.project.guarantee.address
            }

        if investment.project.nper_type == get_enum('MONTH_PROJECT'):
            date_step = relativedelta(months=int(investment.project.periods))
        else:
            date_step = relativedelta(days=int(investment.project.periods))

        if investment.project.category == get_enum('COMMON_PROJECT'):
            description = investment.project.application.description
        else:
            description = '学仕贷申请书'

        data['project'] = {
            'amount': str(investment.amount),
            'use': description,
            'rate': investment.project.rate,
            'repayment_method': {
                'name': investment.project.repaymentmethod.name,
                'logic': investment.project.repaymentmethod.logic,
            },
            'periods': investment.project.periods,
            'added_at': investment.added_at.isoformat(),
            'ended_at': (investment.added_at + date_step).isoformat()
        }

        if investment.project.repaymentmethod.logic in ['one_only',
                                                        'interest_first']:
            data['project']['once_amount'] = str(
                investment.amount + investment.interest)
        elif investment.project.repaymentmethod.logic in [
            'average_captial_plusInterest', 'capital_final',
            'average_capital'
        ]:
            data['project']['month_amount'] = str(investment.plans[
                0].amount + investment.plans[0].interest)

        return data


class InvestmentTransferringResource(Resource):
    """ 债权转让 """
    method_decorators = []

    urls = ['/investment_transferring',
            '/investment_transferring/<int:investment_id>']
    endpoint = 'investment_transferring'

    def get(self, investment_id=None):
        user = get_current_user()

        status_enum = (get_enum('INVESTMENT_TRANSFERING'),
                       get_enum('INVESTMENT_TRANSFERED'))
        if investment_id:
            investment = Investment.query.get(investment_id)
            if not investment or investment.status not in status_enum:
                abort(404)
            return marshal(investment, get_field('investment_transfer_detail'))
        if not user:
            invest_list = Investment.query.filter(
                Investment.status.in_(status_enum),
                Investment.project.has(Project.login_show == False)
            )
        else:

            invest_list = Investment.query.filter(
                Investment.status.in_(status_enum),
                or_(
                    Investment.project.has(
                        Project.project_level_show.any(UserLevel.id == user.level_id)), 
                    Investment.project.has(Project.login_show == False),
                    Investment.user_id == user.id
                )
            )
        invest_list = invest_list.order_by(
            Investment.status.asc(),
            Investment.transfering_start_time.desc(),
            Investment.added_at.desc()
        )

        investments = pagination(
            filtering(
                sorting(invest_list)
            )
        ).all()
        return marshal(investments, get_field('investment_transfer_list'))

    def _vaild(self, user, now, investment, args):
        if investment.user != user:
            abort(403, message='权限不足')
        if not investment:
            abort(404)

        executing_plans = investment.executing_plans
        if len(executing_plans) == 0:
            abort(400, message='该项目已完结，不能转让!')

        authenticate = db_session.query(
            Authentication).join(Authentication.type).filter(
            Authentication.user == user,
            AuthenticationType.logic == 'idcard'
        ).first()

        if not authenticate or not authenticate.status:
            abort(400, '实名认证后才能投资, 请先认证')

        if Config.get_bool('TRADE_PASSWORD_ENABLE'):  # 是否开启交易密码功能
            if not user.trade_password_enable:
                abort(400, message='请先设置交易密码')
            if not user.check_trade_password(args['trade_password']):
                abort(400, message='错误的交易密码')
        if investment.project.category != get_enum('COMMON_PROJECT'):
            abort(400, message='抱歉，只有中小微项目才可以转让！')

        if investment.status != get_enum('INVESTMENT_SUCCESSED'):
            abort(400, message='申请转让的项目必须为还款中的项目！')

        recently_plan = executing_plans[0]
        if recently_plan.plan_time < now:
            abort(400, message='您申请的项目存在逾期现象，请联系客服处理！')

        if investment.amount < 100:
            abort(400, message='债权本金不能低于100元!')

        pay_amount = args['pay_amount']
        if pay_amount < 0 or (
            not pay_amount.is_integer() and
            len(str(pay_amount).split('.')[-1]) > 2
        ):
            abort(400, message='贴现金额格式错误!')

        pay_amount = Decimal(str(pay_amount))
        if pay_amount > 0 and user.available_amount < pay_amount:
            abort(400, message='可用资金不足!')

        # 债权转让再转天数限制
        if investment.previous:
            trans_again_limit = Config.get_int('TRANSFERING_AGAIN_LIMIT')
            trans_date = (
                investment.added_at +
                datetime.timedelta(days=trans_again_limit)
            )
            if now <= trans_date:
                abort(400, message='再次转让需等待至少{}天'.format(trans_again_limit))

        # 项目持有天数
        hold_limit = Config.get_int('TRANSFERING_HOLD_LIMIT')
        if now <= (investment.added_at + datetime.timedelta(days=hold_limit)):
            message = '申请转让的项目需持有大于{}天'.format(hold_limit)
            abort(400, message=message)

        # 还款日几天前
        trans_limit_days = Config.get_int('TRANSFERING_LIMIT_DAYS')
        trans_limit_date = datetime.timedelta(days=trans_limit_days)
        if now >= (recently_plan.plan_time - trans_limit_date):
            fmt = '转让申请日应为还款日/结息日的{}天之前'
            message = fmt.format(trans_limit_days)
            abort(400, message=message)

        # 到期日几天前
        remain_days = Config.get_int('TRANSFERING_LIMIT_REMAIN_DAYS')
        remain_date = datetime.timedelta(days=remain_days)
        if now >= executing_plans[-1].plan_time - remain_date:
            message = '转让申请日应为到期日的{}天之前'.format(remain_days)
            abort(400, message=message)

    def post(self, investment_id):
        user = get_current_user()
        if not user:
            abort(403, message='请先登录!')

        logfmt = ('[Investment Transferring Post] User(id: {}): {}, '
                  'investment_id: {} ')
        loginfo = logfmt.format(user.id, user, investment_id)
        logger.info(loginfo)
        investment = Investment.query.get(investment_id)
        args = get_parser('investment_transfer_post').parse_args()

        now = datetime.datetime.now()
        self._vaild(user, now, investment, args)    # 转让验证

        session = db_session()
        try:
            investment.status = get_enum('INVESTMENT_TRANSFERING')

            pay_amount = Decimal(str(args['pay_amount']))
            if pay_amount > 0:
                investment.discount = pay_amount                # 贴现金额
                user.capital_deduct(pay_amount)
                user.blocked_amount += pay_amount               # 用户冻结资金增加
                description = '[债权转让贴现] 用户:{} 冻结资金:{}'.format(
                    user, pay_amount)
                Log.create_log(user=user, amount=pay_amount,
                               description=description)

            limit_time = datetime.timedelta(
                hours=Config.get_int('TRANSFERING_LIMIT_TIME'))
            investment.transfering_start_time = now
            investment.transfering_end_time = now + limit_time

            fmt = ('[Investment Transferring Post Success] User(id: {}): {}, '
                   'investment_id: {}')
            logger.info(fmt.format(user.id, user, investment_id))
            session.commit()
        except Exception as e:
            logger.error(e, exc_info=1)
            session.rollback()
            abort(400, message='申请失败，请联系客服！')
        else:
            return dict(message='申请成功!')

    def _before_update_valid(self, investment, user):
        if investment.project.category != get_enum('COMMON_PROJECT'):
            abort(400, message='抱歉，只有中小微项目才可以转让！')

        if investment.user == user:
            abort(400, message='抱歉，不能自己认购自己的项目！')
        if investment.project.user == user:
            abort(400, message='抱歉，您是项目所有者，不能认购此项目！')
        if investment.status != get_enum('INVESTMENT_TRANSFERING'):
            abort(400, message='此项目暂不能被操作，请联系客服！')
        if investment.remain_periods_capital > user.available_amount:
            abort(400, message='账户余额不足，请先充值！')

        authenticate = db_session.query(
            Authentication).join(Authentication.type).filter(
            Authentication.user == user,
            AuthenticationType.logic == 'idcard'
        ).first()

        if not authenticate or not authenticate.status:
            abort(400, '实名认证后才能投资, 请先认证')

    def put(self, investment_id):
        user = get_current_user()
        if not user:
            abort(403, message='请先登录!')

        args = get_parser('investment_transfer_put').parse_args()
        if Config.get_bool('TRADE_PASSWORD_ENABLE'):  # 是否开启交易密码功能
            if not user.trade_password_enable:
                abort(400, message='请先设置交易密码')
            if not user.check_trade_password(args['trade_password']):
                abort(400, message='错误的交易密码')

        investment = Investment.query.get(investment_id)
        if not investment:
            abort(404)

        self._before_update_valid(investment, user)

        session = db_session()

        try:
            if investment.discount and investment.discount > 0:
                # 贴现金额
                investment.user.blocked_amount -= investment.discount
                description = '[债权转让] 用户:{} 贴现金额扣除:{}'.format(
                    investment.user, investment.discount)
                Log.create_log(user=investment.user,
                               amount=investment.discount,
                               description=description)

                user.income_amount += investment.discount
                description = '[债权购买]  用户:{} 获得贴现金额:{}'.format(
                    user, investment.discount)
                Log.create_log(user=user, amount=investment.discount,
                               description=description)

            investment.transfer(user, args['capital_deduct_order'])
            session.commit()
        except Exception as e:
            logger.error(e, exc_info=1)
            session.rollback()
            abort(400, message='认投失败，请联系客服!')
        else:
            return dict(message='购买成功')


class AutoInvestmentResoure(Resource):
    method_decorators = [authenticate]

    urls = ['/autoinvest']
    endpoint = 'autoinvest'

    @marshal_with(get_field('auto_invest'))
    def get(self):
        user = get_current_user()
        auto_investment = AutoInvestment.query.filter(
            AutoInvestment.user == user).first()
        if not auto_investment:
            auto_investment = AutoInvestment()
            auto_investment.user = user
            db_session.commit()

        return auto_investment

    def put(self):
        args = get_parser('auto_investment').parse_args()

        if not Config.get_bool('AUTO_INVESTMENT_ENABLE'):
            abort(400, message='自动投标服务未开启')

        user = get_current_user()
        auto_investment = AutoInvestment.query.filter(
            AutoInvestment.user == user).first()

        if not user.trade_password_enable:
            abort(400, message='请先设置交易密码')
        if not user.check_trade_password(args['trade_password']):
            abort(400, message='错误的交易密码')

        if args['reserve_amount'] < 0:
            abort(400, message='预留资金格式错误')

        if not (0 <= args['min_rate'] <= args['max_rate']):
            abort(400, message='利率范围不正确')

        if not (0 <= args['min_periods'] <= args['max_periods']):
            abort(400, message='期数范围不正确')

        if not (0 <= args['min_amount'] <= args['max_amount'] <= \
                    auto_investment.max_allow_amount):
            abort(400, message='投资金额范围不正确')

        session = db_session()
        if not args['is_open'] and auto_investment.auto_index:
            session.delete(auto_investment.auto_index)
        elif not auto_investment.auto_index:
            auto_index = AutoInvestIndex()
            auto_index.auto = auto_investment
            auto_index.user = user

        auto_investment.is_open = args['is_open']
        auto_investment.min_amount = args['min_amount']
        auto_investment.max_amount = args['max_amount']
        auto_investment.min_rate = args['min_rate']
        auto_investment.max_rate = args['max_rate']
        auto_investment.min_periods = args['min_periods']
        auto_investment.max_periods = args['max_periods']
        auto_investment.reserve_amount = args['reserve_amount']
        session.add(auto_investment)
        session.commit()

        data = marshal(auto_investment, get_field('auto_invest'))
        data.update(message='修改成功')
        return data


class RepaymentResource(Resource):
    method_decorators = [authenticate]

    urls = ['/repayment', '/repayment/<int:project_id>',
            '/repayment/<int:project_id>/<int:repayment_id>']
    endpoint = 'repayment'

    def get(self, project_id=None, repayment_id=None):
        user_id = get_current_user_id()

        if project_id:
            repayments = pagination(
                filtering(
                    sorting(
                        Repayment.query.filter_by(
                            project_id=project_id, user_id=user_id)
                    )
                )
            ).all()
            return marshal(repayments, get_field('repayment_detail'))
        else:
            repayments = pagination(
                filtering(
                    sorting(
                        Repayment.query.filter(Repayment.user_id == user_id)
                    )
                )
            ).all()
            return marshal(repayments, get_field('repayment_list'))


class FinRepaymentResource(Resource):
    method_decorators = [authenticate]

    urls = ['/finrepayment', '/finrepayment/<int:project_id>',
            '/finrepayment/<int:project_id>/<int:repayment_id>']
    endpoint = 'finrepayment'

    def get(self, project_id=None, repayment_id=None):
        user_id = get_current_user_id()

        if project_id:
            plans = pagination(
                filtering(
                    sorting(
                        ProjectPlan.query.filter(
                            ProjectPlan.project_id == project_id,
                            ProjectPlan.user_id == user_id
                        )
                    )
                )
            ).all()
            return marshal(plans, get_field('project_plan_list'))
        else:
            projects = pagination(filtering(sorting(
                Project.query.filter_by(
                    user_id=user_id,
                    category=get_enum('STUDENT_PROJECT')
                )
            ))).all()
            return marshal(projects, get_field('project_list'))

    def put(self, project_id=None, repayment_id=None):
        user = get_current_user()
        args = get_parser('only_trade_password').parse_args()

        if Config.get_bool('TRADE_PASSWORD_ENABLE'):
            if not user.trade_password_enable:
                abort(400, message='请先设置交易密码')
            if not user.check_trade_password(args['trade_password']):
                abort(400, message='错误的交易密码')

        repeat_str = 'repeat_submit:repayment:{}'.format(repayment_id)
        if redis.get(repeat_str):
            abort(400, message='对不起，请不要重复提交')

        logfmt = '[ProjectPlan Repay Start] ProjectPlan: {}'
        logger.info(logfmt.format(repayment_id))

        project_plan = ProjectPlan.query.filter_by(
            id=repayment_id, user_id=user.id, project_id=project_id
        ).first()
        if not project_plan:
            abort(404, message='找不到该页面')
        if project_plan.status != get_enum('PROJECT_PLAN_PENDING'):
            message = '对不起, 无法执行本操作, 如有疑问, 请联系客服处理. '
            abort(400, message=message)
        if project_plan.period - 1 > project_plan.project.paid_periods:
            abort(400, message='对不起, 请您先归还前一期')

        if user.available_amount < project_plan.amount_interest:
            logfmt = ('[ProjectPlan Repay current user have no enough money]'
                      ' User(id:{}):{}')
            logger.info(logfmt.format(user.id, user.username))
            abort(400, message='对不起, 您的余额不足, 请先充值. ')

        session = db_session()
        try:
            redis.set(repeat_str, '1', 60)
            project_plan.repay()
            # tasks.repayment_success_sms.delay(repayment_id)
        except Exception as error:
            logfmt = '[ProjectPlan Repay Error] ProjectPlan: {}, Error: {}'
            logger.info(logfmt.format(repayment_id, error))
            session.rollback()
            abort(400, message='还款失败，请联系客服处理')
        else:
            session.commit()
            redis.delete(repeat_str)
            logfmt = '[ProjectPlan Repay End] ProjectPlan: {}'
            logger.info(logfmt.format(repayment_id))
            data = marshal(project_plan, get_field('project_plan_detail'))
            data.update(message='还款成功')
            tasks.check_project_plan_done.delay(repayment_id)
            return data


class PlanResource(Resource):
    method_decorators = [authenticate]

    urls = ['/plans']
    endpoint = 'plans'

    @marshal_with(get_field('collection_plan'))
    def get(self):
        user_id = get_current_user_id()

        plans = pagination(
            plan_filtering(
                Plan.query.filter(Plan.investment_id == Investment.id,
                                  Investment.user_id == user_id).
                order_by(Plan.status.asc(), Plan.plan_time.asc())
            )
        ).all()
        return plans


class ApplicationResource(Resource):
    method_decorators = [authenticate]

    urls = ['/application']
    endpoint = 'application'

    @marshal_with(get_field('application'))
    def get(self):
        user = get_current_user()
        applications = pagination(
            filtering(
                sorting(
                    Application.query.filter_by(user=user)
                )
            )
        ).all()

        return applications

    @marshal_with(get_field('application'))
    def post(self):
        user = get_current_user()
        args = get_parser('application').parse_args()
        guarantee = Guarantee.query.get(args['guarantee_id'])
        repaymentmethod = RepaymentMethod.query.get(args['repaymentmethod_id'])

        if not guarantee and args['guarantee_id'] != 0:
            abort(400, message='担保机构不存在')
        if not repaymentmethod:
            abort(400, message='还款方式不存在')

        if args.get('nper_type') == get_enum('DAY_PROJECT') and \
           repaymentmethod.logic != 'interest_first':
            abort(400, message='天标只支持(一次付息到期还本)')

        is_day_project = args.get('nper_type') == get_enum('DAY_PROJECT')
        if args['periods'] > 29 and is_day_project:
            abort(400, message='天标最大天数不能大于29天')

        application = Application()
        application.user = user
        application.repay_method = repaymentmethod
        application.amount = args['amount']
        application.name = args['name']
        application.periods = args['periods']
        application.description = args['description']
        application.added_ip = request.remote_addr

        nper_type = args.get('nper_type', get_enum('MONTH_PROJECT'))
        application.nper_type = nper_type
        if nper_type == get_enum('MONTH_PROJECT'):
            application.rate = args['rate'] / 12
        elif nper_type == get_enum('DAY_PROJECT'):
            application.rate = args['rate'] / 365

        if args['guarantee_id']:
            application.guarantee = guarantee
            application.auditor = guarantee.user
            application.status = get_enum('APPLICATION_GUARANTEE_TRIALING')
        else:
            application.status = get_enum('APPLICATION_RISKCONTROL_TRIALING')

        try:
            db_session.add(application)
            db_session.commit()
            return application
        except sqlalchemy.exc.IntegrityError as e:
            logger.error('[申请书] 新增失败 {}'.format(e))
            abort(400, message='申请失败')


class RepaymentMethodResource(Resource):
    method_decorators = []

    urls = ['/repaymentmethod']
    endpoint = 'repaymentmethod'

    @marshal_with(get_field('repaymentmethod'))
    def get(self):
        repaymentmethods = pagination(
            filtering(
                sorting(
                    RepaymentMethod.query.filter_by(
                        is_show=True).order_by("priority desc")
                )
            )
        ).all()
        return repaymentmethods


class FinApplicationRepaymentMethodResource(Resource):
    method_decorators = []

    urls = ['/finapplication/repaymentmethod']
    endpoint = 'finapplication_repaymentmethod'

    @marshal_with(get_field('repaymentmethod'))
    def get(self):
        repaymentmethods = pagination(
            filtering(
                sorting(
                    RepaymentMethod.query.filter(
                        RepaymentMethod.logic.in_(
                            project_config['FINAPPLICATION_METHOD']
                        ),
                    ).filter_by(
                        is_show=True
                    ).order_by("priority desc")
                )
            )
        ).all()
        return repaymentmethods


class InvestmentRankResource(Resource):
    method_decorators = []

    urls = ['/rank']
    endpoint = 'investment_rank'

    @marshal_with(get_field('rank_list'))
    def get(self):
        day_list = rank.dayList()
        week_list = rank.weekList()
        month_list = rank.monthList()

        ranklist = dict(daylist=day_list, weeklist=week_list,
                        monthlist=month_list)
        return ranklist


class TradeStatResource(Resource):
    method_decorators = []

    urls = ['/trade_stat']
    endpoint = 'trade_stat'

    @marshal_with(get_field('trade_stat'))
    def get(self):
        trade_stat = dict(
            turnover=tradestat.turnover(),
            users_income=tradestat.users_income(),
            gross_income=tradestat.gross_income()
        )
        return trade_stat


class FinApplicationResource(Resource):

    method_decorators = [authenticate]

    urls = ['/finapplication', '/finapplication/<int:obj_id>']
    endpoint = 'finapplication'

    def get(self, obj_id=None):
        user = get_current_user()
        if obj_id:
            application = FinApplication.query.filter_by(
                id=obj_id, user=user
            ).first()
            if not application:
                abort(404)
            return marshal(application,
                           get_field('finapplication_detail'))
        else:
            applications = pagination(
                filtering(
                    sorting(
                        FinApplication.query.filter_by(user=user)
                    )
                )
            ).all()

            return marshal(applications, get_field('finapplication'))

    def post(self):
        user = get_current_user()
        args = get_parser('finapplication').parse_args()

        repay_method = Config.get_config('FINAPPLICATION_DEFAULT_REPAY_METHOD')
        repaymentmethod = RepaymentMethod.query.filter_by(
            logic=repay_method).first()

        if not repaymentmethod:
            abort(400, message='还款方式不存在')

        args['user'] = user
        args['repay_method'] = repaymentmethod
        args['added_ip'] = request.remote_addr
        args['rate'] = Config.get_float('FINAPPLICATION_DEFAULT_RATE')
        application = FinApplication(**args)
        application.generate_uid()

        try:
            db_session.add(application)
            db_session.commit()
            message = '材料已提交，中宝财富的客服人员会在48小时内致电联系您'
            return dict(success=True, message=message)
        except sqlalchemy.exc.IntegrityError as e:
            logger.error('[学仕贷] 新增失败 {}'.format(e), exc_info=True)
            abort(400, message='申请失败')


class FinMobileApplicationResource(Resource):

    method_decorators = [authenticate]

    urls = ['/finmobileapplication', '/finmobileapplication/<int:obj_id>']
    endpoint = 'finmobileapplication'

    def get(self, obj_id=None):
        user = get_current_user()
        if obj_id:
            application = FinMobileApplication.query.filter_by(
                id=obj_id, user=user
            ).first()
            if not application:
                abort(404)
            return marshal(application,
                           get_field('fin_mobile_application_detail'))
        else:
            applications = pagination(
                filtering(
                    sorting(
                        FinMobileApplication.query.filter_by(user=user)
                    )
                )
            ).all()

            return marshal(applications, get_field('fin_mobile_application'))

    def post(self):
        user = get_current_user()
        args = get_parser('fin_mobile_application').parse_args()
        application = FinMobileApplication(**args)
        application.user = user
        db_session.add(application)
        db_session.commit()

        message = '申请提交成功!'
        return dict(success=True, message=message)


class FinApplicationPlanResource(Resource):

    method_decorators = [authenticate]

    urls = ['/finapplication/<int:obj_id>/plan',
            '/finapplication/<int:obj_id>/plan/<int:plan_id>']
    endpoint = 'finapplication_plan'

    def _redis_repeat_post_limit(self, obj_id, plan_id, user_id):
        pattern = consts.FINAPPLICATION_PLAN_REPAY_LIMIT.format(
            obj_id, plan_id, user_id)
        if redis.exists(pattern):
            abort(400, message='请求太频繁请稍后重试')
        else:
            redis.set(pattern, 0, 5)

    def get(self, obj_id=None, plan_id=None):
        user = get_current_user()
        if obj_id:
            application = FinApplication.query.filter_by(
                id=obj_id, user_id=user.id
            ).first()

            if (application and application.status ==
                    get_enum('FINAPPLICATION_VERIFY_SUCCESS')):
                plans = pagination(
                    filtering(
                        sorting(
                            FinApplicationPlan.query.filter_by(
                                application_id=application.id
                            ).order_by(FinApplicationPlan.id.asc())
                        )
                    )
                ).all()
                return marshal(plans, get_field('finapplication_plans'))
        abort(404)

    def put(self, obj_id=None, plan_id=None):
        if obj_id and plan_id:
            user = get_current_user()
            plan = FinApplicationPlan.query.filter(
                FinApplication.id == obj_id,
                FinApplication.user_id == user.id,
                FinApplicationPlan.id == plan_id,
            ).first()

            if plan:
                if plan.status != get_enum('PROJECT_PLAN_PENDING'):
                    message = '对不起, 无法执行本操作, 如有疑问, 请联系客服处理. '
                    abort(400, message=message)
                if plan.period - 1 > plan.application.paid_periods:
                    abort(400, message='对不起, 请您先归还前一期')

                amount = plan.amount_interest + plan.query_overdue_fee()
                if user.available_repay_amount < amount:
                    logfmt = ('[FinApplication Plan Repay current user have no'
                              ' enough money] User(id:{}):{}, plan:{}')
                    logger.info(logfmt.format(user.id, user.username, plan.id))
                    abort(400, message='对不起, 您的余额不足, 请先充值. ')

                self._redis_repeat_post_limit(obj_id, plan.id, user.id)
                session = db_session()
                try:
                    plan.repay()
                    session.commit()
                except HTTPException as error:
                    raise error
                except Exception:
                    fmt = '[学仕贷还款] obj_id: {}, plan_id: {}'
                    logger.error(fmt.format(obj_id, plan_id), exc_info=True)
                    session.rollback()
                    abort(400, message='还款失败')
                else:
                    return dict(success=True, message='还款成功')

        abort(404)


class FinApplicationPlanOverdueFeeResource(Resource):

    method_decorators = [authenticate]

    urls = ['/finapplication/<int:obj_id>/plan/<int:plan_id>/fee']
    endpoint = 'finapplication_plan_fee'

    def get(self, obj_id=None, plan_id=None):
        if obj_id and plan_id:
            user = get_current_user()
            plan = FinApplicationPlan.query.filter(
                FinApplication.id == obj_id,
                FinApplication.user_id == user.id,
                FinApplicationPlan.id == plan_id,
            ).first()
            return dict(fee=float_quantize_by_two(plan.query_overdue_fee()))
        abort(404)
