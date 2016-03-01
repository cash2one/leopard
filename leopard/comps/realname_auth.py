import re
import json
import logging

from suds.client import Client
from leopard.core.config import get_config
from leopard.orm import RealnameAuth
from leopard.core.orm import db_session
from leopard.conf.consts import IDCARD_PATTERN


logger = logging.getLogger('comps')


config = get_config('realname.auth')

cred = {'UserName': config['USERNAME'], 'Password': config['PASSWORD']}
cred = json.dumps(cred)


def query_balance():
    """
    :函数名: 查询余额
    {
        "SimpleBalance": 19,
        "ExactBalance": 5,
        "ResponseCode": 100,
        "ResponseText": "成功"
    }
    """

    client = Client(config['REQUEST_URL'])
    data = client.service.QueryBalance('', cred)
    return data


def simple_check(user_id, idcard, realname):
    """
    :函数名: 简单认证
    {
        "Identifier": {
            "IDNumber": "身份证号",
            "Name": "姓名",
            "FormerName": null,
            "Sex": "性别",
            "Nation": null,
            "Birthday": "1991-12-25",
            "Company": null,
            "Education": null,
            "MaritalStatus": null,
            "NativePlace": null,
            "BirthPlace": null,
            "Address": null,
            "Photo": "",
            "QueryTime": null,
            "IsQueryCitizen": false,
            "Result": "一致|不一致|库中无此号"
        },
        "RawXml": null,
        "ResponseCode": 100,
        "ResponseText": "成功"
    }
    """
    is_valid = re.match(IDCARD_PATTERN, idcard)
    logger.info('[实名认证 - 第三方服务 请求前] 身份证:{} 姓名:{} 是否合法:{}'.format(
                idcard, realname, is_valid))

    if not is_valid:
        return False, None

    obj = RealnameAuth.query.filter_by(idcard=idcard, result='一致').first()
    if obj and obj.user_id != user_id:
        return False, None
    elif obj and obj.realname != realname:
        return False, None

    obj = RealnameAuth.query.filter_by(idcard=idcard,
                                       realname=realname).first()
    if obj:
        if obj.result == '一致':
            return True, None
        else:
            return False, None

    req = {'IDNumber': idcard, 'Name': realname}
    req = json.dumps(req)

    client = Client(config['REQUEST_URL'])
    strdata = client.service.SimpleCheckByJson(req, cred)
    jsondata = json.loads(strdata)

    idcard = jsondata['Identifier']['IDNumber']
    realname = jsondata['Identifier']['Name']
    result = jsondata['Identifier']['Result']

    success = result == '一致'

    balance = query_balance()
    logger.info('[实名认证 - 请求第三方服务] 身份证:{} 姓名:{} data:{} {}'.format(
                idcard, realname, strdata, balance))

    if not obj or (obj and obj.result != '一致'):
        realname_auth = RealnameAuth(idcard=idcard,
                                     realname=realname,
                                     result=result,
                                     user_id=user_id)
    db_session.add(realname_auth)
    db_session.commit()

    return success, jsondata
