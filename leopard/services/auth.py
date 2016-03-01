import io
import os
import sh
import re
import base64
import random
import logging
import datetime
import tempfile
import sqlalchemy
from sqlalchemy.sql import exists

from PIL import Image
from redis import Redis
from flask import Blueprint, current_app, request, send_file, session
from decimal import Decimal
from flask.ext.restful import abort, marshal_with, Resource, marshal
import simplejson as json

from leopard.core.orm import db_session
from leopard.core.red_packet import red_register
from leopard.core.config import get_config
from leopard.apps.service.tasks import strange_land_inspect
from leopard.comps.redis import pool
from leopard.comps.sms.utils import identifying_code
from leopard.comps.sms import sms_send, sms_content
from leopard.comps.captcha import captcha_image, captcha_clear_image
from leopard.helpers import (
    authenticate, generate_user_id_uuid, get_current_user, get_field,
    get_parser, get_user_username, sign, generate_and_save_bearer_token,
    generate_invite_code, filtering, pagination, sorting)
from leopard.orm import (User, Config, Log, RedPacket, RedPacketType, Message,
                         AuthenticationType, Authentication, UserLevel, UserLevelLog,
                         AuthenticationField, SourceWebsite)
from leopard.services.restrict import (phone_code as phone_code_func,
                                       authentication as auth_utils)

config = get_config(__name__)
project_config = get_config('project')
service_config = get_config('leopard.apps.service')

auth = Blueprint('auth', __name__,
                 url_prefix='/auth', template_folder='templates')

redis = Redis(connection_pool=pool)
logger = logging.getLogger('rotate')


def update_login_counter(user):
    user.login_counter += 1


def update_login_ip(user):
    user.last_login_ip = user.current_login_ip
    user.current_login_ip = request.remote_addr


def update_login_datetime(user):
    user.last_login_at = user.current_login_at
    user.current_login_at = datetime.datetime.now()


def allowed_file(filename):
    allowed_ext = config['AVATAR_ALLOWED_EXTENSIONS']
    file_ext = filename.rsplit('.', 1)[1].lower()
    return '.' in filename and file_ext in allowed_ext


class SessionResource(Resource):
    method_decorators = [authenticate]

    urls = ['/session']
    endpoint = 'session'

    def post(self):
        args = get_parser('session').parse_args()
        count = redis.get('login_faild: {}'.format(request.remote_addr))
        count = int(count) if count else 0
        total_count = redis.get('total_login_faild: {}'.format(
                                request.remote_addr))
        total_count = int(total_count) if total_count else count
        if total_count >= 50:
            abort(400, message='密码错误次数超过50次，一天之内不能访问，请联系客服处理！')
        if count >= 5:
            redis.set('total_login_faild: {}'.format(
                request.remote_addr), total_count + 1, 86400)
            abort(400, message='密码错误次数超过5次，请休息10分钟后提交！')

        vcode = args['identifying_code']
        if request.headers.get('Platform') == 'wechat':
            cb = args.get('cb')
            wechat_login_key = '{}:{}'.format(cb, vcode)
            ident_code = redis.get(wechat_login_key)
            if not ident_code:
                abort(400, message='验证码错误')
        else:
            ident_code = session.get('identifying_code', {}).get('login')
            if ident_code and vcode != ''.join(ident_code).lower():
                abort(400, message='验证码错误')
        username, password = args['username'], args['password']

        user = get_user_username(username, password)
        if not user:
            redis.set('login_faild: {}'.format(
                request.remote_addr), count + 1, 120)
            abort(400, message='用户名或密码错误。')
        if not user.is_active:
            abort(400, message='用户未激活！')
        if user.is_bane:
            abort(400, message='该账号已被冻结，请联系客服！')

        token = ''
        platform = request.headers.get('Platform')
        if platform in project_config['BEARER_TOKEN_PLATFORM']:
            token = generate_and_save_bearer_token(user.id)
        else:
            session['user_id'] = user.id

        update_login_counter(user)
        update_login_ip(user)
        update_login_datetime(user)
        strange_land_inspect.delay(
            user.last_login_ip, user.current_login_ip)
        db_session.commit()

        # 删除验证码
        if 'identifying_code' in session:
            del session['identifying_code']
        return dict(user_id=user.id, token=token)
    post.authenticated = False

    def get(self):
        user_id = session.get('user_id', None)
        return dict(user_id=user_id)
    get.authenticated = False

    def delete(self):
        user_id = session.pop('user_id', None)
        return dict(user_id=user_id)
    delete.authenticated = False


class UserResource(Resource):  # FIXME
    method_decorators = [authenticate]

    urls = ['/user']
    endpoint = 'user'

    def vaild(self, username, password, phone, email, phone_code):
        if username == password:
            abort(400, message='用户名和密码不能一样')
        if len(password) < 8:
            abort(400, message='密码长度最少8位')
        if not re.match('^[a-zA-Z0-9\\u4E00-\\u9FA5]{3,32}$', username):
            abort(400, message='用户名应由4-32位数字、英文或中文组成 !')
        if not re.match('^[1][1-9][\d]{9}$', phone):
            abort(400, message='手机号码格式错误')

        email_pattern = '^\w+([-+.]\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*$'
        if email and not re.match(email_pattern, email):
            abort(400, message='邮箱格式错误')
        if Config.get_bool('REGISTER_PHONE_CODE_ENABLE'):
            if (not redis.get('register_phone_code:' + phone) or
                    not (phone_code == redis.get(
                         'register_phone_code:%s' % phone).decode())):
                abort(400, message='验证码错误')

    def post(self):
        args = get_parser('user_create').parse_args()
        if project_config['REGISTER_IDENTIFYING_CODE_ENABLE']:
            if args['identifying_code'] != session.get('identifying_code',
                                                       {}).get('register'):
                abort(400, message='验证码错误')

        email = args['email']
        phone = args['phone']
        username = args['username']
        password = args['password']
        phone_code = args['phone_code']
        friend_invitation = args['friend_invitation']
        invite_code = args['invite_code']    # 短邀请码

        self.vaild(username, password, phone, email, phone_code)

        if invite_code:
            exists_code = db_session.query(
                exists().where(User.invite_code == invite_code)
            ).scalar()
            if not exists_code:
                invite_code = None

        flag = db_session.query(
            exists().where(User.username == username)
        ).scalar()
        if flag:
            abort(400, message='用户已注册!')

        # 一个手机号只能注册一次
        if phone != '13147121930':
            registered = db_session.query(
                exists().where(User.phone == phone)
            ).scalar()
            if registered:
                abort(400, message='手机号已注册!')

        user = User()
        user.username = username
        user.password = password
        user.phone = phone
        user.permissions = []
        user.friend_invitation = base64.b64encode(
            sign(user.username.encode('utf-8'),
                 current_app.config['SECRET_KEY'],
                 salt='friend')).decode('utf-8').replace('=', '')

        # 生成短邀请码
        user.invite_code = generate_invite_code()

        if(Config.get_bool('REGISTER_PHONE_CODE_ENABLE')):
            user.is_active = True

        if(friend_invitation):
            invite = User.query.filter_by(
                friend_invitation=friend_invitation).first()
            if invite:
                user.invited = invite
            title = '系统消息 - 好友邀请通知!'
            content = '尊敬的用户，您邀请的好友{}，已经加入本平台。'.format(user.username)
            Message.system_inform(
                to_user=invite, title=title, content=content)
        elif(invite_code):
            invite = User.query.filter_by(invite_code=invite_code).first()
            if invite:
                user.invited = invite
            title = '系统消息 - 好友邀请通知!'
            content = '尊敬的用户，您邀请的好友{}，已经加入本平台。'.format(user.username)
            Message.system_inform(to_user=invite, title=title, content=content)

        if email and project_config['ACTIVATION_EMAIL_ENABLE']:
            authentication_type = AuthenticationType.query.filter(
                AuthenticationType.logic == 'email').first()
            authentication = Authentication()
            authentication.type = authentication_type
            authentication.user = user
            field = AuthenticationField()
            field.type = authentication_type.fields[0]
            field.authentication = authentication
            field.value = email
            authentication.is_edit = True
            auth_utils.activate_email(user, authentication.fields[0].value)

        urlparams = json.loads(args['urlparams'])
        puthin = urlparams.get('puthin', '')
        child = urlparams.get('child', '')
        key = urlparams.get('keys', '')
        website = SourceWebsite.query.filter(
            SourceWebsite.puthin == puthin,
            SourceWebsite.key == key).first()
        if website:
            user.source_website = website
            user.source_code = child.strip('{|}')

        common_level = UserLevel.query.filter_by(is_auto_adjust=True, 
            is_show=True).order_by('level_amount').first()
        if common_level:
            user.level = common_level
            level_log = UserLevelLog()
            level_log.user = user
            level_log.level_id = common_level.id
            level_log.description = "[初始等级] 用户等级初始化"
            
        db_session.add(user)
        try:
            db_session.commit()
        except sqlalchemy.exc.IntegrityError as e:
            logger.error('[Register Error] - Error: {}'.format(e))
            abort(400, message='注册无效')
        redis.delete('register_phone_code:' + phone)

        session['user_id'] = user.id
        update_login_counter(user)
        update_login_ip(user)
        update_login_datetime(user)

        if Config.get_bool('REDPACKET_REGISTER_ENABLE'):
            packet_type = RedPacketType.query.filter_by(
                logic='REGISTER').first()
            red_packet = RedPacket()
            red_packet.amount = Config.get_decimal(
                'REDPACKET_REGISTER_AMOUNT')
            red_packet.user = user
            red_packet.type = packet_type
            title = '系统信息 - 您获赠一个注册红包'
            content = '尊敬的用户 - 您于 {} 注册，获赠一个{}元的注册红包！'.format(
                user.added_at.strftime('%Y年%m月%d日 %H:%M:%S'),
                red_packet.amount)
            Message.system_inform(
                to_user=user, title=title, content=content)
            logstr = ('[RedPacket Register Largess Success] User(id: {}): {}, '
                      'amount: {}')
            logger.info(logstr.format(user.id, user, red_packet.amount))

        if Config.get_bool('CODEREDPACKET_REGISTER_ENABLE'):
            red_register(db_session, user)

        if Config.get_bool('REDPACKET_REGISTER_EXPERIENCE_ENABLE'):
            packet_type = RedPacketType.query.filter_by(
                logic='REGISTER_EXPERIENCE').first()
            red_packet = RedPacket()
            red_packet.amount = Config.get_decimal(
                'REDPACKET_REGISTER_EXPERIENCE_AMOUNT')
            red_packet.user = user
            red_packet.type = packet_type
            red_packet.is_available = True
            title = '系统信息 - 您获赠一个注册体验金红包'
            content = '尊敬的用户 - 您于 {} 注册，获赠一个{}元的注册体验金红包！'.format(
                user.added_at.strftime('%Y年%m月%d日 %H:%M:%S'),
                red_packet.amount)
            Message.system_inform(
                to_user=user, title=title, content=content)
            logstr = ('[RedPacket Register experience Largess Success] '
                      'User(id: {}): {}, amount: {}')
            logger.info(logstr.format(user.id, user, red_packet.amount))

        db_session.commit()
        return dict(user_id=user.id, form=dict())
    post.authenticated = False

    @marshal_with(get_field('user'))
    def get(self):
        user = get_current_user()
        return user


class UserProfileResource(Resource):  # FIXME
    method_decorators = [authenticate]

    urls = ['/user/profile']
    endpoint = 'user_profile'

    @marshal_with(get_field('user_profile'))
    def get(self):
        user = get_current_user()
        return user

    def put(self):
        user = get_current_user()
        args = get_parser('user_profile_update').parse_args()
        user.address = args['address']
        user.age = args['age']
        user.sex = args['sex']
        user.education = args['education']
        user.marital_status = args['marital_status']
        db_session.commit()
        return dict(message='修改成功')


class PasswordResource(Resource):  # FIXME
    method_decorators = [authenticate]

    urls = ['/password']
    endpoint = 'password'

    def put(self):
        user = get_current_user()
        args = get_parser('user_password').parse_args()

        if user != get_user_username(user.username, args['oldpassword']):
            abort(400, message="原始密码错误")
        if len(args['newpassword']) < 8:
            abort(400, message="新密码长度少于8位")
        user.password = args['newpassword']
        if(user.password == user.trade_password):
            abort(400, message='登录密码和交易密码不能一样')

        db_session.commit()
        return dict(message='修改成功')


class ForgetPasswordResource(Resource):
    method_decorators = []

    urls = ['/resetter_password']
    endpoint = 'resetter_password'

    def put(self):
        keyword = 'retrieve_password'
        args = get_parser('resetter_password').parse_args()
        user_info, phone_code, password = args[
            'user_info'], args['phone_code'], args['password']

        logstr = '[ForgetPassword Put] user_info: {}, phone_code: {}'
        logger.info(logstr.format(user_info, phone_code))

        if len(password) < 8:
            abort(400, message='密码长度最少8位')
        user = User.query.filter(User.username == user_info).first()
        if not user:
            abort(400, message='用户不存在')
        if user.username == password:
            abort(400, message='用户名和密码不能一样')
        if (not redis.get('{}_phone_code:{}'.format(keyword, user.phone)) or
                (phone_code != redis.get(
                 '{}_phone_code:{}'.format(keyword, user.phone)).decode())):
            abort(400, message='验证码错误')

        user.password = password
        db_session.commit()
        redis.delete('password_phone_code:' + user.phone)

        logstr = '[ForgetPassword Put Success] User(id: {}): {}'
        logger.info(logstr.format(user.id, user))
        return dict(message='密码修改成功')


class TradePasswordResource(Resource):  # FIXME
    method_decorators = [authenticate]

    urls = ['/trade_password']
    endpoint = 'trade_password'

    def post(self):
        user = get_current_user()
        if user.trade_password:
            abort(400, message='您已经有交易密码了')

        args = get_parser('user_set_trade_password').parse_args()
        if len(args['password']) < 8:
            abort(400, message="密码长度少于8位!")
        user.trade_password = args['password']
        if(user.trade_password == user.password):
            abort(400, message='交易密码和登录密码不能一样')
        db_session.commit()

        return dict(message='设置成功')

    def put(self):
        user = get_current_user()
        args = get_parser('user_change_trade_password').parse_args()

        if Config.get_bool('TRADE_PASSWORD_PHONE_CODE_ENABLE'):

            trade_password_phone_code = redis.get(
                'trade_password_phone_code:{}'.format(user.phone)
            ).decode()
            valid_phone_code = args['phone_code'] == trade_password_phone_code
            if not trade_password_phone_code or not valid_phone_code:
                abort(400, message='验证码错误')

        if not user.trade_password:
            abort(400, message='请先设置交易密码')
        if len(args['newpassword']) < 8:
            abort(400, message="1")
        user.trade_password = args['newpassword']
        if(user.trade_password == user.password):
            abort(400, message='交易密码和登录密码不能一样')

        redis.delete('trade_password_phone_code:' + user.phone)
        db_session.commit()
        return dict(message='2')


class ChangePhoneResource(Resource):
    method_decorators = [authenticate]

    urls = ['/change_phone']
    endpoint = 'change_phone'

    def put(self):
        user = get_current_user()
        args = get_parser('change_phone_put').parse_args()

        if not re.match('^[1][1-9][\d]{9}$', args['phone']):
            abort(400, message='新手机号码格式错误')

        current_phone_key = 'current_phone_phone_code:{}'.format(user.phone)
        new_phone_key = 'change_phone_phone_code:{}'.format(args['phone'])
        if not redis.exists(current_phone_key) or \
                not redis.exists(new_phone_key):
            abort(400, message='请先获取验证码')

        current_phone_code = redis.get(current_phone_key).decode()
        if not args['current_phone_code'] == current_phone_code:
            abort(400, message='当前手机验证码错误')
        change_phone_code = redis.get(new_phone_key).decode()
        if not args['change_phone_code'] == change_phone_code:
            abort(400, message='新手机验证码错误')

        user.phone = args['phone']
        db_session.commit()

        redis.delete(current_phone_key)
        redis.delete(new_phone_key)

        return dict(message='手机修改成功')


class AvatarResource(Resource):
    method_decorators = [authenticate]

    urls = ['/avatar']
    endpoint = 'avatar'
    csrf_exempt = True

    def post(self):
        if not request.files:
            abort(400, message='请选择上传图片')
        f = request.files['avatar']
        image_size = len(f.read())
        f.seek(0)
        if image_size > config['AVATAR_MAX_IMAGE_SIZE']:
            abort(413, message='上传的图片太大')
        if not allowed_file(f.filename):
            abort(400, message='图片格式错误')

        image_prefix = generate_user_id_uuid(session['user_id'])
        image_suffix = os.path.splitext(f.filename)[-1].lower()
        temp = tempfile.mkstemp(
            prefix=image_prefix, suffix=image_suffix, dir=config['TMP_FOLDER'])
        dir_image_name = os.path.join(
            config['TMP_FOLDER'], temp[1].split('/')[-1])
        os.write(temp[0], f.read())
        return dict(avatar=dir_image_name)

    def put(self):
        args = get_parser('avatar').parse_args()
        image_path = args['avatar']
        box = (args['left'], args['upper'], args['right'], args['lower'])
        user = get_current_user()
        region = Image.open(image_path).crop(box)
        region = region.resize((100, 100), Image.ANTIALIAS)
        avatar_path = os.path.join(config['AVATAR_FOLDER'],
                                   os.path.basename(image_path))
        region.save(avatar_path)

        exists_avatar = os.path.exists(user.avatar)
        if user.avatar and avatar_path != user.avatar and exists_avatar:
            sh.rm(user.avatar)

        if not user.avatar or user.avatar != avatar_path:
            user.avatar = avatar_path
            db_session.commit()

        if os.path.exists(image_path):
            sh.rm(image_path)  # PAY ATTENTION ON IT !!!
        return dict(message='头像裁剪成功')


class DuplicatedUserResource(Resource):
    method_decorators = []

    urls = ['/duplicated_user']
    endpoint = 'duplicated_user'

    def get(self):
        args = get_parser('duplicated_user').parse_args()
        for i in args:
            user = User.query.filter_by(**{i: args[i]}).first()
            args[i] = True if user else False
        return args


class FriendInviteResource(Resource):
    method_decorators = []

    urls = ['/friend_invitation/<string:code>']
    endpoint = 'friend_invitation'

    def get(self, code):
        user = User.query.filter(User.friend_invitation == code).first()

        if not user:
            abort(404, message='无效的好友邀请码')
        else:
            return dict(username=user.username)


class InviteCodeResource(Resource):
    method_decorators = []

    urls = ['/invite_code/<string:invite_code>']
    endpoint = 'invite_code'

    def get(self, invite_code):
        user = User.query.filter_by(invite_code=invite_code).first()
        if not user:
            abort(404, message='无效的好友邀请码')
        return dict(username=user.username)


class VipServerResource(Resource):
    method_decorators = [authenticate]

    urls = ['/vip_server']
    endpoint = 'vipserver'

    @marshal_with(get_field('vip_server'))
    def get(self):
        users = User.query.filter(User.is_server).all()
        return users  # FIXME 未知的获取VIP客服公式

    def put(self):
        args = get_parser('vip_server').parse_args()
        user = get_current_user()
        if user and not user.server and user.is_vip:
            user.server_id = args['id']
            db_session.commit()
        else:
            abort(400, message='请联系客服修改您的资料.')
        return dict(message='恭喜您成为VIP! ')


class VipResource(Resource):
    method_decorators = [authenticate]

    urls = ['/vip']
    endpoint = 'vip'

    def get(self):
            vip_commission = Config.get_float('VIP_COMMISSION')
            vip_duration = Config.get_float('VIP_TIME')
            return dict(vip_commission=vip_commission,
                        vip_duration=vip_duration)

    def put(self):
        if request.values['charge'] == 'true':
            user = get_current_user()
            vip_commission = Config.get_float('VIP_COMMISSION')
            vip_time = Config.get_float('VIP_TIME')

            if user.available_amount < vip_commission:
                abort(400, message='用户余额不足')
            if not user.vip_end_at:
                user.vip_end_at = datetime.datetime.now()
            user.vip_end_at += datetime.timedelta(days=vip_time)
            user.capital_deduct(Decimal(vip_commission))
            user.is_vip = True

            fundstr = '[VIP充值] 用户:{user} id:{uid}, 费用:{amount}'
            description = fundstr.format(
                user=user,
                uid=user.id,
                amount=vip_commission
            )
            Log.create_log(
                amount=vip_commission,
                user=user,
                added_at=datetime.datetime.now(),
                description=description
            )

            db_session.commit()
        return dict(message='续费VIP成功!')  # FIXME ERROR


class IdentifyingCodeResource(Resource):
    method_decorators = []

    urls = ['/identifying_code']
    endpoint = 'identifying_code'

    def get(self):
        args = get_parser('identifying_code').parse_args()
        code_type = args['type'].lower()

        if code_type not in config['IDENTIFYING_CODE_TYPES']:
            abort(400, message='验证码类型错误')

        code_chars = config['IDENTIFYING_CODE_CHARS']

        if code_type != 'admin_login':
            code_chars = code_chars.lower()
        code = random.sample(code_chars, 5)

        query_string = request.query_string.decode()
        if 'cb=' in query_string:
            # 微信登录验证码
            cb = query_string.split('cb=')[-1]
            wechat_login_key = '{}:{}'.format(cb, ''.join(code))
            redis.set(wechat_login_key, 0, 300)

        if not session.get('identifying_code'):
            session['identifying_code'] = {}
        session['identifying_code'][code_type] = code
        if code_type in ['login', 'register']:
            image = captcha_clear_image(code)
        else:
            image = captcha_image(code)
        data = io.BytesIO()
        image.save(data, 'JPEG', quality=70)
        data.seek(0)
        return send_file(data, mimetype='image/jpeg')


class RealNameAuthResource(Resource):
    method_decorators = []

    urls = ['/realname_auth']
    endpoint = 'realname_auth'

    def post(self):
        if not request.files:
            abort(400, message='请选择上传图片')
        card_front = request.files['card_front']
        card_back = request.files['card_back']
        card_front_size = len(card_front.read())
        card_back_size = len(card_back.read())
        card_front.seek(0)
        card_back.seek(0)

        max_size = config['AVATAR_MAX_IMAGE_SIZE']
        if card_front_size > max_size or card_back_size > max_size:
            abort(413, message='身份证图片太大')
        if not allowed_file(card_front.filename) or not \
                allowed_file(card_back.filename):
            abort(400, message='图片格式错误')

        image_prefix = generate_user_id_uuid(session['user_id'])
        card_front_suffix = os.path.splitext(card_front.filename)[-1].lower()
        card_back_suffix = os.path.splitext(card_back.filename)[-1].lower()
        card_front_prefix = '{}front'.format(image_prefix)
        card_back_prefix = '{}back'.format(image_prefix)
        card_front_temp = tempfile.mkstemp(
            prefix=card_front_prefix, suffix=card_front_suffix,
            dir=config['CARD_FOLDER'])
        card_back_temp = tempfile.mkstemp(
            prefix=card_back_prefix, suffix=card_back_suffix,
            dir=config['CARD_FOLDER'])

        card_front_image_name = os.path.join(
            config['CARD_FOLDER'], card_front_temp[1].split('/')[-1])
        card_back_image_name = os.path.join(
            config['CARD_FOLDER'], card_back_temp[1].split('/')[-1])

        os.write(card_front_temp[0], card_front.read())
        os.write(card_back_temp[0], card_back.read())
        return dict(card_front=card_front_image_name,
                    card_back=card_back_image_name)


class RegisterPhoneCodeResource(Resource):
    """ 注册短信发送 """
    method_decorators = []

    urls = ['/register_phone_code/<string:ver_code>/']
    endpoint = 'register_phone_code'

    def get(self, ver_code):

        keyword = 'register'
        logger.info(
            "[Register Phone Code - {}] IP: {}".format(keyword,
                                                       request.remote_addr))
        if request.headers.get('Platform') == 'wechat':
            ident_code = redis.get(ver_code)
            if not ident_code:
                abort(400, message='错误的图片验证码，如看不清请点击图片刷新验证码')
        else:
            session_vcode = session.get('identifying_code', {}).get('register')
            if not session_vcode:
                abort(400, message='不存在的图片验证码，请点击图片刷新!')
            session_vcode = ''.join(session_vcode)
            if ver_code.upper() != session_vcode.upper():
                abort(400, message='错误的图片验证码，如看不清请点击图片刷新验证码!')

        # 删除图片验证码
        if 'identifying_code' in session:
            del session['identifying_code']
        if(not Config.get_bool('TRADE_PASSWORD_PHONE_CODE_ENABLE')):
            abort(400, message='功能维护中。')

        if project_config['SMS_CODE_ALLOWED_KEYWORD_AUTHENTICATE'][keyword]:
            if 'user_id' not in session:
                abort(403, message='权限不足')

        if redis.get('click_gap_ip:' + request.remote_addr):
            abort(400, message='请求频率过高，请休息下。')
        redis.set('click_gap_ip:' + request.remote_addr, '1',
                  project_config['SMS_PHONE_CODE_GAP_IP'])

        func = getattr(phone_code_func, keyword)
        phone = func()

        ver_code = identifying_code()
        content = sms_content(
            ver_code, project_config['SMS_CODE_ALLOWED_KEYWORD_STR'][keyword])
        status, message = sms_send(content=content, to_phone=phone)

        if not status:
            logstr = '[{} Phone Code Error] Phone: {}'
            logger.error(logstr.format(keyword.upper(), phone))
            abort(400, message='{}'.format(message))
        redis.set('{}_phone_code:{}'.format(keyword, phone),
                  ver_code, project_config['SMS_VAILD_TIME_VALUE'])

        logger.info("[Phone Code Get Success - {}] Phone: {}".format(
                    keyword, phone))
        return dict(message='验证码已发送，注意查收!')


class RetrievePassowrdPhoneCodeResource(Resource):
    """ 找回密码短信发送 """
    method_decorators = []

    urls = ['/retrieve_password_phone_code/<string:ver_code>/']
    endpoint = 'retrieve_password_phone_code'

    def get(self, ver_code):
        keyword = 'retrieve_password'
        logger.info(
            "[retrieve_password Phone Code - {}] IP: {}".format(
                keyword, request.remote_addr))

        session_vcode = session.get('identifying_code',
                                    {}).get('retrieve_password')

        if not session_vcode:
            abort(400, message='不存在的图片验证码，请点击图片刷新!')

        session_vcode = ''.join(session_vcode)
        if ver_code.upper() != session_vcode.upper():
            abort(400, message='错误的图片验证码，如看不清请点击图片刷新验证码!')

        # 删除图片验证码
        if 'identifying_code' in session:
            del session['identifying_code']

        if(not Config.get_bool('TRADE_PASSWORD_PHONE_CODE_ENABLE')):
            abort(400, message='功能维护中。')

        if project_config['SMS_CODE_ALLOWED_KEYWORD_AUTHENTICATE'][keyword]:
            if 'user_id' not in session:
                abort(403, message='权限不足')

        if redis.get('click_gap_ip:' + request.remote_addr):
            abort(400, message='请求频率过高，请休息下。')
        redis.set('click_gap_ip:' + request.remote_addr, '1',
                  project_config['SMS_PHONE_CODE_GAP_IP'])

        func = getattr(phone_code_func, keyword)
        phone = func()

        ver_code = identifying_code()
        content = sms_content(
            ver_code, project_config['SMS_CODE_ALLOWED_KEYWORD_STR'][keyword])
        status, message = sms_send(content=content, to_phone=phone)

        if not status:
            logstr = '[{} Phone Code Error] Phone: {}'
            logger.error(logstr.format(keyword.upper(), phone))
            abort(400, message='{}'.format(message))
        redis.set('{}_phone_code:{}'.format(keyword, phone),
                  ver_code, project_config['SMS_VAILD_TIME_VALUE'])

        logger.info("[Phone Code Get Success - {}] Phone: {}".format(
                    keyword, phone))
        return dict(message='验证码已发送，注意查收!')


class PhoneCodeResource(Resource):
    method_decorators = []

    urls = ['/phone_code/<string:keyword>']
    endpoint = 'change_phone_code'

    def get(self, keyword=None):
        if keyword in ['register', 'retrieve_password']:
            abort(404)

        logger.info(
            "[Phone Code - {}] IP: {}".format(keyword, request.remote_addr))
        if keyword not in project_config['SMS_CODE_ALLOWED_KEYWORD']:
            abort(404)
        if(not Config.get_bool('TRADE_PASSWORD_PHONE_CODE_ENABLE')):
            abort(400, message='功能维护中。')
        if project_config['SMS_CODE_ALLOWED_KEYWORD_AUTHENTICATE'][keyword]:
            platform = request.headers.get('Platform')
            if 'user_id' not in session and \
                platform  not in project_config['BEARER_TOKEN_PLATFORM']:
                abort(403, message='权限不足')
        if redis.get('click_gap_ip:' + request.remote_addr):
            abort(400, message='请求频率过高，请休息下。')
        redis.set('click_gap_ip:{}'.format(request.remote_addr), '1',
                  project_config['SMS_PHONE_CODE_GAP_IP'])

        func = getattr(phone_code_func, keyword)
        phone = func()
        if redis.get('click_gap_phone:{}'.format(phone)):
            abort(400, message='请求频率过高，请休息下。')
        redis.set('click_gap_phone:{}'.format(phone),
                  '1', project_config['SMS_PHONE_CODE_GAP_PHONE'])
        ver_code = identifying_code()

        content = sms_content(
            ver_code, project_config['SMS_CODE_ALLOWED_KEYWORD_STR'][keyword])
        status, message = sms_send(content=content, to_phone=phone)
        redis.set('{}_phone_code:{}'.format(keyword, phone),
                  ver_code, project_config['SMS_VAILD_TIME_VALUE'])

        if not status:
            logstr = '[{} Phone Code Error] Phone: {}'
            logger.error(logstr.format(keyword.upper(), phone))
            abort(400, message='发送失败，{}'.format(message))

        logger.info(
            "[Phone Code Get Success - {}] Phone: {}".format(keyword, phone))
        return dict(message='验证码已发送，注意查收!')


class SourceWebsiteResource(Resource):

    method_decorators = []

    urls = ['/sourcewebsite']
    endpoint = 'sourcewebsite'

    def post(self):
        args = get_parser('session').parse_args()
        username = args['username']
        password = args['password']
        sourcewebsite = SourceWebsite.query.filter(
            SourceWebsite.name == username,
            SourceWebsite.password == password).first()
        if not sourcewebsite:
            abort(400, message='用户或密码错误 !')
        users = pagination(filtering(
            sorting(
                User.query.filter_by(source_website=sourcewebsite)
            )
        )).all()
        return marshal(users, get_field('sourcewebsite_field'))

    def get(self):
        args = get_parser('session').parse_args()
        username = args['username']
        password = args['password']
        sourcewebsite = SourceWebsite.query.filter(
            SourceWebsite.name == username,
            SourceWebsite.password == password).first()
        if not sourcewebsite:
            abort(400, message='用户或密码错误 !')
        users = pagination(filtering(
            sorting(
                User.query.filter_by(source_website=sourcewebsite)
            )
        )).all()
        return marshal(users, get_field('sourcewebsite_field'))
