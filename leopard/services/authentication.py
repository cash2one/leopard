import re
import os
import base64
import itsdangerous
import logging

from redis import Redis
from itsdangerous import TimestampSigner
from datetime import date
from sqlalchemy import Date, cast
from sqlalchemy.sql import func
from flask import (Blueprint, request, session, current_app, make_response,
                   redirect)
from flask.ext.restful import abort, marshal_with, Resource

from leopard.core.config import get_config
from leopard.helpers import (
    authenticate, filtering, get_field, generate_user_id_uuid,
    pagination, sorting, get_current_user, get_current_user_id, get_parser)
from leopard.orm import (
    Authentication, AuthenticationField, AuthenticationFieldType,
    AuthenticationType, User, RealnameAuth)
from leopard.core.orm import db_session
from leopard.core.validate import exist_realname_auth
from leopard.services.auth import allowed_file
from leopard.services.restrict import authentication as auth_utils
from leopard.comps.redis import pool
from leopard.apps.service.tasks import auto_auth_idcard

project_config = get_config('project')
config = get_config('leopard.services.auth')
logger = logging.getLogger('authentication')

board = Blueprint('authentication', __name__, url_prefix='/authentication',
                  template_folder='templates')
redis = Redis(connection_pool=pool)


class AuthenticationResource(Resource):
    method_decorators = [authenticate]

    urls = ['', '/<int:type_id>']
    endpoint = 'authentication'

    @marshal_with(get_field('authentication_type'))
    def get(self, type_id=None):
        user_id = get_current_user_id()
        if type_id:
            auth_type = AuthenticationType.query.filter(
                AuthenticationType.id == type_id,
                AuthenticationType.logic.in_(('idcard', 'email'))
            ).first()
            if not auth_type:
                abort(404)
            auth_type.authentication = auth_type.get_authentication(user_id)
            if auth_type.logic == 'idcard' and auth_type.authentication:
                fields = auth_type.authentication.fields
                auth_type.authentication.fields[0].value = '{}{}{}'.format(
                    fields[0].value[:3], '*************', fields[0].value[-2:]
                )
                auth_type.authentication.fields[1].value = '{}*{}'.format(
                    fields[1].value[:1], fields[1].value[-1:]
                )
            return auth_type

        authentication_types = pagination(
            filtering(
                sorting(
                    AuthenticationType.query.filter(
                        AuthenticationType.logic.in_(('idcard',)))
                )
            )
        ).all()
        for i in authentication_types:
            i.authentication = i.get_authentication(user_id)
            if i.logic == 'idcard' and i.authentication:
                fields = i.authentication.fields
                i.authentication.fields[0].value = '{}{}{}'.format(
                    fields[0].value[:3],
                    '*************',
                    fields[0].value[-2:]
                )
                i.authentication.fields[1].value = '{}*{}'.format(
                    fields[1].value[:1], fields[1].value[-1:])
        return authentication_types

    def post(self, type_id):
        auth_type = AuthenticationType.query.get(type_id)
        args = request.json
        if not auth_type:
            abort(404, message='该认证不存在')
        for i in auth_type.fields:
            if str(i.id) not in args.keys():
                abort(400, message='请填写所有资料后提交')
        user = get_current_user()
        authentication = Authentication.query.filter(
            Authentication.user_id == user.id,
            Authentication.type_id == type_id).first()
        if authentication and authentication.type.logic != 'email':
            abort(400, message='您已经添加过该认证了！')

        authentication = Authentication()
        authentication.type = auth_type
        authentication.user = user
        for i in auth_type.fields:
            field = AuthenticationField()
            field.type = i
            field.authentication = authentication
            if field.type.pattern:
                if not re.match(field.type.pattern.split('/')[1],
                                args[str(i.id)]):
                    abort(400, "{} - 填写错误".format(i.name))
            field.value = args[str(i.id)]
        message = '添加认证成功'
        for field in authentication.fields:
            if field.type.pattern:
                if not re.match(field.type.pattern.split('/')[1],
                                args[str(field.type.id)]):
                    abort(400, "{} - 填写错误".format(field.type.name))
            field.value = args[str(field.type.id)]

        if auth_type.logic == 'idcard':
            if exist_realname_auth(user.id):
                message = '您所录入的身份证号已在中宝财富有注册账号，不可重复注册'
                abort(400, message=message)

            # 异步执行 身份认证检查
            search_times = db_session.query(
                func.count(RealnameAuth.id)
            ).filter(
                cast(RealnameAuth.added_at, Date) == date.today(),
                RealnameAuth.user == user
            ).scalar()

            logger.info('[实名认证 POST] 今天查询次数:{} user_id:{}'.format(
                search_times, user.id)
            )
            message = '请求次数太多明天再尝试吧!'
            if search_times <= 3:
                task_result = auto_auth_idcard.delay(user.id)
                logger.info('[实名认证 PUT] celery返回值:{}'.format(task_result))
                message = '认证申请已提交!'
            else:
                abort(400, message=message)

        if auth_type.logic == 'email':
            authentication.is_edit = True
            auth_utils.activate_email(user, authentication.fields[0].value)
            message = '添加认证成功，请到邮箱激活！'

        db_session.commit()
        return dict(message=message)

    def put(self, type_id):
        authentication_type = AuthenticationType.query.get(
            type_id)
        args = request.json
        if not authentication_type:
            abort(404, message='该认证不存在')
        for i in authentication_type.fields:
            if str(i.id) not in args.keys():
                abort(400, message='请填写所有资料后提交')
        user = get_current_user()
        authentication = Authentication.query.filter(
            Authentication.user_id == user.id,
            Authentication.type_id == type_id).first()
        if not authentication:
            abort(400, message='请先添加该认证！')
        if not authentication.is_edit and authentication.type.logic != 'email':
            abort(400, message='正在审核中，不能修改！')
        message = '修改认证信息成功'

        authentication.is_edit = False
        for field in authentication.fields:
            if field.type.pattern:
                if not re.match(field.type.pattern.split('/')[1],
                                args[str(field.type.id)]):
                    abort(400, "{} - 填写错误".format(field.type.name))
            field.value = args[str(field.type.id)]

        if authentication_type.logic == 'idcard':
            if exist_realname_auth(user.id):
                message = '您所录入的身份证号已在中宝财富有注册账号，不可重复注册'
                abort(400, message=message)

            search_times = db_session.query(
                func.count(RealnameAuth.id)
            ).filter(
                cast(RealnameAuth.added_at, Date) == date.today(),
                RealnameAuth.user == user
            ).scalar()

            logger.info('[实名认证 PUT] 今天查询次数:{} user_id:{}'.format(
                search_times, user.id)
            )
            message = '请求次数太多明天再尝试吧!'
            if search_times <= 3:
                task_result = auto_auth_idcard.delay(user.id)
                logger.info('[实名认证 PUT] celery返回值:{}'.format(task_result))
                message = '认证申请已提交!'
            else:
                abort(400, message=message)

            message = '认证申请已提交!'
        elif authentication_type.logic == 'email':
            message = '请到新邮箱激活！'
            if not authentication.status:
                authentication.fields[0].value = args['3']
            auth_utils.change_email(user, args['3'])
        db_session.commit()
        return dict(message=message)


class ImageResource(Resource):
    method_decorators = [authenticate]

    urls = ['/image/<int:field_id>']
    endpoint = 'authentication_image'

    def post(self, field_id):
        if not request.files:
            abort(400, message='请选择上传图片')
        field = AuthenticationFieldType.query.get(field_id)
        if not field:
            abort(404, message='找不到该页面')
        image = request.files[str(field_id)]
        image_size = len(image.read())
        image.seek(0)
        if image_size > config['AVATAR_MAX_IMAGE_SIZE']:
            abort(413, message='图片太大')
        if not allowed_file(image.filename):
            abort(400, message='图片格式错误')

        image_prefix = generate_user_id_uuid(
            '{}-{}'.format(session['user_id'], field_id))
        image_suffix = os.path.splitext(image.filename)[-1].lower()

        image_name = os.path.join(
            config['AUTHENTICATION_FOLDER'], image_prefix + image_suffix)
        image.save(image_name)
        return dict(value=image_name)


class ActivationResource(Resource):
    method_decorators = []

    urls = ['/activation']
    endpoint = 'activation'

    def get(self):
        args = get_parser('activation').parse_args()
        serial = args['serial']
        if not redis.get('email_authentication:{}'.format(serial)):
            return make_response(redirect('/#!/?error=激活码无效'))

        signer = TimestampSigner(
            current_app.config['SECRET_KEY'], salt='active')
        try:
            username = signer.unsign(
                base64.b64decode(serial.encode('utf-8')),
                max_age=172800).decode('utf-8')
            user = User.query.filter_by(username=username).first()
            if not user:
                return make_response(redirect('/#!/?error=激活码无效'))
            authentication = db_session.query(Authentication).filter(
                AuthenticationType.logic == 'email',
                Authentication.type_id == AuthenticationType.id,
                Authentication.user_id == user.id).first()
            if authentication.status:
                redis.delete('email_authentication:{}'.format(serial))
                return make_response(redirect('/#!/?error=激活码无效'))
            user.email = authentication.fields[0].value
            authentication.accept()
            db_session.commit()
            redis.delete('email_authentication:{}'.format(serial))
        except (itsdangerous.BadSignature, itsdangerous.SignatureExpired):
            abort(400, message='激活码无效')
        else:
            return make_response(redirect('/#!/?success=绑定邮箱成功'))


class EmailChangeResource(Resource):
    method_decorators = []

    urls = ['/change_email']
    endpoint = 'change_email'

    def get(self):
        args = get_parser('activation').parse_args()
        serial = args['serial']
        change_email = redis.get('change_email:{}'.format(serial))
        if not change_email:
            return make_response(redirect('/#!/?error=激活码无效'))
        change_email = change_email.decode()
        signer = TimestampSigner(
            current_app.config['SECRET_KEY'], salt='change_email')
        try:
            username = signer.unsign(
                base64.b64decode(serial.encode('utf-8')),
                max_age=172800).decode('utf-8')
            user = User.query.filter_by(username=username).first()
            if not user:
                return make_response(redirect('/#!/?error=激活码无效'))
            authentication = db_session.query(Authentication).filter(
                AuthenticationType.logic == 'email',
                Authentication.type_id == AuthenticationType.id,
                Authentication.user_id == user.id).first()
            authentication.accept()
            authentication.fields[0].value = change_email
            user.email = change_email
            redis.delete('change_email:{}'.format(serial))
            db_session.commit()
        except (itsdangerous.BadSignature, itsdangerous.SignatureExpired):
            abort(400, message='激活码无效')
        else:
            return make_response(redirect('/#!/?success=修改邮箱成功'))
