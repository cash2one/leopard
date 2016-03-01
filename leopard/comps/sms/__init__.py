import importlib
from leopard.core.config import get_config

config = get_config('project')

module = importlib.import_module(config['SMS_PLATFORM'])

sms_send = module.sms_send
sms_content = module.sms_content
