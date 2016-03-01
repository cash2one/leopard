import logging
from decimal import Decimal

from leopard.helpers import generate_unique_code, float_quantize_by_two
from leopard.orm import (CodeRedPacket, RedPacketType, RedPacket,
    CodeRedPacketLog, Config, Message)

logger = logging.getLogger('rotate')

class GrantRedPacket(object):
    """红包"""

    def __init__(self, *args, **kwargs):
        user, amount, name, valid, session= args
        self.user = user
        self.amount = amount
        self.name = name
        self.valid = valid
        self.session = session
        self.invest_amount = None
        self.is_available = kwargs.get('is_available', False)
        self.enabled = kwargs.get('enabled', False)
        self.description = kwargs.get('description', None)
        self.packet_type = kwargs.get('packet_type')


    def create_red_code(self, invest_amount, logic='single'):
        self.invest_amount = invest_amount
        code_packet = CodeRedPacket()
        code_packet.name = self.name
        code_packet.amount = self.amount
        code_packet.invest_amount = self.invest_amount
        code_packet.valid = self.valid
        code_packet.calc_expires_at(code_packet.valid)
        code_packet.code = generate_unique_code(CodeRedPacket)
        code_packet.logic = logic
        code_packet.enabled = self.enabled
        code_packet.description = self.description
        self.session.add(code_packet)

        self._create_red_packet()
        self._code_red_log(code_packet)

    def _create_red_packet(self):
        redpacket = RedPacket()
        redpacket.name = self.name
        redpacket.description = self.description
        redpacket.amount = self.amount
        redpacket.invest_amount = self.invest_amount
        redpacket.user = self.user
        redpacket.is_available = self.is_available
        redpacket.type =  self.packet_type
        redpacket.calc_expires_at(self.valid)

        self.session.add(redpacket)

    def _code_red_log(self, code_packet):
        codelog = CodeRedPacketLog()
        codelog.code = code_packet.code
        codelog.redpacket = code_packet
        codelog.user = self.user

        self.session.add(codelog)


def get_valid_invest_amount(invest_amount, valid, packet_type):
    if not invest_amount:
        if isinstance(packet_type.invest_amount, (int, float, Decimal)):
            invest_amount =  packet_type.invest_amount \
                if packet_type.invest_amount > Decimal('0.0') else Decimal('0.0')
        else:
            invest_amount = Decimal('0.0')
    if not valid:
        valid = packet_type.valid \
            if packet_type.valid > 0 else 0

    return invest_amount, valid

def first_deposit(session, user):
    """ 第一次充值  """

    red_packet = session.query(RedPacket).filter(
        RedPacketType.logic == 'FIRST_RECORD_CODE',
        RedPacket.type_id == RedPacketType.id,
        RedPacket.user_id == user.id
    ).order_by(RedPacket.id).first()

    if red_packet:
        return None

    return _first_deposit_coderedpacket(session, user)


def _first_deposit_coderedpacket(session, user, invest_amount=None, 
        valid=None):
    """第一次充值代码红包奖励 """
    

    packet_type = RedPacketType.query.filter_by(
        logic='FIRST_RECORD_CODE').first()

    if not packet_type:
        logger.error('[CodeRedPacket Register Largess Error] - Error: {}'.format(
            '没找到红包FIRST_RECORD_CODE类型'))
        return None

    invest_amount, valid = get_valid_invest_amount(invest_amount, valid, packet_type)
    amount = Config.get_decimal(
            'CODEREDPACKET_FIRST_RECORD_AMOUNT')

    name = '首次充值代码红包'

    GrantRedPacket(user, amount, name, valid, session, 
        description='首次充值送代码红包', packet_type=packet_type
        ).create_red_code(invest_amount)



    title = '系统信息 - 您获赠一个首次充值代码红包'
    msgstr = '尊敬的用户 - 获赠一个{}元的首次充值代码红包！'
    content = msgstr.format(amount)

    Message.system_inform(to_user=user, title=title, content=content)
    logstr = ('[CodeRedPacket First Tender Largess Success] '
              'ser(id: {}): {}, amount: {}')
    logger.info(logstr.format(user.id, user, amount))

    msgstr = '您首次充值成功，你获赠一个{}元的首次充值代码红包！'
    message = msgstr.format(float_quantize_by_two(amount))

    return message


def red_register(session, user):
    return _register_coderedpacket(session, user)


def _register_coderedpacket(session, user, invest_amount=None, 
        valid=None):
    """ 注册送代码红包 """

    packet_type = RedPacketType.query.filter_by(
        logic='REGISTER_CODE').first()

    if not packet_type:
        logger.error('[CodeRedPacket Register Largess Error] - Error: {}'.format(
            '没找到红包REGISTER_CODE类型'))

        return None

    invest_amount, valid = get_valid_invest_amount(invest_amount, valid, packet_type)

    amount = Config.get_decimal(
            'CODEREDPACKET_REGISTER_AMOUNT')

    name = '注册代码红包'

    GrantRedPacket(user, amount, name, valid, session, 
        description='新用户注册代码红包', packet_type=packet_type
        ).create_red_code(invest_amount)

    title = '系统信息 - 您获赠一个注册代码红包'
    content = '尊敬的用户 - 您于 {} 注册，获赠一个{}元的注册代码红包！'.format(
        user.added_at.strftime('%Y年%m月%d日 %H:%M:%S'), amount)
    Message.system_inform(
        to_user=user, title=title, content=content)
    logstr = ('[CodeRedPacket Register Largess Success] User(id: {}): {}, '
              'amount: {}')
    logger.info(logstr.format(user.id, user, amount))


def first_tender_coderedpacket(session, user, investd_Amount, 
    invest_amount=None, valid=None):
    """第一次投资代码红包奖励"""

    red_packet = session.query(RedPacket).filter(
            RedPacketType.logic == 'FIRST_INVESTMENT_CODE',
            RedPacket.type_id == RedPacketType.id,
            RedPacket.user_id == user.id
        ).order_by(RedPacket.id).first()

    if red_packet:
        return None
    packet_type = RedPacketType.query.filter_by(
            logic='FIRST_INVESTMENT_CODE').first()

    if not packet_type:
        logger.error('[CodeRedPacket Register Largess Error] - Error: {}'.format(
            '没找到红包FIRST_INVESTMENT_CODE类型'))
        return None

    invest_amount, valid = get_valid_invest_amount(invest_amount, valid, packet_type)

    amount = Config.get_decimal(
            'CODEREDPACKET_FIRST_TENDER_AMOUNT')

    name = '首次投资代码红包'

    GrantRedPacket(user, amount, name, valid, session, 
        description='新用户首次投资代码红包', packet_type=packet_type
        ).create_red_code(invest_amount)

    title = '系统信息 - 您获赠一个首次投资代码红包'
    msgstr = '尊敬的用户 - 您投资{}元，获赠一个{}元的首次投资代码红包！'
    content = msgstr.format(investd_Amount, amount)

    Message.system_inform(to_user=user, title=title, content=content)
    logstr = ('[CodeRedPacket First Tender Largess Success] '
              'user(id: {}): {}, amount: {}')
    logger.info(logstr.format(user.id, user, float_quantize_by_two(amount)))

    msgstr = '您首次投资{}元成功，你获赠一个{}元的首次投资代码红包！'
    message = msgstr.format(float_quantize_by_two(investd_Amount),
                            float_quantize_by_two(amount))

    return message



