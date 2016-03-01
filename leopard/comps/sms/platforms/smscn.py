import logging
from leopard.core.config import get_config

import requests

logger = logging.getLogger('sms')
setup = get_config('project')
config = get_config('leopard.comps.sms.platforms')['smscn']


def sms_send(content, to_phone):
    params = dict(uid=config['USERNAME'],
                  pwd=config['PASSWORD'],
                  mobile=to_phone,
                  content=content.encode('gbk'))
    results = requests.get(config['URL'], params=params)
    r = results.content.decode("gbk").split("&")
    status, message = r[1].split("=")[1], r[2].split("=")[1]

    if status == '100':
        loginfo = (
            '[smscn Phone Code] phone:{}, content:{}, message:{}, status:{}.'
        )
        logger.info(loginfo.format(
                    to_phone, content, message, status_code.get(status)))
        return True, status_code.get(status)
    else:
        loginfo = (
            '[smscn Phone Code] phone:{}, content:{}, message:{}, error:{}.'
        )
        logger.error(loginfo.format(
                     to_phone, content, message, status_code.get(status)))
        return False, status_code.get(status)


def sms_content(ver_code, content):
    content = '{}尊敬的客户，您正在进行 - {}，短信验证码是 {}，有效期{}。{}'.format(
        setup.get('SMS_SIGN_MESSAGE'),
        content,
        ver_code,
        setup.get('SMS_VALID_TIME_EXPLAIN'),
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
