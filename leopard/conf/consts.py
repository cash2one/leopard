from leopard.core.config import get_config

project_config = get_config('project')

temp_fmt = 'truffle:{}:finapplication:uid:{{}}'
FINAPPLICATION_UID = temp_fmt.format(project_config['PLATFORM'])

temp_fmt = 'truffle:{}:finapplication:repay_limit:{{}}:{{}}:{{}}'
FINAPPLICATION_PLAN_REPAY_LIMIT = temp_fmt.format(project_config['PLATFORM'])

IDCARD_PATTERN = ('^[1-9]\\d{5}(\\d{2}|\\d{4})(0[1-9]|1[0-2])(0[1-9]|'
                  '[1,2][0-9]|3[0-1])(\\d{3}|\\d{3}[0-9,X,x])$')

BEARER_TOKEN = 'truffle:bearer_token:token:{}'
BEARER_TOKEN_ID = 'truffle:bearer_token:id:{}'


ADMIN_LOGIN_FMT = 'truffle:admin:login:ip:{}:username:{}'
LOGIN_LIMIT_FMT = 'truffle:admin:login:ip:{}:username:{}:limit'
ADMIN_LOGIN_NEED_CODE = 'truffle:admin:login:ip:{}'
ADMIN_CAN_NOT_LOGIN = 'truffle:admin:can_not_login:ip:{}'


CODE_REDPACKET_SINGLE = 'single'
CODE_REDPACKET_REUSE = 'reuse'
REDPACKET_LOGIC_CHOICES = {'single', 'reuse'}

# 红包代码字符
CODE_REDPACKET_CHARS = 'abcdefghijkmnpqrstuvwxy23456789'
CODE_REDPACKET_TYPE_LOGIC = 'EXCHANGE_CODE'
CODE_REDPACKET_PATTERN = '^[a-z0-9]{10}$'

# 短邀请码字符
INVITE_CODE_CHARS = 'abcdefghijkmnpqrstuvwxy23456789'

# 异步充值
ASYNC_DESPOSIT_USER_KEY = 'truffle:async:deposit:user_id:{}'

# 自动还款
ASYNC_PLAN_NO_AMOUNT = 'truffle:async:no_amount:plan_id:{}'
ASYNC_PLAN_KEY = 'truffle:async:plan_id:{}'
ASYNC_PLAN_USER_KEY = 'truffle:async:plan:user_id:{}'
