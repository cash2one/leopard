import base64
import urllib
import datetime

from redis import Redis
from bs4 import BeautifulSoup
from flask import current_app, render_template
from flask.ext.restful import url_for, abort

from leopard.apps.service.tasks import send_email
from leopard.comps.redis import pool
from leopard.helpers import timestamp_sign, get_config

project_config = get_config('project')

redis = Redis(connection_pool=pool)


def activate_email(user, email):
    serial = base64.b64encode(timestamp_sign(user.username.encode('utf-8'),
                                             current_app.config['SECRET_KEY'],
                                             salt='active')).decode('utf-8')
    redis.set('email_authentication:{}'.format(serial), user.id, 172800)
    activation_url = urllib.parse.urljoin(
        project_config['HOST'], url_for('authentication.activation', serial=serial))
    content = render_template('activation_email.html',
                              host=project_config['HOST'],
                              corporation=project_config['CORPORATION'],
                              user=user,
                              activation_url=activation_url,
                              current_time=datetime.datetime.now())
    soup = BeautifulSoup(content)
    title = soup.title.string
    send_email.delay(title, content, to_email=email)


def change_email(user, email):
    serial = base64.b64encode(timestamp_sign(user.username.encode('utf-8'),
                                             current_app.config['SECRET_KEY'],
                                             salt='change_email')).decode('utf-8')
    redis.set('change_email:{}'.format(serial), email, 172800)
    activation_url = urllib.parse.urljoin(
        project_config['HOST'], url_for('authentication.change_email', serial=serial))
    content = render_template('change_email.html',
                              host=project_config['HOST'],
                              corporation=project_config['CORPORATION'],
                              user=user,
                              activation_url=activation_url,
                              current_time=datetime.datetime.now())
    soup = BeautifulSoup(content)
    title = soup.title.string
    send_email.delay(title, content, to_email=email)