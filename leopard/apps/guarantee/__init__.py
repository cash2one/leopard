import requests

from datetime import timedelta
from leopard.core.config import get_config

from flask import request, session, redirect, url_for, render_template, flash
from flask.ext.admin import Admin, expose
from flask.ext.admin import AdminIndexView as origin_adminindexview
from flask.ext.babelex import Babel

from leopard.orm import Application
from leopard.core import factory
from leopard.core.orm import db_session
from leopard.comps.redis import RedisSessionInterface
from leopard.comps.admin import AuthMixin as origin_authmixin
from leopard.services.auth import update_login_datetime, update_login_ip, update_login_counter
from leopard.helpers import get_enum
from leopard.helpers import get_current_user, get_user_username

from leopard.apps.service.tasks import strange_land_inspect


class AuthMixin(origin_authmixin):
    extra_condition_field = 'is_guarantee'


class AdminIndexView(origin_adminindexview):

    @expose('/')
    def index(self):
        user = get_current_user()
        if not user:
            return redirect(url_for('.login_view'))
        if user and not user.is_guarantee:
            return redirect('/')
        applications = Application.query.filter(Application.guarantee == user.guarantee,
                                                Application.status == get_enum(
                                                    'APPLICATION_GUARANTEE_TRIALING'
                                                )).order_by("added_at desc").limit(20)
        app.jinja_env.globals['applications'] = applications

        return super(AdminIndexView, self).index()

    @expose('/login/', methods=('GET', 'POST'))
    def login_view(self):
        if request.method == "GET":
            return render_template('admin/login.html')

        if request.method == "POST":
            username = request.form['username']
            password = request.form['password']
            user = get_user_username(username, password)
            if user and user.is_guarantee:
                session['user_id'] = user.id
                update_login_counter(user)
                update_login_ip(user)
                update_login_datetime(user)
                strange_land_inspect.delay(user.last_login_ip, user.current_login_ip)
                app.jinja_env.globals['admin_username'] = user.username
                app.jinja_env.globals['guarantee_name'] = user.guarantee.name
                db_session.commit()
                if request.args.get('next', ''):
                    return redirect(request.args.get('next', ''))
                return redirect(url_for('.index'))
            flash('错误的用户名或密码!')
            return render_template('admin/login.html')
        return super(AdminIndexView, self).index()

    @expose('/logout/')
    def logout_view(self):
        session.pop('user_id', None)
        return redirect(url_for('.login_view'))


def create_app(import_name):
    app = factory.create_app(import_name)
    app.config.update(get_config(import_name))
    app.session_interface = RedisSessionInterface()
    app.permanent_session_lifetime = timedelta(minutes=10)
    return app

app = create_app(__name__)
admin = Admin(app, name='担保机构管理', index_view=AdminIndexView(url='/'), url='/', static_url_path='')


@app.errorhandler(404)
def page_not_found(e):
    user = get_current_user()
    if user:
        raise e
    return redirect(url_for('admin.login_view', next=requests.utils.urlparse(request.url).path))

babel = Babel(app)
