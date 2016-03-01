import requests
import logging

from bs4 import BeautifulSoup
from leopard.core.config import get_config

config = get_config('leopard.comps.sms.platforms')['b2mcn']
setup = get_config('project')

logger = logging.getLogger('rotate')


def sms_send(content, to_phone):
    params = dict(cdkey=config['CDKEY'], password=config['PASSWORD'], phone=to_phone, message=content)
    results = requests.get(config['URL'], params=params)
    soup = BeautifulSoup(results.text)
    message = soup.message.string
    error = soup.error.string
    
    if error == '0':
        logger.info('[b2mcn Phone Code] phone:{}, content:{}, message:{}, status:{}->{}.'.format(
            to_phone, content, message, error, status_code.get(error)))
        return True, status_code.get(error)
    else:
        logger.error('[b2mcn Phone Code] phone:{}, content:{}, message:{}, error:{}->{}.'.format(
            to_phone, content, message, error, status_code.get(error)))
        return False, status_code.get(error)


def register():
    url = 'http://sdk999ws.eucp.b2m.cn:8080/sdkproxy/registdetailinfo.action'
    params = dict(
        cdkey=config['CDKEY'],
        password=config['PASSWORD'],
        ename='河北易简投资管理有限公司',
        linkman='苗昆',
        phonenum='18034563199',
        mobile='18034563199',
        email='kmiao@jishangjijin.com',
        fax='0311-87802367',
        address='河北省石家庄市桥东区建设北大街120号',
        postcode='050000'
    )
    results = requests.get(url, params=params)
    soup = BeautifulSoup(results.text)
    message = soup.message.string
    error = soup.error.string
    return dict(message=message, status=error)


def register_key():
    url = 'http://sdk999ws.eucp.b2m.cn:8080/sdkproxy/regist.action'
    params = dict(
        cdkey=config['CDKEY'],
        password=config['PASSWORD']
    )
    results = requests.get(url, params=params)
    soup = BeautifulSoup(results.text)
    message = soup.message.string
    error = soup.error.string
    return dict(message=message, status=error)


def query_balance():
    url = 'http://sdk999ws.eucp.b2m.cn:8080/sdkproxy/querybalance.action'
    params = dict(cdkey=config['CDKEY'], password=config['PASSWORD'])
    results = requests.get(url, params=params)
    soup = BeautifulSoup(results.text)
    message = soup.message.string
    error = soup.error.string
    return dict(message=message, status=error)


def sms_content(ver_code, content):
    content = '{} 尊敬的客户，您正在进行 - {}，短信验证码是 {}，有效期{}。{}'.format(
        setup.get('SMS_SIGN_MESSAGE'), content, ver_code, setup.get('SMS_VALID_TIME_EXPLAIN'),
        setup.get('SMS_SERVICE_PHONE')
    )
    return content

status_code = {
    '0': '操作成功',
    '304': '客户端发送三次失败',
    '305': '服务器返回了错误的数据，原因可能是通讯过程中有数据丢失',
    '307': '发送短信目标号码不符合规则，手机号码必须是以0、1开头',
    '308': '非数字错误，修改密码时如果新密码不是数字那么会报308错误',
    '3': '连接过多，指单个节点要求同时建立的连接数过多',
    '911005': '客户端注册失败,序列号或者密码有误',
    '911003': '客户端注册失败,序列号已注册且与当前客户赋值的password不同',
    '11': '企业信息注册失败',
    '12': '查询余额失败',
    '13': '充值失败',
    '14': '手机转移失败',
    '15': '手机扩展转移失败',
    '16': '取消转移失败',
    '17': '发送信息失败',
    '18': '发送定时信息失败',
    '22': '注销失败',
    '27': '查询单条短信费用错误码',
    '-1': '系统异常',
    '-2': '客户端异常',
    '-101': '命令不被支持',
    '-102': 'RegistryTransInfo删除信息失败',
    '-103': 'RegistryInfo更新信息失败',
    '-104': '请求超过限制',
    '-110': '号码注册激活失败',
    '-111': '企业注册失败',
    '-113': '充值失败',
    '-117': '发送短信失败',
    '-118': '接收MO失败',
    '-119': '接收Report失败',
    '-120':'修改密码失败',
    '-122': '号码注销激活失败',
    '-123': '查询单价失败',
    '-124': '查询余额失败',
    '-125': '设置MO转发失败',
    '-126': '路由信息失败',
    '-127': '计费失败0余额',
    '-128': '计费失败余额不足',
    '-190': '数据操作失败',
    '-1100': '序列号错误,序列号不存在内存中,或尝试攻击的用户',
    '-1102': '序列号密码错误',
    '-1103': '序列号Key错误',
    '-1104': '路由失败，请联系系统管理员',
    '-1105': '注册号状态异常, 未用 1',
    '-1107': '注册号状态异常, 停用 3',
    '-1108': '注册号状态异常, 停止 5',
    '-1131': '充值卡无效',
    '-1132': '充值密码无效',
    '-1133': '充值卡绑定异常',
    '-1134': '充值状态无效',
    '-1135': '充值金额无效',
    '-1901': '数据库插入操作失败',
    '-1902': '数据库更新操作失败'
}