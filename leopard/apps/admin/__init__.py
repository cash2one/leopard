import random
import requests
import datetime
from redis import Redis
from datetime import date, timedelta
from sqlalchemy import Date, cast
from sqlalchemy.sql import func
from flask import request, session, redirect, url_for, render_template, flash
from flask.ext.admin import Admin, expose
from flask.ext.admin import AdminIndexView as OriginAdminindexview
from flask.ext.babelex import Babel

from leopard.orm import Investment, User, Deposit, Withdraw, Plan, Log
from leopard.comps.redis import RedisSessionInterface
from leopard.comps.admin import AuthMixin as OriginAuthmixin
from leopard.core import factory
from leopard.helpers import get_enum
from leopard.core.orm import db_session
from leopard.helpers import get_current_user, validate_admin_user
from leopard.services.auth import (update_login_datetime, update_login_ip,
                                   update_login_counter)
from leopard.services.restrict import tradestat
from leopard.apps.service.tasks import strange_land_inspect
from leopard.core.config import get_config
from leopard.conf import consts

redis = Redis()
project = get_config('project')


class AuthMixin(OriginAuthmixin):
    extra_condition_field = 'is_staff'


class AdminIndexView(OriginAdminindexview):

    def _monthly_incomes(self):
        monthly_incomes = []
        d = datetime.datetime.now()
        start_year = 2014
        for year in range(start_year, d.year):
            for index in range(1, 13):
                start_at = datetime.datetime(year, index, 1, 0, 0, 0)
                if index + 1 > 12:
                    end_at = datetime.datetime(year + 1, 1, 1, 0, 0, 0)
                else:
                    end_at = datetime.datetime(year, index + 1, 1, 0, 0, 0)

                plan_amounts = db_session.query(
                    func.sum(Plan.interest)
                ).filter(
                    Plan.status == get_enum('PLAN_DONE'),
                    cast(Plan.executed_time, Date) >= start_at,
                    cast(Plan.executed_time, Date) < end_at
                ).scalar()

                reward_amounts = db_session.query(func.sum(Log.amount)).filter(
                    Log.description.like('%奖励%'),
                    cast(Log.added_at, Date) >= start_at,
                    cast(Log.added_at, Date) < end_at
                ).scalar()

                plan_amounts = plan_amounts if plan_amounts else 0
                reward_amounts = reward_amounts if reward_amounts else 0
                users_income = plan_amounts + reward_amounts

                monthly_incomes.append({'amount': users_income,
                                        'start_at': start_at,
                                        'end_at': end_at})

        for index in range(1, d.month + 1):
                start_at = datetime.datetime(d.year, index, 1, 0, 0, 0)
                if index + 1 > 12:
                    end_at = datetime.datetime(d.year + 1, 1, 1, 0, 0, 0)
                else:
                    end_at = datetime.datetime(d.year, index + 1, 1, 0, 0, 0)

                plan_amounts = db_session.query(
                    func.sum(Plan.interest)
                ).filter(
                    Plan.status == get_enum('PLAN_DONE'),
                    cast(Plan.executed_time, Date) >= start_at,
                    cast(Plan.executed_time, Date) < end_at
                ).scalar()

                reward_amounts = db_session.query(func.sum(Log.amount)).filter(
                    Log.description.like('%奖励%'),
                    cast(Log.added_at, Date) >= start_at,
                    cast(Log.added_at, Date) < end_at
                ).scalar()

                plan_amounts = plan_amounts if plan_amounts else 0
                reward_amounts = reward_amounts if reward_amounts else 0
                users_income = plan_amounts + reward_amounts

                monthly_incomes.append({'amount': users_income,
                                        'start_at': start_at,
                                        'end_at': end_at})

        app.jinja_env.globals['users_income'] = tradestat.users_income()
        app.jinja_env.globals['monthly_incomes'] = monthly_incomes

    def _investments(self):
        today_investments = Investment.query.filter(
            cast(Investment.added_at, Date) == date.today(),
            Investment.status.in_(
                (get_enum('INVESTMENT_PENDING'),
                 get_enum('INVESTMENT_SUCCESSED'))
            )
        ).order_by("added_at desc").limit(10)

        history_investments = db_session.query(
            func.date_trunc('day', Investment.added_at),
            func.sum(Investment.amount)).group_by(
            func.date_trunc('day', Investment.added_at)
        ).order_by(func.date_trunc('day', Investment.added_at)).all()

        total_investments = db_session.query(
            func.sum(Investment.amount)).scalar()

        today_invest_amount = db_session.query(
            func.sum(Investment.amount)).filter(
            cast(Investment.added_at, Date) == date.today(),
            Investment.status.in_(
                (get_enum('INVESTMENT_PENDING'),
                 get_enum('INVESTMENT_SUCCESSED'))
            )
        ).scalar()
        if not today_invest_amount:
            today_invest_amount = 0

        app.jinja_env.globals['today_invest_amount'] = today_invest_amount
        app.jinja_env.globals['today_investments'] = today_investments
        app.jinja_env.globals['total_investments'] = total_investments
        app.jinja_env.globals['history_investments'] = history_investments

    def _repayments(self):
        today_repayments = Plan.query.filter(
            cast(Plan.plan_time, Date) == date.today(),
            Plan.status == get_enum('PLAN_PENDING')
        ).order_by('plan_time desc').limit(10)

        today_repay_amount = db_session.query(
            func.sum(Plan.amount)
        ).filter(
            cast(Plan.plan_time, Date) == date.today(),
            Plan.status == get_enum('PLAN_PENDING')
        ).scalar()

        if not today_repay_amount:
            today_repay_amount = 0

        total_repay_amount = db_session.query(
            func.sum(Plan.amount)
        ).filter(Plan.status == get_enum('PLAN_PENDING')).scalar()

        if not total_repay_amount:
            total_repay_amount = 0

        app.jinja_env.globals['today_repay_amount'] = today_repay_amount
        app.jinja_env.globals['total_repay_amount'] = total_repay_amount
        app.jinja_env.globals['today_repayments'] = today_repayments

    def _deposits(self):
        today_deposits = Deposit.query.filter(
            cast(Deposit.added_at, Date) == date.today(),
            Deposit.status == get_enum('DEPOSIT_SUCCESSED')
        ).order_by("added_at desc").limit(10)

        today_deposits_amount = db_session.query(
            func.sum(Deposit.amount)).filter(
            cast(Deposit.added_at, Date) == date.today(),
            Deposit.status == get_enum('DEPOSIT_SUCCESSED')
        ).scalar()
        if not today_deposits_amount:
            today_deposits_amount = 0

        total_deposits = db_session.query(func.sum(Deposit.amount)).filter(
            Deposit.status == get_enum('DEPOSIT_SUCCESSED')).scalar()

        app.jinja_env.globals['today_deposits_amount'] = today_deposits_amount
        app.jinja_env.globals['total_deposits'] = total_deposits
        app.jinja_env.globals['today_deposits'] = today_deposits

    def _withdraws(self):
        today_withdraws = Withdraw.query.filter(
            cast(Withdraw.added_at, Date) == date.today(),
            Withdraw.status == get_enum('WITHDRAW_SUCCESSED')
        ).order_by("added_at desc").limit(10)

        total_withdraws = db_session.query(func.sum(Withdraw.amount)).filter(
            Withdraw.status == get_enum('WITHDRAW_SUCCESSED')).scalar()
        today_withdraws_amount = db_session.query(
            func.sum(Withdraw.amount)).filter(
            cast(Withdraw.added_at, Date) == date.today(),
            Withdraw.status == get_enum('WITHDRAW_SUCCESSED')
        ).scalar()

        if not today_withdraws_amount:
            today_withdraws_amount = 0

        app.jinja_env.globals['today_withdraws_amount'] = \
            today_withdraws_amount
        app.jinja_env.globals['today_withdraws'] = today_withdraws
        app.jinja_env.globals['total_withdraws'] = total_withdraws

    @expose('/')
    def index(self):
        user = get_current_user()
        if not user:
            return redirect(url_for('.login_view'))
        if user and not user.is_staff:
            return redirect('/')

        self._investments()
        self._repayments()
        self._withdraws()
        self._deposits()
        self._monthly_incomes()

        total_users = User.query.filter_by(is_super=False).count()
        app.jinja_env.globals['total_users'] = total_users

        return super(AdminIndexView, self).index()

    @expose('/login/', methods=('GET', 'POST'))
    def login_view(self):
        fmt_username = 'nonentity'
        context = {}
        context['cb'] = random.randint(1, 10000000)
        need_vercode = redis.get(consts.ADMIN_LOGIN_NEED_CODE.format(
                                 request.remote_addr)) or False
        app.jinja_env.globals['HOSTNAME'] = project['HOST']
        context['need_vercode'] = need_vercode
        context['can_not_login'] = redis.get(consts.ADMIN_CAN_NOT_LOGIN.format(
                                             request.remote_addr)) or False
        if request.method == 'GET':
            if context['can_not_login']:
                flash('错误次数过多，请1小时后再尝试!')
            return render_template('admin/login.html', **context)

        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            context['username'] = username
            context['password'] = password

            if not username or not password:
                flash('请输入账号和密码!')
                return render_template('admin/login.html', **context)

            user = validate_admin_user(username)
            if user:
                fmt_username = username

            if redis.exists(
                consts.LOGIN_LIMIT_FMT.format(request.remote_addr,
                                              fmt_username)
            ) or context['can_not_login']:
                flash('错误次数过多，请1小时后再尝试!')
                return render_template('admin/login.html', **context)

            if need_vercode:
                vercode = request.form.get('vercode')
                ident_code = session.get('identifying_code',
                                         {}).get('admin_login')
                if not vercode:
                    flash('请输入验证码!')
                    return render_template('admin/login.html', **context)
                if ident_code and ''.join(ident_code) != vercode:
                    flash('验证码错误!')
                    return render_template('admin/login.html', **context)

            if user and user.check_password(password) and user.is_staff:
                redis.delete(consts.LOGIN_LIMIT_FMT.format(request.remote_addr,
                             username))
                redis.delete(consts.ADMIN_LOGIN_FMT.format(request.remote_addr,
                             username))
                redis.delete(
                    consts.ADMIN_LOGIN_NEED_CODE.format(request.remote_addr))

                session['user_id'] = user.id
                update_login_counter(user)
                update_login_ip(user)
                update_login_datetime(user)
                strange_land_inspect.delay(user.last_login_ip,
                                           user.current_login_ip)
                app.jinja_env.globals['admin_username'] = user.username
                db_session.commit()

                # 删除验证码
                if 'identifying_code' in session:
                    del session['identifying_code']

                if request.args.get('next', ''):
                    return redirect(request.args.get('next', ''))
                return redirect(url_for('.index'))
            else:
                redis.incr(consts.ADMIN_LOGIN_FMT.format(
                           request.remote_addr, fmt_username))

                error_times = redis.get(consts.ADMIN_LOGIN_FMT.format(
                                        request.remote_addr, fmt_username))
                if error_times and int(error_times) > 2:
                    redis.set(consts.ADMIN_LOGIN_NEED_CODE.format(
                              request.remote_addr), 0, 3600)
                if error_times and int(error_times) > 5:
                    redis.set(consts.LOGIN_LIMIT_FMT.format(
                              request.remote_addr, fmt_username), 0, 3600)
                    redis.set(consts.ADMIN_CAN_NOT_LOGIN.format(
                              request.remote_addr), 0, 3600)

                flash('错误的用户名或密码!')
                return render_template('admin/login.html', **context)
        return super(AdminIndexView, self).index()

    @expose('/logout/')
    def logout_view(self):
        session.pop('user_id', None)
        app.jinja_env.globals['admin_username'] = None
        return redirect(url_for('.login_view'))


def create_app(import_name):
    app = factory.create_app(import_name)
    app.config.update(get_config(import_name))
    app.session_interface = RedisSessionInterface()
    app.permanent_session_lifetime = timedelta(minutes=10)
    return app

app = create_app(__name__)
admin = Admin(app, name='后台管理',
              index_view=AdminIndexView(url='/'), url='/',
              static_url_path='')


@app.errorhandler(404)
def page_not_found(e):
    user = get_current_user()
    if user:
        raise e
    return redirect(url_for('admin.login_view',
                    next=requests.utils.urlparse(request.url).path))

babel = Babel(app)
