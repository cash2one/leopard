import datetime

from redis import Redis
from flask import Blueprint, make_response, render_template

from leopard.orm import Project, Banner, Post
from leopard.core.config import get_config
from leopard.comps.redis import pool
from leopard.helpers import get_enum
from leopard.services.restrict import tradestat

blueprint = Blueprint('views', __name__)

config = get_config(__package__)
project_config = get_config('project')
redis = Redis(connection_pool=pool)


@blueprint.route('/')
def index():
        with open(config['INDEX_HTML'], encoding='utf-8') as f:
            return make_response(f.read())


@blueprint.route('/new_index')
def new_index():
    data = {}
    return make_response(render_template('new_index.html', **data))


@blueprint.route('/spider/')
def spider_index():
    data = {}
    data['projects'] = Project.query.filter_by(
        is_show=True,
        category=get_enum('COMMON_PROJECT')
    ).filter(
        Project.status.in_(get_enum('PROJECT_SHOW'))
    ).order_by(
        'id desc', 'status asc'
    )[:4]
    data['finprojects'] = Project.query.filter_by(
        is_show=True,
        category=get_enum('STUDENT_PROJECT')
    ).filter(
        Project.status.in_(get_enum('PROJECT_SHOW'))
    ).order_by(
        'id desc', 'status asc'
    )[:4]

    data['BANNERS'] = Banner.query.filter_by(
        is_show=True, location=get_enum('BANNER_WEB')
    ).order_by('priority').all()[:5]

    data['trailer'] = Post.query.filter_by(
        is_active=True, type=53
    ).order_by('priority').first()
    data['today'] = datetime.datetime.now().strftime('%Y年%m月%d日')
    data['turnover'] = tradestat.turnover()
    data['users_income'] = tradestat.users_income()
    data['gross_income'] = tradestat.gross_income()
    data['META_DESCRIPTION'] = project_config['META_DESCRIPTION']
    data['SYSTEM_PHONE'] = project_config['CORPORATION_TEL']
    data['SYSTEM_NAME'] = project_config['CORPORATION']
    data['SYSTEM_ICP'] = project_config['CORPORATION_ICP']
    data['CORPORATION_FULLNAME'] = project_config['CORPORATION_FULLNAME']
    return make_response(render_template('index.html', **data))


@blueprint.route('/wechat/')
def wechat_index():
    data = {}
    return make_response(render_template('wechat_index.html', **data))
