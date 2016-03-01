import logging
import hashlib
import urllib
import requests
import datetime
import xml.etree.ElementTree as element_tree
from decimal import Decimal
from flask import make_response, render_template, redirect
import simplejson as json

from leopard.orm import Deposit, Bankcard
from leopard.core.orm import db_session
from leopard.helpers import get_config, float_quantize_by_two

from leopard.apps.service.tasks import async_accept_deposit

logger = logging.getLogger('rotate')
project = get_config('project')


class Chinabank(object):
    """网银在线"""

    def __init__(self, platform):
        self.context = platform.dataset

    def accept(self, request, amount):
        async_accept_deposit.delay(request.values['v_oid'], amount)

    def reject(self, request, amount):
        recharge = Deposit.query.filter(
            Deposit.platform_order == request.values['v_oid']).first()
        recharge.amount = amount
        recharge.reject()
        db_session.commit()

    def validate_signature(self, request):
        d = request.values.to_dict().copy()
        encrypt_before = "{}{}{}{}{}".format(
            d['v_oid'],
            d['v_pstatus'],
            d['v_amount'],
            d['v_moneytype'],
            self.context['md5key'],
        )
        local_value = hashlib.md5(encrypt_before.encode()).hexdigest().upper()
        remote_value = request.values['v_md5str']
        return local_value == remote_value

    def get_signature(self, form):
        d = {}
        d.update(form)
        encrypt_before = "{}{}{}{}{}{}".format(
            d['v_amount'],
            d['v_moneytype'],
            d['v_oid'],
            d['v_mid'],
            d['v_url'],
            d['md5key']
        )
        return hashlib.md5(encrypt_before.encode()).hexdigest().upper()

    def create_form(self, recharge):
        form = {}
        form.update(self.context)
        form['v_oid'] = recharge.platform_order
        form.pop('action', None)
        form['v_amount'] = "{:.2f}".format(recharge.amount)
        form['v_url'] = project['HOST'] + form['v_url']
        form['v_md5info'] = self.get_signature(recharge, form)
        form['remark2'] = project['HOST'] + form['remark2']
        form.pop('md5key')
        return form

    def send(self, recharge):
        form = self.create_form(recharge)
        logger.info("[ChinaBank Send] form: {}".format(form))
        return make_response(render_template('recharge_ready_form.html',
                             action=self.context['action'], form=form))

    def recv(self, request):
        """
            充值 - 服务器回调
            1. v_pstatus 参数等于20 - 通过 其他参数为失败
            2. 完成后返回 ok
        """
        try:
            logger.info("[ChinaBank recv] values: {}".format(request.values))
            if self.validate_signature(request):
                if request.values['v_pstatust'] == '20':
                    self.accept(request, float(request.values['v_amount']))
                else:
                    self.reject(request, float(request.values['v_amount']))
        except Exception as exception:
            loginfo = "[ChinaBank recv Error] Request: {}, Error: {}"
            logger.error(loginfo.format(request, exception), exc_info=1)
            raise exception
        else:
            return make_response('OK')

    def front(self, request):
        """
            充值 - 浏览器回调
            1. v_pstatus 参数等于20 - 通过 其他参数为失败
            2. 完成后跳转到用户中心界面
        """
        try:
            logger.info("[ChinaBank recv] values: {}".format(request.values))
            if self.validate_signature(request):
                if request.values['v_pstatus'] == '20':
                    self.accept(request, float(request.values['v_amount']))
                    msgstr = '/#!/account/funding/deposit?success=您成功充值了{}元'
                    return make_response(
                        redirect(msgstr.format(
                            float_quantize_by_two(request.values['v_amount']))
                        )
                    )
                else:
                    self.reject(request, float(request.values['v_amount']))
                    msgstr = ('/#!/account/funding/deposit?error=抱歉！'
                              '您的充值操作遇到了问题，请联系客服！')
                    return make_response(redirect(msgstr))
        except Exception as exception:
            loginfo = "[ChinaBank front Error] Request: {}, Error: {}"
            logger.error(loginfo.format(request, exception), exc_info=1)
            raise exception
        else:
            return make_response(redirect('/#!/account/funding/deposit'))


class Offline(object):
    """线下充值"""

    def __init__(self, platform):
        self.context = platform.dataset

    def send(self, recharge):
        return dict(message='您已经成功提交线下充值订单，请等待客服处理！')


class Baofoo(object):
    """
        宝付
    """
    def __init__(self, platform):
        self.context = platform.dataset

    def accept(self, request, amount):
        async_accept_deposit.delay(request.values['TransID'], amount)

    def reject(self, request, amount):
        recharge = Deposit.query.filter(
            Deposit.platform_order == request.values['TransID']).first()
        recharge.amount = amount
        recharge.accept()
        db_session.commit()

    def validate_signature(self, request):
        d = request.values.to_dict().copy()
        md5_sign = "{}{}{}{}{}{}{}{}".format(
            d['MerchantID'],
            d['TransID'],
            d['Result'],
            d['resultDesc'],
            d['factMoney'],
            d['additionalInfo'],
            d['SuccTime'],
            self.context['Md5Key']
        ).encode('utf-8')
        local_value = hashlib.md5(md5_sign).hexdigest()
        remote_value = request.values['Md5Sign']
        return local_value == remote_value

    def get_signature(self, form):
        md5_sign = "{}{}{}{}{}{}{}{}{}".format(
            form['MerchantID'],
            form['PayID'],
            form['TradeDate'],
            form['TransID'],
            form['OrderMoney'],
            form['Merchant_url'],
            form['Return_url'],
            form['NoticeType'],
            form['Md5Key']
        ).encode('utf-8')
        return hashlib.md5(md5_sign).hexdigest()

    def create_form(self, recharge):
        form = {}
        form.update(self.context)
        form['TradeDate'] = recharge.added_at.strftime('%Y%m%d%H%M%S')
        form['TransID'] = recharge.platform_order
        form['OrderMoney'] = '{}'.format(int(recharge.amount * 100))
        form['Return_url'] = project['HOST'] + form['Return_url']
        form['Merchant_url'] = project['HOST'] + form['Merchant_url']
        form['ProductName'] = " "
        form['Amount'] = 1
        form['ProductLogo'] = " "
        form['Username'] = " "
        form['Email'] = " "
        form['Mobile'] = " "
        form['AdditionalInfo'] = " "
        form['Md5Sign'] = self.get_signature(form)
        form.pop('Md5Key')
        form.pop('action')
        return form

    def send(self, recharge):
        form = self.create_form(recharge)
        logger.info("[Baofoo Send] form: {}".format(form))
        return make_response(render_template('recharge_ready_form.html',
                             action=self.context['action'], form=form))

    def recv(self, request):
        logger.info("[Baofoo recv] form: {}".format(request.values.to_dict()))
        try:
            if self.validate_signature(request):
                amount = float(request.values.get('factMoney', 0))
                amount = Decimal(str(amount / 100))
                if request.values['Result'] == '1':
                    self.accept(request, amount)
                else:
                    self.reject(request, amount)
        except Exception as exception:
            logger.error('[Baofoo Recv Error] Error: {}'.format(exception),
                         exc_info=1)
            raise exception
        else:
            return make_response('OK')

    def front(self, request):
        logger.info("[Baofoo front] form: {}".format(request.values.to_dict()))
        try:
            if self.validate_signature(request):
                amount = float(request.values.get('factMoney', 0))
                amount = Decimal(str(amount / 100))
                if request.values['Result'] == '1':
                    self.accept(request, amount)
                    msgstr = '/#!/account/funding/deposit?success=您成功充值了{}元！'
                    return make_response(
                        redirect(msgstr.format(float_quantize_by_two(amount)))
                    )
                else:
                    self.reject(request, amount)
                    msgstr = ('/#!/account/funding/deposit?error=抱歉！'
                              '您的充值操作遇到了问题，请联系客服！')
                    return make_response(redirect(msgstr))
        except Exception as exception:
            logger.error('[Baofoo Front Error] Error: {}'.format(exception),
                         exc_info=1)
            msgstr = '/#!/account/funding/deposit?error=抱歉！您的充值操作遇到了问题，请联系客服！'
            return make_response(redirect(msgstr))
        else:
            return make_response(redirect('/#!/account/funding/deposit'))


class Ebatong(object):
    """
        贝付
    """
    def __init__(self, platform):
        self.context = platform.dataset

    def accept(self, request, amount):
        async_accept_deposit.delay(request.values['out_trade_no'], amount)

    def reject(self, request, amount):
        recharge = Deposit.query.filter(
            Deposit.platform_order == request.values['out_trade_no']).first()
        recharge.amount = amount
        recharge.reject()
        db_session.commit()

    def validate_signature(self, request):
        d = request.values.to_dict().copy()
        d.pop('sign', None)
        plain = '{}{}'.format(
            '&'.join(['%s=%s' % (k, d[k]) for k in sorted(d.keys())]),
            self.context['certification']
        ).encode('utf-8')

        local_value = hashlib.md5(plain).hexdigest()
        remote_value = request.values['sign']
        return local_value == remote_value

    def get_signature(self, form):
        d = {}
        d.update(form)
        d.pop('sign', None)
        plain = '{}{}'.format(
            '&'.join(['%s=%s' % (k, d[k]) for k in sorted(d.keys())]),
            self.context['certification']
        ).encode('utf-8')
        return hashlib.md5(plain).hexdigest()

    def query_timestamp(self, partner, sign):
        data = {
            'service': 'query_timestamp',
            'partner': partner,
            'input_charset': 'UTF-8',
            'sign_type': 'MD5',
            'sign': sign
        }
        data = urllib.parse.urlencode(data)

        requrl = 'https://www.ebatong.com/gateway.htm?{}'.format(data)
        resp_data = requests.get(requrl)
        xml = resp_data.text
        tree = element_tree.XML(xml)
        is_success = tree.findtext('is_success')
        encrypt_key = ''
        if is_success == 'T':
            encrypt_key = tree.find('response').find('timestamp').findtext(
                'encrypt_key')
        return encrypt_key

    def get_timestamp(self):
        form = {}
        partner = self.context['partner']
        form['input_charset'] = 'UTF-8'
        form['partner'] = partner
        form['service'] = 'query_timestamp'
        form['sign_type'] = 'MD5'
        sign = self.get_signature(form)
        encrypt_key = self.query_timestamp(partner, sign)

        if encrypt_key != "":
            return encrypt_key
        else:
            msgstr = '/#!/account/funding/deposit?error=抱歉！您的充值操作遇到了问题，请联系客服！'
            return make_response(redirect(msgstr))

    def create_form(self, recharge):
        form = {}
        form.update(self.context)
        form.pop('action', None)
        form.pop('certification', None)
        form['out_trade_no'] = recharge.platform_order
        form['return_url'] = project['HOST'] + form['return_url']
        form['notify_url'] = project['HOST'] + form['notify_url']
        form['total_fee'] = '{:.2f}'.format(recharge.amount)
        form['anti_phishing_key'] = self.get_timestamp()
        form['exter_invoke_ip'] = recharge.remote_addr
        form['sign'] = self.get_signature(form)
        return form

    def send(self, request):
        form = self.create_form(request)
        logger.info("[Ebatong Send] form: {}".format(form))
        return make_response(render_template('recharge_ready_form.html',
                             action=self.context['action'], form=form))

    def recv(self, request):
        """ 第三方通知 """
        logger.info("[Ebatong Recv] form: {}".format(request.values.to_dict()))
        try:
            if self.validate_signature(request):
                total_fee = Decimal(str(request.values['total_fee']))
                if request.values['trade_status'] == 'TRADE_FINISHED':
                    self.accept(request, total_fee)
                else:
                    self.reject(request, total_fee)
        except Exception as e:
            logger.error('[Ebatong Recv Error] Error: {}'.format(e),
                         exc_info=1)
            raise e
        else:
            return make_response('{}'.format(request.values['notify_id']))

    def front(self, request):
        loginfo = "[Ebatong Front] form: {}"
        logger.info(loginfo.format(request.values.to_dict()))
        try:
            if self.validate_signature(request):
                total_fee = Decimal(str(request.values['total_fee']))
                if request.values['trade_status'] == 'TRADE_FINISHED':
                    self.accept(request, total_fee)
                    msgstr = '/#!/account/funding/deposit?success=您成功充值了{}元！'
                    total_fee = float_quantize_by_two(
                        request.values['total_fee'])

                    return make_response(
                        redirect(msgstr.format(total_fee))
                    )
                else:
                    self.reject(request, total_fee)
                    msgstr = ('/#!/account/funding/deposit?error=抱歉！'
                              '您的充值操作遇到了问题，请联系客服！')
                    return make_response(redirect(msgstr))
        except Exception as e:
            logger.error('[Ebatong Front Error] Error: {}'.format(e),
                         exc_info=1)
            msgstr = '/#!/account/funding/deposit?error=抱歉！您的充值操作遇到了问题，请联系客服！'
            return make_response(redirect(msgstr))
        else:
            return make_response(redirect('/#!/account/funding/deposit'))


class Yintong(object):
    """
        连连网银支付
    """
    def __init__(self, platform):
        self.context = platform.dataset

    def accept(self, request, amount):
        async_accept_deposit.delay(request.values['no_order'], amount)

    def reject(self, request, amount):
        recharge = Deposit.query.filter(
            Deposit.platform_order == request.values['no_order']).first()
        recharge.amount = amount
        recharge.reject()
        db_session.commit()

    def validate_signature(self, request):
        
        if type(request.values) == dict:
            d = request.values.copy()
        else:
            d = request.values.to_dict().copy()
        d.pop('sign', None)
        plain = '{}&key={}'.format(
            '&'.join(['%s=%s' % (k, d[k]) for k in sorted(d.keys()) 
                if d[k]]),
            self.context['key']
        ).encode('utf-8')

        local_value = hashlib.md5(plain).hexdigest()
        remote_value = request.values['sign']
        return local_value == remote_value

    def get_signature(self, form):
        d = {}
        d.update(form)
        d.pop('sign', None)
        plain = '{}&key={}'.format(
            '&'.join(['%s=%s' % (k, d[k]) for k in sorted(d.keys())
                if d[k]]),
            self.context['key']
        ).encode('utf-8')
        return hashlib.md5(plain).hexdigest()

    def create_form(self, recharge):
        form = {}
        form.update(self.context)
        form.pop('action', None)
        form.pop('key', None)
        form['no_order'] = recharge.platform_order
        form['user_id'] = recharge.user.id
        form['dt_order'] = recharge.added_at.strftime('%Y%m%d%H%M%S')
        form['name_goods'] = recharge.user.username
        form['url_return'] = project['HOST'] + form['url_return']
        form['notify_url'] = project['HOST'] + form['notify_url']
        form['money_order'] = '{:.2f}'.format(recharge.amount)
        form['userreq_ip'] = recharge.remote_addr.replace('.','-')
        form['timestamp'] = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        form['sign'] = self.get_signature(form)

        return form

    def send(self, request):
        form = self.create_form(request)
        logger.info("[Yintong Send] form: {}".format(form))
        return make_response(render_template('recharge_ready_form.html',
                             action=self.context['action'], form=form))

    def recv(self, request):
        """ 第三方通知 """
        logger.info("[Yintong Recv] form: {}".format(request.data.decode('utf-8')))
        try:
            request_data = json.loads(request.data.decode('utf-8'))
            request.values = request_data
            if self.validate_signature(request):
                money_order = Decimal(str(request.values['money_order']))
                if request.values['result_pay'] == 'SUCCESS':
                    self.accept(request, money_order)
                else:
                    self.reject(request, money_order)
        except Exception as e:
            logger.error('[Yintong Recv Error] Error: {}'.format(e),
                         exc_info=1)
            raise e
        else:
            return make_response("{'ret_code':'0000','ret_msg':'交易成功'}")

    def front(self, request):
        loginfo = "[Yintong Front] form: {}"
        logger.info(loginfo.format(request.values.to_dict()))
        try:
            if self.validate_signature(request):
                money_order = Decimal(str(request.values['money_order']))
                if request.values['result_pay'] == 'SUCCESS':
                    self.accept(request, money_order)
                    msgstr = '/#!/account/funding/deposit?success=您成功充值了{}元！'
                    money_order = float_quantize_by_two(
                        request.values['money_order'])

                    return make_response(
                        redirect(msgstr.format(money_order))
                    )
                else:
                    self.reject(request, money_order)
                    msgstr = ('/#!/account/funding/deposit?error=抱歉！'
                              '您的充值操作遇到了问题，请联系客服！')
                    return make_response(redirect(msgstr))
        except Exception as e:
            logger.error('[Yintong Front Error] Error: {}'.format(e),
                         exc_info=1)
            msgstr = '/#!/account/funding/deposit?error=抱歉！您的充值操作遇到了问题，请联系客服！'
            return make_response(redirect(msgstr))
        else:
            return make_response(redirect('/#!/account/funding/deposit'))

class YintongAuthentication(object):
    """
        连连认证支付
    """
    def __init__(self, platform):
        self.context = platform.dataset

    def accept(self, request, amount):
        async_accept_deposit.delay(request.values['no_order'], amount)

    def reject(self, request, amount):
        recharge = Deposit.query.filter(
            Deposit.platform_order == request.values['no_order']).first()
        recharge.amount = amount
        recharge.reject()
        db_session.commit()

    def validate_signature(self, request):
        
        if type(request.values) == dict:
            d = request.values.copy()
        else:
            d = request.values.to_dict().copy()
        d.pop('sign', None)
        plain = '{}&key={}'.format(
            '&'.join(['%s=%s' % (k, d[k]) for k in sorted(d.keys()) 
                if d[k]]),
            self.context['key']
        ).encode('utf-8')

        local_value = hashlib.md5(plain).hexdigest()
        remote_value = request.values['sign']
        return local_value == remote_value

    def dict_sort(self, k, v):

        if type(v) == dict:
            return '%s={%s}' % ( k, ','.join(['\"%s\":\"%s\"' % (kk, v[kk]) 
                for kk in sorted(v.keys()) ]))
        else:
            return  '%s=%s' % (k, v)

    def get_signature(self, form):
        d = {}
        d.update(form)
        d.pop('sign', None)
        plain = '{}&key={}'.format(
            '&'.join([ self.dict_sort(k, d[k]) for k in sorted(d.keys()) 
                if d[k]]),
            self.context['key']
        ).encode('utf-8')
        return hashlib.md5(plain).hexdigest()

    def get_risk_item(self, user):
        data = {}
        data['frms_ware_category'] = '2009'
        data['user_info_bind_phone'] = str(user.phone)
        data['user_info_dt_register'] = str(user.added_at.strftime('%Y%m%d%H%M%S'))
        data['user_info_full_name'] = user.realname
        data['user_info_id_no'] = user.card       
        data['user_info_id_type'] = "0"
        data['user_info_identify_type'] = '3'
        data['user_info_mercht_userlogin'] = user.username
        data['user_info_mercht_userno'] = str(user.id)
        data['user_info_identify_state'] = '1'
        return data


    def get_bankcard(self, id):
        bankcard = Bankcard.query.get(id)
        if bankcard:
            return bankcard.card
        return ''

    def create_form(self, recharge):
        data = {}
        form = {}
        form.update(self.context)
        form.pop('action', None)
        form.pop('key', None)
        form['user_id'] = str(recharge.user.id) + "_" + recharge.user.username
        form['no_order'] = recharge.platform_order
        form['dt_order'] = recharge.added_at.strftime('%Y%m%d%H%M%S')
        form['name_goods'] = recharge.user.username
        form['money_order'] = '{:.2f}'.format(recharge.amount)
        form['url_return'] = project['HOST'] + form['url_return']
        form['notify_url'] = project['HOST'] + form['notify_url']
        form['id_no'] = recharge.user.card
        form['acct_name'] = recharge.user.realname
        form['card_no'] = self.get_bankcard(recharge.bankcard_id)
        form['risk_item'] = self.get_risk_item(recharge.user)
        form['sign'] = self.get_signature(form)

        data['req_data'] = form
        return data

    def create_card_form(self, recharge):
        form = {}
        form['oid_partner'] = self.context.get('oid_partner')
        form['user_id'] = str(recharge.id) + "_" + recharge.username
        form['pay_type'] = 'D'
        form['sign_type'] = 'MD5'
        form['offset'] = '0'
        form['sign'] = self.get_signature(form)

        return form

    def delete_card_form(self, recharge):
        form = {}
        form['oid_partner'] = self.context.get('oid_partner')
        form['user_id'] = str(recharge.id) + "_" + recharge.username
        form['pay_type'] = 'D'
        form['sign_type'] = 'MD5'
        form['no_agree'] = recharge.no_agree
        form['sign'] = self.get_signature(form)

        return form

    def send(self, request):
        form = self.create_form(request)
        form['action'] = self.context['action']
        logger.info("[YintongAuthentication Send] form: {}".format(form))
        return form
    
    def query_card(self, request):
        form = self.create_card_form(request)
        logger.info("[YintongAuthentication query card] form: {}".format(form))
        action = "https://yintong.com.cn/queryapi/bankcardbindlist.htm"
        r = requests.post(action , data=json.dumps(form))
        request_data = json.loads(r.text)
        return request_data.get('agreement_list', {})
        
    def delete_card(self, request):
        form = self.delete_card_form(request)
        action = "https://yintong.com.cn/traderapi/bankcardunbind.htm"
        logger.info("[YintongAuthentication delete card] form: {}".format(form))
        r = requests.post(action , data=json.dumps(form))
        request_data = json.loads(r.text)
        return request_data


    def recv(self, request):
        """ 第三方通知 """
        logger.info("[YintongAuthentication Recv] form: {}".format(request.data.decode('utf-8')))
        try:
            request_data = json.loads(request.data.decode('utf-8'))
            request.values = request_data
            if self.validate_signature(request):
                money_order = Decimal(str(request.values['money_order']))
                if request.values['result_pay'] == 'SUCCESS':
                    self.accept(request, money_order)
                else:
                    self.reject(request, money_order)
        except Exception as e:
            logger.error('[YintongAuthentication Recv Error] Error: {}'.format(e),
                         exc_info=1)
            raise e
        else:
            return make_response("{'ret_code':'0000','ret_msg':'交易成功'}")

    def front(self, request):
        loginfo = "[YintongAuthentication Front] form: {}"
        logger.info(loginfo.format(request.values.to_dict()))
        try:
            if request.values['res_data']:
                request.values = json.loads(request.values['res_data'])
            if self.validate_signature(request):
                money_order = Decimal(str(request.values['money_order']))
                if request.values['result_pay'] == 'SUCCESS':
                    self.accept(request, money_order)
                    msgstr = project['MOBILE_HOST']  + '/#/truffle/account?success=您成功充值了{}元！'
                    money_order = float_quantize_by_two(
                        request.values['money_order'])

                    return make_response(
                        redirect(msgstr.format(money_order))
                    )
                elif request.values['result_pay'] == 'PROCESSING':
                    msgstr = project['MOBILE_HOST']  + '/#/truffle/account?success=充值{}元正在处理中！'
                    money_order = float_quantize_by_two(
                        request.values['money_order'])

                    return make_response(
                        redirect(msgstr.format(money_order))
                    )
                else:
                    self.reject(request, money_order)
                    msgstr = (project['MOBILE_HOST']  + '/#/truffle/account?error=抱歉！'
                              '您的充值操作遇到了问题，请联系客服！')
                    return make_response(redirect(msgstr))
        except Exception as e:
            logger.error('[Yintong Front Error] Error: {}'.format(e),
                         exc_info=1)
            msgstr = project['MOBILE_HOST']  + '/#/truffle/account?error=抱歉！，请联系客服！'
            return make_response(redirect(msgstr))
        else:
            return make_response(redirect(project['MOBILE_HOST']  + '/#/truffle/account'))
