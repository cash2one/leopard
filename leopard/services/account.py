import re
import logging
import datetime
from decimal import Decimal

from sqlalchemy import desc
from redis import Redis
from flask import Blueprint, make_response, request, redirect
from flask.ext.restful import marshal_with, Resource, abort, marshal

from leopard.helpers import (
    authenticate, filtering, get_current_user, get_field, pagination, sorting,
    generate_order_number, get_parser, get_enum, get_uwsgi)
from leopard.orm import (Deposit, Log, Withdraw, DepositPlatform, Bankcard,
                         Config, GiftPoint, RedPacket, CodeRedPacket,
                         RedPacketType, CodeRedPacketLog)
from leopard.comps.redis import pool

from leopard.conf import consts
from leopard.core.orm import db_session
from leopard.core.config import get_config
from leopard.services import logic
from leopard.services.restrict.account import (check_withdraw_post,
                                               withdraw_post)

account = Blueprint('account', __name__,
                    url_prefix='/account', template_folder='templates')
uwsgi = get_uwsgi()
redis = Redis(connection_pool=pool)
logger = logging.getLogger('rotate')
project_config = get_config('project')


class BankcardResoure(Resource):
    method_decorators = [authenticate]

    urls = ['/bankcard', '/bankcard/<int:bankcard_id>']
    endpoint = 'bankcard'

    @marshal_with(get_field('bankcard'))
    def get(self, bankcard_id=None):
        user = get_current_user()

        if(bankcard_id):
            bankcard = Bankcard.query.filter(
                Bankcard.user_id == user.id,
                Bankcard.id == bankcard_id).first()
            if not bankcard:
                abort(404, message='找不到页面')
            if project_config['BANKCARD_MOSAIC']:
                card = bankcard.card
                bankcard.card = card[0: 4] + '*' * (len(card) - 8) + card[-4:]
            return bankcard

        bankcards = pagination(
            filtering(
                sorting(
                    Bankcard.query.filter_by(user=user)
                )
            )
        ).all()
        if project_config['BANKCARD_MOSAIC']:
            for i in bankcards:
                card = i.card
                i.card = card[0: 4] + '*' * (len(card) - 8) + card[-4:]
        return bankcards

    def post(self, bankcard_id=None):
        user = get_current_user()
        args = get_parser('bankcard').parse_args()
        if len(user.bankcards) == project_config['BANKCARD_NUMBER_LIMIT']:
            abort(400, message='您不能在绑定更多的银行卡！')
        if not args['name'] or not args['card'] or not args['branch']:
            abort(400, message='银行卡、卡号或开户行信息不能为空')

        bankcard = Bankcard()
        bankcard.bank = args['name'] + ':' + args['branch']
        bankcard.card = args['card']
        bankcard.user = user

        db_session.commit()
        data = marshal(bankcard, get_field('bankcard'))
        data.update(message='添加成功！')
        return data

    def delete(self, bankcard_id=None):
        user = get_current_user()
        args = get_parser('bankcard_delete').parse_args()
        if Config.get_bool('TRADE_PASSWORD_ENABLE'):  # 是否开启交易密码功能
            if not user.trade_password_enable:
                abort(400, message='请先设置交易密码')
            if not user.check_trade_password(args['trade_password']):
                abort(400, message='错误的交易密码')

        #  认证支付上的银行卡删除
        if args['platform_type']:
            platform = DepositPlatform.query.filter_by(
                logic=args['platform_type']).first()
            if not platform:
                abort(400, message='删除银行卡有误')
            platform_logic = getattr(logic, platform.logic)
            platform_logic_obj = platform_logic(platform)
            user.no_agree = bankcard_id
            result = platform_logic_obj.delete_card(user)
            return  result

        bankcard = Bankcard.query.filter(Bankcard.user_id == user.id,
                                         Bankcard.id == bankcard_id).first()
        if not bankcard:
            abort(400, message='银行卡信息错误')
        elif bankcard.need_amount > Decimal('0.0'):
            abort(400, message='此卡还有%s元需提现'%(bankcard.need_amount))

        withdraw = Withdraw.query.filter(Withdraw.user_id == user.id, 
            Withdraw.status == get_enum('WITHDRAW_PENDING')).first()
        if withdraw:
            abort(400, message='你有正在提现操作,不可删除')

        db_session.delete(bankcard)
        db_session.commit()
        return dict(message='注销银行卡成功')


class DepositBankcardResoure(Resource):
    method_decorators = [authenticate]

    urls = ['/desposit_bankcard', '/desposit_bankcard/<string:platform_type>']
    endpoint = 'desposit_bankcard'

    @marshal_with(get_field('desposit_bankcard'))
    def get(self, platform_type=None):
        user = get_current_user()

        if platform_type:
            platform = DepositPlatform.query.filter_by(
                logic=platform_type).first()
            if not platform:
                abort(400, message='查询平台有误')
            platform_logic = getattr(logic, platform.logic)
            platform_logic_obj = platform_logic(platform)
            result = platform_logic_obj.query_card(user)

        return result


class WithdrawResoure(Resource):
    method_decorators = [authenticate]

    urls = ['/withdraw', '/withdraw/<int:withdraw_id>']
    endpoint = 'withdraw'

    @marshal_with(get_field('withdraw'))
    def get(self, withdraw_id=None):
        user = get_current_user()
        if withdraw_id:
            withdraw = Withdraw.query.filter(Withdraw.id == withdraw_id,
                                             Withdraw.user == user).first()
            if not withdraw:
                abort(404)
            return withdraw
        accounts = pagination(
            filtering(
                sorting(
                    Withdraw.query.filter_by(user=user)
                )
            )
        ).all()
        return accounts

    def post(self):
        user = get_current_user()
        args = get_parser('withdraw').parse_args()
        logger.info('[Withdraw POST] User(id: {}): {}, phone_code: {}, \
                    amount: {};'.format(user.id, user, args['phone_code'],
                                        args['amount']))

        args['amount'] = Decimal(str(args['amount']))
        check_withdraw_post(args, user)
        message = ''
        try:
            status_code, message = withdraw_post(args, user)
        except Exception as error:
            logfmt = '[Withdraw Post Error] User(id: {}): {}, Error: {}'
            logger.error(logfmt.format(user.id, user, error))
            abort(500, message='系统错误，请重试或联系客服处理。')

        if status_code != 200:
            abort(status_code, message=message)

        return dict(message='申请成功')

    def delete(self, withdraw_id=0):
        withdraw = Withdraw.query.get(withdraw_id)
        if not withdraw:
            abort(404, message='提现失败，请联系客服。')
        if withdraw.status != get_enum('WITHDRAW_PENDING'):
            abort(400, message='提现已经生效或取消，无法操作。')

        withdraw.cancel()
        db_session.commit()
        return dict(message='取消成功')


class DepositPlatformResource(Resource):
    method_decorators = [authenticate]

    urls = ['/deposit_platform', '/deposit_platform/<string:platform_type>']
    endpoint = 'deposit.platform'

    @marshal_with(get_field('deposit_planform'))
    def get(self, platform_type=None):
        if platform_type:
            return pagination(
            filtering(
                sorting(
                    DepositPlatform.query.filter_by(
                        is_show=True, is_mobile=True).order_by('priority desc')
                )
            )
        ).all()
        return pagination(
            filtering(
                sorting(
                    DepositPlatform.query.filter_by(
                        is_show=True, is_pc=True).order_by('priority desc')
                )
            )
        ).all()


class DepositResource(Resource):
    """ 充值接口 """
    method_decorators = [authenticate]

    urls = ['/deposit', '/deposit/<string:platform_type>']
    endpoint = 'deposit'

    @marshal_with(get_field('deposit'))
    def get(self, platform_type=None):
        user = get_current_user()
        accounts = pagination(
            filtering(
                sorting(
                    Deposit.query.filter_by(user=user)
                )
            )
        ).all()
        return accounts

    def post(self, platform_type=None):
        user = get_current_user()
        args = get_parser('deposit').parse_args()
        
        loginfo = "[Depost Post] User(id: {}): {}, Args: {};"
        logger.info(loginfo.format(user.id, user, args))
        platform = DepositPlatform.query.get(args['platform'])
        if not platform:
            abort(400, message='充值平台信息错误')
        try:
            deposit = Deposit()
            deposit.user = user
            deposit.amount = args['amount']
            deposit.comment = args['comment']
            deposit.bankcard_id = args['bankcard_id']
            deposit.platform_order = generate_order_number()
            deposit.platform_id = platform.id
            deposit.added_at = datetime.datetime.now()
            deposit.remote_addr = request.remote_addr

            platform_logic = getattr(logic, platform.logic)
            platform_logic_obj = platform_logic(platform)
            result = platform_logic_obj.send(deposit)

            db_session.commit()
            return result
        except Exception as e:
            loginfo = "[Deposit Post Error] User(id: {}): {}, Error: {};"
            logger.error(loginfo.format(user.id, user, e))
            if platform_type:
                return dict(message='充值遇到错误，请联系客服！')
            resinfo = ('/#!/account/deposit-new?error=充值操作遇到了问题，'
                       '请联系客服！')
            return make_response(redirect(resinfo))


class DepositReceiverResource(Resource):
    """ 第三方异步通知 """
    method_decorators = []

    urls = ['/deposit/<string:platform_id>/<string:recv_type>']
    endpoint = 'deposit_receiver'
    csrf_exempt = True

    def get(self, platform_id, recv_type):
        if recv_type not in['front', 'recv']:
            abort(404)

        platform = DepositPlatform.query.filter(
            DepositPlatform.logic == platform_id).first()
        platform_logic = getattr(logic, platform.logic)
        platform_logic_obj = platform_logic(platform)
        func = getattr(platform_logic_obj, recv_type)

        return func(request)

    def post(self, platform_id, recv_type):
        if recv_type not in['front', 'recv']:
            abort(404)

        platform = DepositPlatform.query.filter(
            DepositPlatform.logic == platform_id).first()
        platform_logic = getattr(logic, platform.logic)
        platform_logic_obj = platform_logic(platform)
        func = getattr(platform_logic_obj, recv_type)

        return func(request)


class LogResoure(Resource):
    method_decorators = [authenticate]

    urls = ['/log']
    endpoint = 'log'

    @marshal_with(get_field('log'))
    def get(self):
        user = get_current_user()
        accounts = pagination(
            filtering(
                sorting(
                    Log.query.filter_by(user=user)
                )
            )
        ).all()
        return accounts


class TenderRedPacketResoure(Resource):
    method_decorators = [authenticate]

    urls = ['/tender_red_packet/<int:tender_amount>']
    endpoint = 'tender_red_packet'

    @marshal_with(get_field('red_packet'))
    def get(self, tender_amount):
        now = datetime.datetime.now()
        user = get_current_user()
        redpackets = RedPacket.query.filter_by(
            user=user, is_use=False,
        ).filter(
            RedPacket.invest_amount <= tender_amount,
            RedPacket.expires_at > now,
        ).join(RedPacketType).filter(
            RedPacketType.logic.in_(get_enum('RED_CODE_SHOW'))
        ).order_by(desc(RedPacket.amount)).all()
        return redpackets


class RedPacketResoure(Resource):
    method_decorators = [authenticate]

    urls = ['/red_packet', '/red_packet/<int:red_packet_id>']
    endpoint = 'red_packet'

    @marshal_with(get_field('red_packet'))
    def get(self, red_packet_id=None):
        user = get_current_user()
        if red_packet_id:
            red_packet = RedPacket.query.filter(RedPacket.id == red_packet_id,
                                                RedPacket.user == user).first()
            if not red_packet:
                abort(404, message='找不到该红包')
            return red_packet
        accounts = pagination(
            filtering(
                sorting(
                    RedPacket.query.filter_by(user=user, is_show=True)
                )
            )
        ).all()
        return accounts

    def put(self, red_packet_id=None):
        user = get_current_user()
        red_packet = RedPacket.query.filter(RedPacket.id == red_packet_id,
                                            RedPacket.user == user).first()

        loginfo = '[RedPacket Put] User(id: {}): {}, RedPacket(id): {}'
        logger.info(loginfo.format(user.id, user, red_packet_id))

        if not red_packet:
            abort(404, message='找不到该红包')

        if not red_packet.never_expire and red_packet.have_expired:
            abort(400, message='红包已过期!')

        if red_packet.type.logic == consts.CODE_REDPACKET_TYPE_LOGIC:
            abort(400, message='只有投资时才能使用噢！')
        if red_packet.is_use:
            abort(400, message='该红包已经被使用!')
        if not red_packet.is_available:
            abort(400, message='该红包还不能使用!')
        red_packet.is_use = True
        user.active_amount += red_packet.amount
        if red_packet.type.logic == 'REGISTER_EXPERIENCE':
            user.experience_amount += red_packet.amount

        fundsfmt = '[红包提现] 红包类型:‹{rtype}› id:{rid}, 金额:{amount}'
        description = fundsfmt.format(
            rtype=red_packet.type.name,
            rid=red_packet.id,
            amount=red_packet.amount)

        Log.create_log(red_packet, description=description,
                       added_at=datetime.datetime.now())

        logger.info('[RedPacket Put Success] User(id: {}): {}, '
                    'RedPacket(id): {}'.format(user.id, user, red_packet_id))

        db_session.commit()
        return dict(message='红包使用成功')


class RedPacketFullResoure(Resource):
    method_decorators = [authenticate]

    urls = ['/red_packet_full']
    endpoint = 'red_packet_full'

    def put(self):
        user = get_current_user()
        red_packets = RedPacket.query.filter_by(
            user=user, is_use=False, is_available=True).all()

        loginfo = '[RedPacketFull Put] User(id: {}): {}, RedPacket: {}'
        logger.info(loginfo.format(user.id, user, red_packets))

        if not red_packets:
            abort(400, message='您没有可用的红包!')

        message = None
        for i in red_packets:
            # 投资后才能使用
            if i.type.logic == consts.CODE_REDPACKET_TYPE_LOGIC:
                message = '兑换的红包投资时才能使用!'
                continue
            if not i.never_expire and i.have_expired:
                message = '红包已过期!'
                continue
            i.is_use = True
            user.active_amount += i.amount
            if i.type.logic == 'REGISTER_EXPERIENCE':
                user.experience_amount += i.amount
            now = datetime.datetime.now()

            fundstr = '[红包提现] 红包类型:‹{rtype}› id:{rid}, 金额:{amount}'
            description = fundstr.format(
                rtype=i.type.name, rid=i.id, amount=i.amount)

            Log.create_log(i, description=description, added_at=now)

        logstr = '[RedPacketFull Put Success] User(id: {}): {}, RedPacket: {}'
        logger.info(logstr.format(user.id, user, red_packets))

        db_session.commit()
        if message:
            abort(400, message=message)
        return dict(message='红包全部使用成功')


class CodeRedPacketResoure(Resource):

    method_decorators = [authenticate]

    urls = ['/code_red_packet']
    endpoint = 'code_red_packet'

    def put(self):
        args = get_parser('code_red_packet').parse_args()
        if not re.match(consts.CODE_REDPACKET_PATTERN, args['code']):
            abort(400, message='兑换码格式错误!')

        exists = db_session.query(CodeRedPacket.query.filter_by(
            code=args['code']).exists()).scalar()
        if not exists:
            abort(400, message='不存在的红包兑换码!')

        user = get_current_user()
        code_packet = CodeRedPacket.query.filter_by(code=args['code']).first()
        if code_packet.have_expired:
            abort(400, message='兑换码已过期，不能兑换!')
        if (
            not code_packet.enabled and
            code_packet.logic != consts.CODE_REDPACKET_REUSE
        ):
            abort(400, message='该兑换码已使用，不能重复兑换!')
        log_len = CodeRedPacketLog.query.filter_by(code=args['code'],
                                                   user=user).all()
        if len(log_len) > 0:
            abort(400, message='您已兑换，不能重复兑换!')

        code_type = RedPacketType.query.filter_by(
            logic=consts.CODE_REDPACKET_TYPE_LOGIC
        ).first()

        if not code_type:
            abort(400, message='不存在的红包类型')

        redpacket = RedPacket()
        redpacket.name = code_packet.name
        redpacket.description = code_packet.description
        redpacket.amount = code_packet.amount
        redpacket.invest_amount = code_packet.invest_amount
        redpacket.user = user
        redpacket.is_available = False
        redpacket.type = code_type
        redpacket.calc_expires_at(code_packet.valid)

        codelog = CodeRedPacketLog()
        codelog.code = code_packet.code
        codelog.redpacket = code_packet
        codelog.user = user

        if code_packet.logic == consts.CODE_REDPACKET_SINGLE:
            code_packet.enabled = False

        db_session.add(codelog)
        db_session.add(redpacket)
        db_session.commit()
        return dict(message='红包兑换成功!')


class GiftPointResource(Resource):
    method_decorators = [authenticate]

    urls = ['/giftpoint']
    endpoint = 'giftpoint'

    @marshal_with(get_field('gift_points'))
    def get(self):
        user = get_current_user()
        gift_points = pagination(filtering(
            sorting(
                GiftPoint.query.filter_by(user=user)
            )
        )).all()
        return gift_points
