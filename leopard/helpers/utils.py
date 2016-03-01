import time
import math
import yaml
import random
import hashlib
import datetime
import sqlalchemy
import subprocess
from dateutil.relativedelta import relativedelta

from flask.ext.restful.reqparse import RequestParser

from leopard.conf import consts
from leopard.core.orm import db_session
from leopard.core.config import get_config
from leopard.apps.service import app, fields, parsers
from leopard.helpers.decorators import after_current_request


enum = get_config('enum')
project_config = get_config('project')
service_config = get_config('leopard.apps.service')


def generate_custom_config():
    from jinja2 import Template
    from leopard.orm import FirendLink, Banner, Config
    links = FirendLink.query.filter_by(is_show=True).order_by('priority').all()

    data = {}
    data['BANNERS'] = Banner.query.filter_by(
        is_show=True, location=get_enum('BANNER_WEB')
    ).order_by('priority').all()
    data['FRIENDLINKS'] = [link for link in links if link.logic == 'links']
    data['PARTNERS'] = [link for link in links if link.logic == 'firendlink']
    data['TRADE_PASSWORD_ENABLE'] = Config.get_int('TRADE_PASSWORD_ENABLE')
    data['BANKCARD_NUMBER_LIMIT'] = Config.get_int('BANKCARD_NUMBER_LIMIT')
    data['PROJECT'] = project_config

    template_file = open('leopard/apps/ng/templates/config.js', 'r')
    template = Template(template_file.read())
    custom_config_file = open('leopard-ng/app/scripts/config.js', 'w')
    custom_config_file.write(template.render(**data))
    template_file.close()
    custom_config_file.close()


def generate_index_html():
    from jinja2 import Template
    from leopard.orm import FirendLink
    links = FirendLink.query.filter_by(is_show=True, logic='links').order_by(
        'priority').all()

    data = {}
    data['FRIENDLINKS'] = links

    template_file = open('leopard/apps/ng/templates/ng_index.html', 'r')
    template = Template(template_file.read())
    custom_config_file = open('leopard-ng/app/index.html', 'w')
    custom_config_file.write(template.render(**data))
    template_file.close()
    custom_config_file.close()


def build_front():
    command = "cd leopard-ng; fife build"
    subprocess.call(command, shell=True)


def get_enum(name):
    return enum[name]


def get_parser(name):
    parser = RequestParser()
    parser.args = getattr(parsers, name)
    return parser


def get_field(name):
    return getattr(fields, name)


def pagination(query):
    args = get_parser('pagination').parse_args()

    @after_current_request
    def make_pagination_number(response):
        response.headers['Page-total'] = count
        response.headers['Page-current'] = current
        return response
    count = math.ceil(query.count() / args['limit']) if args['limit'] > 0 \
        else 1
    current = (args['offset'] // args['limit']) + 1 if args['limit'] > 0 else 1
    query = query.offset(args['offset']).limit(args['limit']) if \
        args['limit'] > 0 else query.offset(args['offset'])
    return query


def filtering(query):
    args = get_parser('filtering').parse_args()
    try:
        filter_args = yaml.safe_load(args['filter'])
        start_date = filter_args.pop('start_date', None)
        end_date = filter_args.pop('end_date', None)
        day = filter_args.pop('day', None)

        obj = query._primary_entity.type
        if start_date:
            query = query.filter(obj.added_at >= start_date)
        if end_date:
            query = query.filter(obj.added_at <= end_date)
        if day:
            d = datetime.datetime.now()
            today = datetime.datetime(d.year, d.month, d.day, 0, 0, 0)
            days = 0 if int(day) == 1 else int(day)
            befor = today - datetime.timedelta(days=days)
            query = query.filter(obj.added_at >= befor)
        query = query.filter_by(**filter_args)
    except yaml.scanner.ScannerError:
        pass
    except sqlalchemy.exc.InvalidRequestError:
        pass
    return query


def plan_filtering(query):
    args = get_parser('filtering').parse_args()
    try:
        filter_args = yaml.safe_load(args['filter'])
        start_date = filter_args.pop('start_date', None)
        end_date = filter_args.pop('end_date', None)
        day = filter_args.pop('day', None)

        obj = query._primary_entity.type
        if start_date:
            query = query.filter(obj.plan_time >= start_date)
        if end_date:
            query = query.filter(obj.plan_time <= end_date)
        if day:
            now = datetime.datetime.now()
            today = datetime.date.today()
            befor = now - datetime.timedelta(days=int(day))
            future = today + datetime.timedelta(days=int(day))
            query = query.filter(obj.plan_time > befor, obj.plan_time < future)
        query = query.filter_by(**filter_args)
    except yaml.scanner.ScannerError:
        pass
    except sqlalchemy.exc.InvalidRequestError:
        pass
    return query


def sorting(query):
    args = get_parser('sorting').parse_args()
    obj = query._primary_entity.type
    if args['sort']:
        for i in args['sort'].split('|'):
            if i.count(' ') != 1:
                return query
            key, sort = i.split(' ')
            if key not in dir(obj) or sort not in ('desc', 'asc'):
                return query
        return query.order_by(*args['sort'].split('|'))
    else:
        return query.order_by('id desc')


def dateformat(value, format='%Y年%m月%d日'):
    return value.strftime(format)
app.jinja_env.filters['dateformat'] = dateformat


def unzip_dict(d):
    return str().join(['<input type="hidden" name="{}" value="{}"/>\
                       '.format(k, v) for k, v in d.items()])
app.jinja_env.filters['unzip_dict'] = unzip_dict


def generate_user_id_uuid(user_id):
    key = service_config['SECONDARY_SECRET_KEY']
    salt = '{}:{}'.format(user_id, key).encode('utf-8')
    return hashlib.sha1(salt).hexdigest()


def generate_media_filename():
    key = service_config['SECONDARY_SECRET_KEY']
    epoch_time = time.time()
    random_key = random.random()
    salt = '{}:{}:{}'.format(epoch_time, random_key, key).encode('utf-8')
    return hashlib.sha1(salt).hexdigest()


def generate_sort_name(item):
    salt = '{}'.format(item).encode('utf-8')
    result = hashlib.sha1(salt).hexdigest()
    return result[:5]


def generate_order_number():
    return '{}{:016d}'.format(datetime.datetime.now().strftime('%Y%m%d%H%M%S'),
                              random.randint(0, 9999999999999999))


def generate_order_withdraw():
    return '{}{:03d}'.format(datetime.datetime.now().strftime('%Y%m%d%H%M%S'),
                             random.randint(0, 999))


def init_config(config_id):
    from leopard.orm import Config, Banner, FirendLink

    setup_config = get_config(config_id)
    for key, (value, name) in setup_config['CONFIG'].items():
        config = Config()
        config.name = name
        config.key = key
        config.value = value
        db_session.add(config)
    for item in setup_config['HOME_BANNERS']:
        banner = Banner()
        banner.src = item['src']
        banner.link = item['link']
        db_session.add(banner)
    for item in setup_config['SYSTEM_FRIENDS']:
        link = FirendLink()
        link.name = item['name']
        link.link = item['link']
        link.img = item['img']
        link.logic = 'firendlink'
        db_session.add(link)
    for item in setup_config['FRIENDS_LINKS']:
        link = FirendLink()
        link.name = item['name']
        link.link = item['link']
        link.img = item['img']
        link.logic = 'links'
        db_session.add(link)
    db_session.commit()


def get_uwsgi():
    try:
        import uwsgi
    except ImportError:
        from leopard.comps.local_uwsgi import uwsgi
    finally:
        return uwsgi


def get_columns_by_model(model):
    keys = [key for key in model.__dict__.keys() if not key.startswith('_')
            and not callable(getattr(model, key))]
    return keys


def float_quantize_by_two(value):
    value_str = str(value)
    where = value_str.find('.')
    if where != -1:
        return float(value_str[:where + 3])
    else:
        return float(value)


def valid_expires(from_date, day):
    now = datetime.datetime.now()
    if from_date + relativedelta(days=day) < now:
        return False
    return True


def generate_redpacket_code():
    code = random.sample(consts.CODE_REDPACKET_CHARS, 10)
    return ''.join(code)


def generate_unique_code(cls_name):
    code = None
    while(1):
        rand_code = generate_redpacket_code()
        exists = db_session.query(cls_name.query.filter_by(
            code=rand_code).exists()).scalar()
        if not exists:
            code = rand_code
            break

    return code


def generate_invite_code():
    from leopard.orm import User
    invite_code = None
    while 1:
        invite_code = random.sample(consts.INVITE_CODE_CHARS, 8)
        invite_code = ''.join(invite_code)
        exists = db_session.query(User.query.filter_by(
            invite_code=invite_code).exists()).scalar()
        if not exists:
            break
    return invite_code
