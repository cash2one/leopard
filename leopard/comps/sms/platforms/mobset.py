import logging
import requests
from requests.exceptions import ConnectionError, Timeout
from leopard.core.config import get_config

logger = logging.getLogger('sms')
setup = get_config('project')
config = get_config('leopard.comps.sms.platforms')['mobset']


def sms_send(content, to_phone):
    params = dict(LoginName=config['LOGINNAME'],
                  Passwd=config['PASSWD'],
                  CorpID=config['GORPID'], send_no=to_phone,
                  msg=content.encode('gbk'))

    try:
        results = requests.get(config['URL'], params=params, timeout=15)
        r = results.content.decode("gbk")
        status, message = r.split(',')
        status = int(status)
    except Timeout:
        loginfo = '[mobset Phone Code] 请求超时, 发送失败'
        logger.error(loginfo, exc_info=1)
        return False, '请求超时, 发送失败!'
    except ConnectionError:
        loginfo = '[mobset Phone Code] 连接错误, 发送失败'
        logger.error(loginfo, exc_info=1)
        return False, '连接错误, 发送失败!'

    if status > 0:
        logfmt = '[mobset Phone Code] phone:{}, content:{}, status:{}.'
        loginfo = logfmt.format(to_phone, content, status)
        logger.info(loginfo)
        return (True, '发送成功')
    else:
        logfmt = '[mobset Phone Code] phone:{}, content:{}, error:{}.'
        loginfo = logfmt.format(to_phone, content, status)
        logger.error(loginfo)
        return (False, '发送失败')

    return False, status_code.get(status)


def sms_content(ver_code, content):
    content = '尊敬的客户，您正在进行 - {}，短信验证码是 {}，有效期{}。{}'.format(
        content, ver_code, setup.get('SMS_VALID_TIME_EXPLAIN'),
        setup.get('SMS_SERVICE_PHONE')
    )
    return content


status_code = {
    '100': '发送成功',
    '101': '验证失败',
    '102': '短信不足',
    '103': '操作失败',
    '104': '非法字符',
    '105': '内容过多',
    '106': '号码过多',
    '107': '频率过快',
    '108': '号码内容空',
    '110': '禁止频繁单条发送',
    '112': '号码错误',
    '113': '定时时间格式不对',
    '114': '账号被锁',
    '116': '禁止接口发送',
    '117': '绑定IP不正确',
    '120': '系统升级'
}
