import unittest
from decimal import Decimal
from leopard.core.business import tender, check_invest
from leopard.core.config import get_config
from leopard.core.logging import setup_logging
from leopard.orm import Project, User, RepaymentMethod, Investment, Repayment, Plan, ProjectType, Config, Log
from leopard.core.orm import create_engine_with_binding, db_session
from leopard.orm import (
    UserFactory, GuaranteeFactory, ApplicationFactory, ProjectFactory)

setup_logging()
enums = get_config('enum')
create_engine_with_binding('database')
repaymethods = '等额本息'


class MyCaseTest(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass