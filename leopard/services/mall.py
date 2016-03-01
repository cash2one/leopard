import os
import logging
import datetime
import sqlalchemy
from decimal import Decimal

from redis import Redis
from flask import Blueprint, request
from flask.ext.restful import abort, marshal_with, Resource, marshal

from leopard.helpers import (authenticate, filtering, get_enum,
                             get_current_user, get_field, get_parser,
                             pagination, sorting, get_current_user_id,
                             get_config, plan_filtering, generate_unique_code,
                             float_quantize_by_two)
from leopard.orm import (Commodity, CommodityOrder, CodeRedPacket, 
                        RedPacketType, RedPacket, CodeRedPacketLog, Config,
                        GiftPoint)
from leopard.conf import consts
from leopard.comps.redis import pool
from leopard.core.orm import db_session


mall = Blueprint('mall', __name__, url_prefix='/mall')
redis = Redis(connection_pool=pool)
logger = logging.getLogger('mall')

class CommodityResource(Resource):

    urls = ['/commodity', '/commodity/<int:commodity_id>']
    endpoint = 'commodity'

    def get(self, commodity_id=None):
        if commodity_id:
            commodity = Commodity.query.filter_by(
                is_show=True,
                id=commodity_id
            ).first()

            if not commodity or commodity.number <0:
                abort(404)
            return marshal(commodity, get_field('commodity_detail'))
        commodity = pagination(
            filtering(
                sorting(
                    Commodity.query.filter_by(
                        is_show=True
                    ).order_by("priority desc")
                )
            )
        ).all()
        return marshal(commodity, get_field('commodity_field'))

    def post(self):
        pass


class CommodityOrderResource(Resource):
    method_decorators = [authenticate]

    urls = ['/commodity_order', '/commodity_order/<int:order_id>']
    endpoint = 'commodity_order'

    def get(self, order_id=None):
        user = get_current_user()
        if order_id:
            order = CommodityOrder.query.get(order_id)
            return marshal(order, get_field('commodity_order_list'))

        order = pagination(
            filtering(
                sorting(
                    CommodityOrder.query.filter_by(user=user)
                    )
                )
            ).all()
        return marshal(order, get_field('commodity_order_list'))

    def _redis_repeat_post_limit(self, order_id, user_id):
        pattern = 'BUYCOMMDITY:ORDER_iD:{}:USER_ID:{}'.format(
            order_id, user_id)
        if redis.exists(pattern):
            abort(400, message='请求太频繁请稍后重试')
        else:
            redis.set(pattern, 0, 3)

    def post(self, order_id):
        # return dict(message='购买成功!')
        args = get_parser('commodity_order').parse_args()
        user = get_current_user()
        if not user:
            abort(403, message='请先登录!')

        if Config.get_bool('TRADE_PASSWORD_ENABLE'):
            if not user.trade_password_enable:
                abort(400, message='请先设置交易密码')
            if not user.check_trade_password(args['trade_password']):
                abort(400, message='错误的交易密码')

        commodity = Commodity.query.get(order_id)
        buy_number = args['buy_number']
        if not buy_number > 0:
            abort(400, message='购买数量出错')

        if not commodity:
            abort(404, message='商品不存在')

        if commodity.number < buy_number:
            abort(404, message='库存不足')

        self._redis_repeat_post_limit(order_id, user.id)

        payamount = buy_number * commodity.price
        if user.gift_points < payamount:
            abort(400, message='宝币不足，请赚取')

        logfmt = "===== [兑换开始] 兑换用户 {}, 商品ID{}, 数量{} "
        loginfo = logfmt.format(user.username, order_id, buy_number)
        logger.info(loginfo)

        session = db_session()
        commodity.number -= buy_number

        logfmt = " - [宝币变化] <兑换用户 {} 宝币总额{}> 商品ID {}, 扣除宝币"
        loginfo = logfmt.format(user.username, user.gift_points, 
            order_id,  payamount)
        logger.info(loginfo)
        user.gift_points -= payamount

        msgstr = '您在宝币商城兑换的-{}，数量{}个，单价 {} 点宝币, 合计扣除 {} 点宝币'
        desc = msgstr.format(
            commodity.name,buy_number,
            '{:,.2f}'.format(commodity.price),
            '{:,.2f}'.format(payamount)
        )
        GiftPoint.add(user=user, points=payamount, description=desc)

        order = CommodityOrder()
        order.user = user
        order.commodity = commodity
        order.number = buy_number
        order.amount = Decimal(str(payamount))
        order.status = get_enum('ORDER_STATUS_PAYED')

        if commodity.type == get_enum('MALL_COMMODITY_VIRTAUL'):

            code_type = RedPacketType.query.filter_by(
                        logic=consts.CODE_REDPACKET_TYPE_LOGIC
                    ).first()
            quantity = buy_number

            while(1):
                if quantity <= 0:
                    break
                code_packet = CodeRedPacket()
                code_packet.name = commodity.name
                code_packet.amount = commodity.amount
                code_packet.invest_amount = commodity.invest_amount
                code_packet.valid = commodity.valid
                code_packet.calc_expires_at(code_packet.valid)
                code_packet.code = generate_unique_code(CodeRedPacket)
                code_packet.logic = 'single'
                code_packet.enabled = False
                code_packet.description = '宝币兑换所得红包'
                db_session.add(code_packet)

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

                db_session.add(codelog)
                db_session.add(redpacket)

                logfmt = " - [生成代码红包] 兑换用户 {}, 红包代码 {} ,生成顺序{} "
                loginfo = logfmt.format(user.username, code_packet.code, quantity)
                logger.info(loginfo)

                quantity -= 1
            order.status = get_enum('ORDER_STATUS_SUCCESS')
            order.process_at = datetime.datetime.now()

        elif commodity.type == get_enum('MALL_COMMODITY_MATERIAL'):
            order.addressee = args['addressee']
            order.phone = args['phone']
            order.address = args['address']
            order.description = args['description']

            logfmt = " - [生成收件人信息] 兑换用户 {}, 收件人 {}, 电话{} "
            loginfo = logfmt.format(user.username, order.addressee, order.phone)
            logger.info(loginfo)
        else:
            loginfo = " - CommodityOrderResource POST Error 不存在的商品类型 "
            logger.error(loginfo)
            abort(404, message='类型出错，请联系客服')

        session.add(order)
        session.commit()
        logfmt = "===== [兑换结束] 兑换用户 {} 商品ID{}"
        loginfo = logfmt.format(user.username, order_id)
        logger.info(loginfo)
        return dict(message='购买成功!')

