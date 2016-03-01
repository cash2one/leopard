import datetime
import logging
from decimal import Decimal
from leopard.helpers import get_enum, float_quantize_by_two, valid_expires
from leopard.orm import (Investment, Repayment, Log, Config, RedPacketType,
                         RedPacket, Message, GiftPoint)
from leopard.core import repayment_method
from leopard.core.red_packet import first_tender_coderedpacket
from leopard.core.repayment_method import get_total_interest, quantize_func
from leopard.core.repayment_plan import (generate_repayment_plans,
                                         generate_repayment_project_plans)
logger = logging.getLogger('tender')
alogger = logging.getLogger('admin')


class Tender(object):
    """投标父类"""

    def __init__(self, *args, **kwargs):
        user, project, amount = args
        self.commission = 0.00          # FIXME 投标手续费用
        self.user = user
        self.project = project
        self.amount = Decimal(str(amount))
        self.plans = []
        self.investment = None
        self.repayment = None
        self.redpacket_id = kwargs.get('redpacket_id', None)
        self.redpacket = None
        self.redpacket_use_amount = None
        self.repaymentmethod = project.repaymentmethod
        self.deduct_order = kwargs.get('deduct_order')
        self.can_use_expe = kwargs.get('can_use_expe', True)
        self.session = kwargs.get('session')
        self.invest_from_type = kwargs.get('invest_from', get_enum('MODE_OTHER'))
        self.invest_from = get_enum('MODE_FROM').get(self.invest_from_type, '手动投标')   

        if self.redpacket_id:
            self.get_tender_redpacket()

        self.total_interest = get_total_interest(self.amount, project)

    @staticmethod
    def calc_total_tender_amount(project, amount, redpacket):
        if amount + redpacket.amount <= project.lack_amount:
            return amount + redpacket.amount

        return project.lack_amount

    def get_tender_redpacket(self):
        self.redpacket = RedPacket.query.get(self.redpacket_id)
        if self.redpacket:
            logger.info('[投资红包使用] 原来投资金额:{} id:{} 金额:{} 过期时间:{}'.format(
                        self.amount, self.redpacket_id,
                        self.redpacket.amount, self.redpacket.expires_at))

            self.amount, redpacket_lack_amount = self._calc_tender_amount(
                self.redpacket.amount)
            self.redpacket_use_amount = \
                self.redpacket.amount - redpacket_lack_amount

            if redpacket_lack_amount > Decimal('0'):
                self.user.active_amount += redpacket_lack_amount
                msgstr = ('[投标红包返现] 投资人:‹{invest_user}› 金额:{amount}, '
                          '红包id:{redpacket_id} 投资方式:{invest_from}')
                description = msgstr.format(
                    invest_user=self.user.username,
                    amount=redpacket_lack_amount,
                    redpacket_id=self.redpacket_id,
                    invest_from=self.invest_from)

                logger.info('- {}'.format(description))
                Log.create_log(description=description, user=self.user,
                               amount=redpacket_lack_amount)
            elif redpacket_lack_amount == Decimal('0'):
                msgstr = ('[投标红包使用] 投资人:‹{invest_user}› 金额:{amount}, '
                          '红包id:{redpacket_id} 投资方式:{invest_from}')
                description = msgstr.format(
                    invest_user=self.user.username,
                    amount=self.redpacket.amount,
                    redpacket_id=self.redpacket_id,
                    invest_from=self.invest_from)

                logger.info('- {}'.format(description))
                Log.create_log(description=description, user=self.user,
                               amount=self.redpacket.amount)

            self.redpacket.use_at = datetime.datetime.now()
            self.redpacket.is_use = True
            self.redpacket.is_available = True
            logger.info('[投资金额变更] 现投资金额:{}'.format(self.amount))

    def _calc_tender_amount(self, redpacket_amount):
        """ 计算投资红包投资金额 """
        if self.amount + redpacket_amount <= self.project.lack_amount:
            return self.amount + redpacket_amount, 0

        if self.project.lack_amount < self.amount:
            raise Exception('投资金额异常')
            fmt = ('[投资金额异常] amount:{} redpacket_amount:{} '
                   'project:lack_amount:{}')
            logger.error(fmt.format(self.amount, redpacket_amount,
                         self.project.lack_amount))

        lack_amount = self.project.lack_amount - self.amount
        return self.project.lack_amount, redpacket_amount - lack_amount

    @staticmethod
    def get_total_interest(repayment_name, pv, nper, rate):
        """获取总利息"""
        pv = Decimal(str(pv))
        rate = Decimal(str(rate / 100))
        total_interest = rate * nper * pv

        if repayment_name == 'average_captial_plus_interest':
            rv = Decimal(str((1 + rate) ** nper))
            total_interest = (pv * rate * rv / (rv - 1)) * nper - pv

        return repayment_method.quantize_func(total_interest)

    def create_investment_repayment(self):
        """创建投资记录和还款记录"""
        investment = Investment.create_investment(
            user=self.user,
            amount=self.amount,
            project=self.project,
            commission=self.commission,
            total_interest=self.total_interest,
            redpacket_id=self.redpacket_id,
            invest_from=self.invest_from_type,
            status=get_enum('INVESTMENT_PENDING')
        )
        investment.origin_amount = self.amount

        logfmt = '- [投资记录] amount:{}, interest:{}'
        loginfo = logfmt.format(investment.amount, investment.interest)
        logger.info(loginfo)

        repayment = Repayment.create_repayment(
            amount=self.amount,
            project=self.project,
            investment=investment,
            user=self.project.user,
            total_interest=self.total_interest,
            status=get_enum('REPAYMENT_PENDING')
        )

        logfmt = '- [还款记录] amount:{}, interest:{}'
        loginfo = logfmt.format(repayment.amount, repayment.interest)
        logger.info(loginfo)

        self.investment = investment
        self.repayment = repayment

        return investment, repayment

    def income_reward_rate(self):
        """回款续投奖励比率 """
        month, nper_type = self.project.periods, self.project.nper_type
        if nper_type == get_enum('DAY_PROJECT'):
            reward_rate = 'INCOME_INVEST_DAY_REWARD'
        else:
            if month == 1:
                reward_rate = 'INCOME_INVEST_JAN_REWARD'
            elif month == 2:
                reward_rate = 'INCOME_INVEST_FEB_REWARD'
            elif 3 <= month <= 5:
                reward_rate = 'INCOME_INVEST_MARCH_TO_MAY_REWARD'
            elif 6 <= month <= 8:
                reward_rate = 'INCOME_INVEST_JUNE_TO_AUG_REWARD'
            elif 9 <= month <= 11:
                reward_rate = 'INCOME_INVEST_SEPT_TO_NOV_REWARD'
            else:
                reward_rate = 'INCOME_INVEST_DEC_AND_MORE_REWARD'

        return Config.get_decimal(reward_rate)

    def income_reward(self, amount):
        """回款续投奖励"""
        raise NotImplementedError('未实现的回款续投奖励')

    def invest_reward(self):
        """投资奖励"""
        raise NotImplementedError('未实现的投资奖励')

    def deduct_fees(self):
        """借款人扣费操作"""
        raise NotImplementedError('未实现的扣费方法')

    def capital_change(self):
        """资金变化"""
        raise NotImplementedError('未实现的资金变化方法')

    def after_tender(self):
        """投标之后"""
        raise NotImplementedError('未实现的投标后方法')

    def create_plan(self):
        """创建还款计划"""
        logger.info('- [还款计划] 生成')
        return generate_repayment_plans(self.user,
                                        self.amount,
                                        self.project,
                                        self.investment,
                                        self.repaymentmethod.logic)

    @staticmethod
    def first_investment(user, amount, session):
        """第一次投资"""
        red_packet = session.query(RedPacket).filter(
            RedPacketType.logic == 'REGISTER',
            RedPacket.type_id == RedPacketType.id,
            RedPacket.is_use == False,
            RedPacket.is_available == True,
            RedPacket.user_id == user.id
        ).order_by(RedPacket.id).first()

        if red_packet:
            red_packet.is_available = True
            title = '系统信息 - 您的注册红包激活成功'
            content = '尊敬的用户 - 您首次投资成功，您的注册红包已经被激活！'
            Message.system_inform(to_user=user, title=title, content=content)
            logfmt = ('[RedPacket Register Available] User(id: {}): {},'
                      'RedPacket(id): {}')
            loginfo = logfmt.format(user.id, user, red_packet.id)
            logger.info(loginfo)


        if Config.get_bool('CODEREDPACKET_FIRST_TENDER_ENABLE'):
            return first_tender_coderedpacket(session, user, amount)
        elif Config.get_bool('REDPACKET_FIRST_TENDER_ENABLE'):
            return Tender.first_tender_redpacket(session, user, amount)
        else:
            return None

    @staticmethod
    def first_tender_redpacket(session, user, amount):
        """第一次投资红包奖励"""

        rate = Config.get_decimal('REDPACKET_FIRST_TENDER_RATE') / 100
        rate = Decimal(str(rate))
        amount = Decimal(str(amount))

        red_packet = session.query(RedPacket).filter(
            RedPacketType.logic == 'FIRST_TENDER',
            RedPacket.type_id == RedPacketType.id,
            RedPacket.user_id == user.id
        ).order_by(RedPacket.id).first()

        if red_packet:
            return None

        packet_type = RedPacketType.query.filter_by(
            logic='FIRST_TENDER').first()
        red_packet = RedPacket()
        amount_limit = Config.get_decimal(
            'REDPACKET_FIRST_TENDER_AMOUNT_LIMIT')

        red_packet.amount = min(rate * amount, amount_limit)
        red_packet.user = user
        red_packet.type = packet_type
        red_packet.is_available = True

        title = '系统信息 - 您获赠一个首次投资红包'
        msgstr = '尊敬的用户 - 您投资{}元，获赠一个{}元的首次投资红包！'
        content = msgstr.format(amount, red_packet.amount)

        Message.system_inform(to_user=user, title=title, content=content)
        logstr = ('[RedPacket First Tender Largess Success] '
                  'ser(id: {}): {}, amount: {}')
        logger.info(logstr.format(user.id, user, red_packet.amount))

        msgstr = '您首次投资{}元成功，你获赠一个{}元的首次投资红包！'
        message = msgstr.format(float_quantize_by_two(amount),
                                float_quantize_by_two(red_packet.amount))

        return message

    def friend_investment_reward(self):
        """好友投资奖励

        :奖励: 投资金额的万分比 + 固额
        """
        award_expires = Config.get_int('FRIEND_INVITATION_AWARD_EXPIRES')

        invitation_award = Config.get_bool('FRIEND_INVITATION_AWARD_ENABLE')

        fmt = '[好友投资奖励] 投资人:{} id:{} 注册日期:{} 是否开启:{} 到期天数:{}'
        logger.info(fmt.format(
            self.user, self.user.id, self.user.added_at,
            invitation_award, award_expires)
        )

        if (
            invitation_award and self.user.invited and
            valid_expires(self.user.added_at, award_expires)
        ):
            award_rate = Config.get_decimal('FRIEND_INVITATION_AWARD_RATE')
            award_fixed = Config.get_decimal('FRIEND_INVITATION_AWARD_FIXED')

            award_rate = Decimal(str(award_rate / 10000))
            investment_amount = Decimal(str(self.investment.amount))
            award_fixed = Decimal(str(award_fixed))

            award = investment_amount * award_rate + award_fixed
            self.user.invited.deposit_amount += award

            fundstr = '[好友投资奖励] 投资人:{}, 投资:{} 邀请人获得:{}, 项目:<{}>'
            description = fundstr.format(self.investment.user,
                                         self.investment.amount,
                                         quantize_func(award),
                                         self.investment.project.name)

            logger.info('- {}'.format(description))
            Log.create_log(None, amount=award,
                           user=self.investment.user.invited,
                           description=description)

            title = '系统消息 - 好友投资奖励通知!'
            content = '尊敬的用户，您邀请的好友{}，投资{}元，您获得奖励{}元'.format(
                self.investment.user.username,
                float_quantize_by_two(self.investment.amount),
                float_quantize_by_two(award))
            Message.system_inform(to_user=self.investment.user.invited,
                                  title=title, content=content)


class FlowTender(Tender):
    """流转标"""
    def __init__(self, *args, **kwargs):
        super(FlowTender, self).__init__(*args, **kwargs)
        user, project, amount = self.user, self.project, self.amount
        loginfo = (
            '> [流转标] 投资人:{} amount:{}, 项目:<amount:{} rate:{} periods:{}>'
        )
        logger.info(loginfo.format(
            user, amount, project.amount, project.rate, project.periods
        ))

    def create_investment_repayment(self):
        now = datetime.datetime.now()
        super(FlowTender, self).create_investment_repayment()
        self.investment.status = get_enum('INVESTMENT_SUCCESSED')
        self.repayment.status = get_enum('REPAYMENT_START')
        self.investment.processed_at = now

        msgstr = '您投资的项目-{}，投资了{}元，获得 {} 点宝币'
        gift_point = self.investment.interest
        desc = msgstr.format(
            self.project.name,
            '{:,.2f}'.format(self.investment.amount),
            '{:,.2f}'.format(gift_point)
        )
        self.user.gift_points += gift_point
        GiftPoint.add(user=self.user, points=gift_point, description=desc)

    def capital_change(self):
        # 用户可用资金减少
        user, project, amount = self.user, self.project, self.amount

        # 扣除红包投资金额
        if self.redpacket_use_amount:
            inveset_amount = amount - self.redpacket_use_amount
        else:
            inveset_amount = amount
        income_amount_invest = user.capital_deduct(
            inveset_amount, order=self.deduct_order,
            can_use_expe=self.can_use_expe
        )

        project.borrowed_amount += amount           # 项目已借资金增加
        project.user.income_amount += amount        # 借款人资金增加

        self.invest_reward()                                  # 投资奖励
        self.invest_capital_record()                          # 投资资金记录
        self.income_reward(income_amount_invest)              # 回款续投奖励

        # 好友投资奖励 调整到还款的时候
        self.capital_change_log()                             # 输出日志

        return user, project

    def invest_reward(self):
        # 投标奖励(投资金额 * 百分比)
        amount = self.amount * self.project.invest_award
        if amount != Decimal('0.0'):
            self.user.deposit_amount += amount
            msgstr = ('[投标奖励] 投资人:‹{invest_user}› 奖励:{amount}, '
                      '投资方式:{invest_from}')
            description = msgstr.format(
                invest_user=self.user.username,
                amount=amount,
                invest_from=self.invest_from)

            logger.info('- {}'.format(description))
            Log.create_log(description=description, user=self.user,
                           amount=amount)

    def invest_capital_record(self):
        # 投资生效资金记录

        fundstr = ('[投标生效] 项目:«{project_name}» id:{project_id},'
                   '投资人:‹{invest_user}›, 资金扣除:{amount},'
                   '投资方式:{invest_from}')

        description = fundstr.format(
            invest_user=self.user,
            project_name=self.project,
            project_id=self.project.id,
            amount=quantize_func(self.amount),
            invest_from=self.invest_from
        )

        logger.info('- {}'.format(description))
        Log.create_log(description=description, user=self.user,
                       amount=self.amount)

        fundstr = ('[借款生效] 项目:«{project_name}» id:{project_id},借款人:'
                   '‹{borrower}›, 资金增加:{amount}, 投资方式:{invest_from}')
        description = fundstr.format(
            borrower=self.project.user,
            invest_user=self.user,
            project_name=self.project,
            project_id=self.project.id,
            amount=self.amount,
            invest_from=self.invest_from)

        logger.info('- {}'.format(description))
        Log.create_log(amount=self.amount,
                       user=self.project.user,
                       description=description)

    def income_reward(self, amount):
        """回款续投奖励

        :奖励: 续投金额的千分比
        """
        reward_rate = self.income_reward_rate()
        reward_enable = Config.get_config('INCOME_AMOUNT_INVEST_REWARD_ENABLE')

        if not reward_enable:
            logger.info('- [回款续投奖励] 未开启')
        elif reward_enable and amount == Decimal('0.00'):
            logger.info('- [回款续投奖励] 续投金额 {}'.format(amount))
        elif reward_enable and amount:
            reward_amount = amount * reward_rate / 1000
            self.user.deposit_amount += reward_amount

            logmt = ('[回款续投奖励] 项目:«{project}» id:{pid} 期数:{periods}'
                     ' 类型:{nper_type}, 投资人: ‹{invest_user}›, '
                     '投资:{amount}, 奖励:{reward}, 投资方式:{invest_from}')

            description = logmt.format(
                pid=self.project.id,
                periods=self.project.periods,
                nper_type=self.project.nper_type,
                project=self.project,
                invest_user=self.user,
                reward=quantize_func(reward_amount),
                amount=amount,
                invest_from=self.invest_from
            )

            logger.info('- {}'.format(description))
            Log.create_log(user=self.user, amount=reward_amount,
                           description=description)

    def deduct_fees(self):
        """
            扣费操作 (借款人扣费)
            借款管理费 ( 投资金额 * 借款管理费比例 千分比 )
            信息管理费 ( 投资金额 * 信息管理费比例 * 月数 )
        """
        user, project = self.project.user, self.project  # 借款人，项目
        borrow_manage_fee = Config.get_decimal('COMMISSION_BORROW_MANAGE_FEE')
        info_manage_fee = Config.get_decimal('COMMISSION_INFO_MANAGE_FEE')

        borrow_fee = borrow_manage_fee / 1000
        info_fee = info_manage_fee / 100

        borrow_fee = self.amount * borrow_fee
        info_fee = info_fee * self.amount * project.periods

        total_fee = borrow_fee + info_fee  # 总费用
        user.income_amount -= total_fee

        fundstr = ('[借款服务费] 项目:«{project_name}» id:{project_id}, '
                   '借款人: ‹{borrower}›, 总费用:{total_fee}, '
                   '投资方式:{invest_from}')

        description = fundstr.format(
            borrower=project.user,
            total_fee=total_fee,
            project_id=project.id,
            project_name=project.name,
            invest_from=self.invest_from
        )

        Log.create_log(description=description,
                       user=project.user,
                       amount=total_fee)

        return user, project

    def capital_change_log(self):
        loginfo = (
            '- [资金变化] 用户: <id:{uid}, {user}, 可用:{available_amount}>;'
            '项目: <id: {pid}, {project}, amount:{amount}, '
            '已借: {borrowed_amount}>;'
            '借款人: <可用:{project_user_amount}>'
        )

        loginfo = loginfo.format(
            uid=self.user.id,
            user=self.user,
            pid=self.project.id,
            project=self.project,
            borrowed_amount=self.project.borrowed_amount,
            amount=self.amount,
            available_amount=self.user.available_amount,
            project_user_amount=self.project.user.available_amount)

        logger.info(loginfo)

    def after_tender(self):
        project, investment, repayment, amount = (self.project,
                                                  self.investment,
                                                  self.repayment,
                                                  self.amount)

        lack_amount = project.amount - project.borrowed_amount
        if lack_amount < Decimal('0.01'):
            project.status = get_enum('PROJECT_REPAYING')

        if len(self.user.investments) > 1:
            message = '您已成功投资{}元 !'.format(investment.amount)
        else:
            message = Tender.first_investment(self.user, amount, self.session)

        tender_data = dict(plans=self.plans, investment=investment,
                           repayment=repayment, project=project, amount=amount)

        return tender_data, message

    def create_plan(self):
        return super(FlowTender, self).create_plan()


class CommonTender(Tender):
    """普通标"""

    def __init__(self, *args, **kwargs):
        super(CommonTender, self).__init__(*args, **kwargs)
        user, project, amount = self.user, self.project, self.amount
        loginfo = (
            '> [普通标] 投资人:{} amount:{}, 项目:<id:{} amount:{} rate:{} periods:{}'
        )
        logger.info(loginfo.format(
            user, amount, project.id, project.amount, project.rate,
            project.periods
        ))

    def capital_change(self):
        """
        资金变化
        * 项目已投金额增加
        * 用户冻结资金增加
        """
        user, project, amount = self.user, self.project, self.amount

        # 扣除红包投资金额
        if self.redpacket_use_amount:
            inveset_amount = amount - self.redpacket_use_amount
        else:
            inveset_amount = amount
        income_amount_invest = user.capital_deduct(
            inveset_amount, order=self.deduct_order,
            can_use_expe=self.can_use_expe
        )

        user.blocked_amount += amount               # 用户冻结资金增加
        project.borrowed_amount += amount           # 项目借资金增加

        logfmt = '- [资金变化] 投资:{}后, 项目已投资金:{}, 用户冻结资金:{}'
        loginfo = logfmt.format(
            amount, project.borrowed_amount, user.blocked_amount,
        )
        logger.info(loginfo)

        msgstr = '投标资金冻结, {}'.format(project.get_project_url())
        description = msgstr.format(project.id, project.name, project.id)
        Log.create_log(user=user, amount=amount, description=description)

        self.income_reward(income_amount_invest)    # 回款续投奖励

    def income_reward(self, amount):
        """
        :函数名称: 回款续投奖励
        :奖励: 续投金额的千分比
        """
        reward_rate = self.income_reward_rate()

        reward_enable = Config.get_config('INCOME_AMOUNT_INVEST_REWARD_ENABLE')
        if not reward_enable:
            logger.info('- [回款续投奖励] 未开启')
        elif reward_enable and amount == Decimal('0.00'):
            logger.info('- [回款续投奖励] 续投金额 {}'.format(amount))
        elif reward_enable and amount:
            reward_amount = amount * reward_rate / 1000
            self.user.deposit_amount += reward_amount

            logmt = ('[回款续投奖励] 项目:«{project}» id:{pid}, 投资人: '
                     '‹{invest_user}›, 投资:{amount}, 奖励:{reward}, '
                     '投资方式:{invest_from}')

            description = logmt.format(
                pid=self.project.id,
                project=self.project,
                invest_user=self.user,
                reward=quantize_func(reward_amount),
                amount=amount,
                invest_from=self.invest_from
            )

            logger.info('- {}'.format(description))
            Log.create_log(user=self.user, amount=reward_amount,
                           description=description)

    @staticmethod
    def deduct_fees(user, project):
        """借款手续费
        :todo::
            未完成
        """
        alogger.info('- [借款手续费] 未开启 TODO')

    @staticmethod
    def full_tender(project, session):
        project.status = get_enum('PROJECT_REPAYING')
        project.user.income_amount += project.borrowed_amount

        loginfo = '借款生效, {}'.format(project.get_project_url())

        msgstr = loginfo.format(project.id, project.name, project.id)
        Log.create_log(user=project.user, amount=project.borrowed_amount,
                       description=msgstr)

        title = '系统信息 - 您所申请的项目（{}），已通过审核！'.format(project.name)
        content = '尊敬的用户 - 您于 {} 申请的项目（{}），已通过满标审核！'.format(
            project.added_at.strftime('%Y年%m月%d日 %H:%M:%S'), project.name)
        Message.system_inform(to_user=project.user, title=title,
                              content=content)

        alogger.info('- 生成 [项目还款计划]')
        generate_repayment_project_plans(project,
                                         project.repaymentmethod.logic)

        alogger.info('- 生成 [还款计划]')
        CommonTender.generate_plans(project, project.repaymentmethod.logic,
                                    session)
        CommonTender.invest_reward(project)

    def create_plan(self):
        logger.info('- [还款计划] 需满标审核后生成')

    @staticmethod
    def generate_plans(project, repayment_name, session):
        """根据项目生成还款计划"""
        plan_list = []
        CommonTender.deduct_fees(project.user, project)

        # config_points_rate = Config.get_float('INVESTMENT_POINTS_RATE')
        # investment_points_rate = config_points_rate / 100
        # investment_points_rate = Decimal(str(investment_points_rate))

        day_project = project.nper_type == get_enum('DAY_PROJECT')
        activity_project = \
            project.repaymentmethod.logic == 'repayment_immediately'

        now = datetime.datetime.now()
        for investment in project.investments:
            repayment = investment.repayment
            gift_point = investment.interest
            user = investment.user      # 投资人

            weighted_amount = 0           # 加权金额
            # 秒标、天标不计算宝币
            if not (day_project or activity_project):
                weighted_amount = investment.periods * investment.amount

                msgstr = '您投资的项目-{}，投资了{}元，获得 {} 点宝币'
                description = msgstr.format(
                    investment.project.name,
                    '{:,.2f}'.format(investment.amount),
                    '{:,.2f}'.format(gift_point))
                investment.user.gift_points += gift_point
                GiftPoint.add(user=user, points=gift_point,
                              description=description)

            user.blocked_amount -= investment.amount

            # 好友邀请投资奖励 调整到还款的时候发放

            investment.status = get_enum('INVESTMENT_SUCCESSED')
            repayment.status = get_enum('REPAYMENT_START')
            investment.processed_at = now

            msgstr = '投标生效, 扣除冻结资金, 项目 - {}'.format(project.get_project_url())

            description = msgstr.format(project.id, project.name, project.id)
            alogger.info('- {}'.format(description))

            Log.create_log(user=user,
                           amount=investment.amount,
                           weighted_amount=weighted_amount,
                           description=description)

            plans = generate_repayment_plans(
                user=user,
                amount=investment.amount,
                project=project,
                investment=investment,
                repayment_name=repayment_name
            )

            plan_list.extend(plans)
        return plan_list

    @staticmethod
    def invest_reward(project):
        """
        :函数名称: 投资奖励
        :奖励: 投资金额的百分比
        """
        ratio = project.invest_award
        if ratio > Decimal('0.0'):
            for i in project.investments:
                amount = i.amount * ratio
                i.user.income_amount += amount
                msgstr = '[投标奖励] 投资人:‹{invest_user}› 奖励:{amount}.'
                description = msgstr.format(
                    invest_user=i.user.username,
                    amount=amount)

                logger.info('- {}'.format(description))
                Log.create_log(description=description, user=i.user,
                               amount=amount)

    @staticmethod
    def friend_investment_reward(investment):
        user = investment.user

        award_expires = Config.get_int('FRIEND_INVITATION_AWARD_EXPIRES')
        invitation_award = Config.get_bool('FRIEND_INVITATION_AWARD_ENABLE')

        fmt = '[好友投资奖励] 投资人:{} id:{} 注册日期:{} 是否开启:{} 到期天数:{}'
        logger.info(fmt.format(
            user, user.id, user.added_at,
            invitation_award, award_expires)
        )

        if (
            invitation_award and user.invited and
            valid_expires(user.added_at, award_expires)
        ):
            award_rate = Config.get_decimal('FRIEND_INVITATION_AWARD_RATE')
            award_fixed = Config.get_decimal('FRIEND_INVITATION_AWARD_FIXED')

            award_rate = Decimal(str(award_rate / 10000))
            investment_interest = Decimal(str(investment.amount))
            award_fixed = Decimal(str(award_fixed))

            award = investment_interest * award_rate + award_fixed
            user.invited.income_amount += award

            fundstr = '[好友投资奖励] 投资人:{}, 投资:{} 邀请人获得:{}, 项目:<{}>'
            description = fundstr.format(investment.user,
                                         investment.amount,
                                         award.quantize(Decimal('0.01')),
                                         investment.project.name)
            alogger.info('- {}'.format(description))

            Log.create_log(None, amount=award, user=investment.user.invited,
                           description=description)

            title = '系统消息 - 好友投资奖励通知!'
            content = '尊敬的用户，您邀请的好友{}，投资{}元，您获得奖励{}元'.format(
                investment.user.username,
                float_quantize_by_two(investment.amount),
                float_quantize_by_two(award))
            Message.system_inform(to_user=investment.user.invited,
                                  title=title, content=content)

    @staticmethod
    def flow_borrow(project, current_user, session):
        """流标操作"""
        message = None
        logstr = '[后台管理] 流标操作 开始 project:(id:{} {}) 操作人: {}'
        alogger.info(logstr.format(project.id, project, current_user))

        if project.status == get_enum('PROJECT_FAILED'):
            message = '项目 <{}> 已流标!'.format(project)
            alogger.info('[后台管理] 流标操作 {}'.format(message))
        elif project.status not in [get_enum('PROJECT_INVESTING'),
                                    get_enum('PROJECT_PENDING')]:
            message = '只有在投资中和审核中的项目才能流标'
            alogger.info('[后台管理] 流标操作 {}'.format(message))
        else:
            project.status = get_enum('PROJECT_FAILED')
            project.is_show = False

            investments = session.query(Investment).filter(
                Investment.project == project).all()
            session.query(Repayment).filter(
                Repayment.project == project).delete()

            for item in investments:
                logfmt = ('[后台管理] 流标操作 - （投资记录，冻结资金解冻）'
                          'project: {} investment: {}, user: {}')
                loginfo = logfmt.format(project, item, item.user)
                alogger.info(loginfo)

                if item.redpacket_id:
                    # 红包退还
                    redpacket = RedPacket.query.get(item.redpacket_id)
                    alogger.info('[后台管理] 流标操作 红包: {}'.format(redpacket))
                    if redpacket:
                        redpacket.refund()
                        fmt = '[后台管理] 流标操作 红包退还: id:{} {} {} {} {}'
                        alogger.info(fmt.format(
                            redpacket.id, redpacket, redpacket.amount,
                            redpacket.is_use, redpacket.is_available))

                item.status = get_enum('INVESTMENT_FAILED')     # 投资记录失败
                item.user.blocked_amount -= item.amount         # 冻结资金解冻
                item.user.income_amount += item.amount

                description = '[流标操作] 用户:{} 冻结资金解冻:{}'.format(
                    item.user, item.amount)
                Log.create_log(user=item.user, amount=item.amount,
                               description=description)
                title = '系统消息 - 您所投资的项目({})，已取消!'.format(project.name)
                msgstr = '尊敬的用户，您于{} 投资的项目({}) 已取消，解冻 {} 元'
                strftime = item.added_at.strftime('%Y年%m月%d日 %H:%M:%S')
                thaw_funds = '{:,.2f}'.format(
                    float_quantize_by_two(item.amount))

                content = msgstr.format(strftime, project.name, thaw_funds)
                Message.system_inform(to_user=item.user, title=title,
                                      content=content)
            else:
                logfmt = ('[后台管理] 流标操作 - 项目无投资记录 '
                          'project: {} investment: {}')
                loginfo = logfmt.format(project, investments)
                alogger.info(loginfo)
        return message

    def after_tender(self):
        """投标之后"""
        project, investment, repayment, amount = (self.project,
                                                  self.investment,
                                                  self.repayment,
                                                  self.amount)

        lack_amount = project.amount - project.borrowed_amount
        if not lack_amount >= Decimal('0.01'):
            project.status = get_enum('PROJECT_PENDING')

        if self.user.investments:
            message = '您已成功投资{}元 !'.format(investment.amount)
        else:
            message = Tender.first_investment(self.user, amount, self.session)

        tender_data = dict(plans=[], investment=investment,
                           repayment=repayment, project=project, amount=amount)
        return tender_data, message


def tender_func(*args, **kwargs):
    user, project, amount = args
    if project.type.logic == 'flow':
        tender = FlowTender(*args, **kwargs)
    elif project.type.logic == 'common':
        tender = CommonTender(*args, **kwargs)
    else:
        raise NotImplementedError('不存在的标种')

    tender.create_investment_repayment()        # 生成投资记录和还款记录
    tender.capital_change()                     # 资金变化
    tender.create_plan()                        # 创建还款计划
    data = tender.after_tender()
    return data
