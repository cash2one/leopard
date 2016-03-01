import unittest
from decimal import Decimal
from leopard.core.automatic_invest import auto_invest_start
from leopard.core.config import get_config
from leopard.helpers import get_enum
from leopard.core.logging import setup_logging
from leopard.orm import Project, User, RepaymentMethod, Investment, Repayment, Plan, ProjectType, AutoInvestment, Log
from leopard.core.orm import create_engine_with_binding, db_session
from leopard.orm import UserFactory, ApplicationFactory, ProjectFactory

setup_logging()
enums = get_config('enum')
create_engine_with_binding('database')
repaymethods = '等额本息'
project_type = ProjectType.query.filter(ProjectType.logic == 'flow').first()


def decimalFormat(amount):
    return Decimal(str(amount)).quantize(Decimal('0.01'))


class AutoInvestCheck(unittest.TestCase):

    def setUp(self):
        user = UserFactory(username='自动投标测试', deposit_amount=Decimal('800000'))
        autoinvest = AutoInvestment(
            user=user, is_open=True, min_rate=1, max_rate=12, min_periods=1, max_periods=36, reserve_amount=Decimal('10'),
            min_amount=Decimal('100'), max_amount=Decimal('10000')
        )

        borrower = User.query.filter(User.username == '我是借款人').first()
        repaymethod = RepaymentMethod.query.filter(RepaymentMethod.name == repaymethods).first()
        application = ApplicationFactory(user=borrower, repay_method=repaymethod)
        project = ProjectFactory(
            name='自动投标测试', amount=Decimal('10000'), status=get_enum('PROJECT_AUTOINVEST'),
            borrowed_amount=Decimal('0'), application=application, repaymentmethod=repaymethod, type=project_type)
        db_session.commit()

    def tearDown(self):
        user = User.query.filter(User.username == '自动投标测试').first()
        autoinvest = AutoInvestment.query.filter(AutoInvestment.user == user).first()
        project = Project.query.filter(Project.name == '自动投标测试').first()
        for instance in db_session.query(Investment).filter(Investment.project == project).all():
            for plan in db_session.query(Plan).filter(Plan.investment == instance).all():
                db_session.delete(plan)
            db_session.delete(instance)
        for instance in db_session.query(Repayment).filter(Repayment.project == project).all():
            db_session.delete(instance)
        for instance in db_session.query(Log).filter(Log.user == user).all():
            db_session.delete(instance)
        db_session.delete(project)
        db_session.delete(autoinvest)
        db_session.delete(user)
        db_session.commit()

    def test_auto_invest(self):
        project = Project.query.filter(Project.name == '自动投标测试').first()
        if project.status == get_enum('PROJECT_AUTOINVEST'):
            autoinvest_list = db_session.query(AutoInvestment).join(AutoInvestment.user).filter(
                AutoInvestment.is_open == True,
                AutoInvestment.min_periods <= project.periods,
                AutoInvestment.max_periods >= project.periods,
                AutoInvestment.min_rate <= project.rate,
                AutoInvestment.max_rate >= project.rate,
                (User.deposit_amount + User.active_amount + User.income_amount - AutoInvestment.reserve_amount) >= AutoInvestment.min_amount
            ).all()
            auto_invest_start(db_session, project, autoinvest_list)
