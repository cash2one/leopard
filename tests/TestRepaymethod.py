import unittest
import math
from decimal import Decimal
from leopard.core.business import tender, check_invest
from leopard.core.config import get_config
from leopard.core.logging import setup_logging
from leopard.orm import Project, User, RepaymentMethod, Investment, Repayment, Plan, ProjectType, Log
from leopard.core.orm import create_engine_with_binding, db_session
from leopard.orm import (UserFactory, ApplicationFactory, ProjectFactory)

setup_logging()
enums = get_config('enum')
create_engine_with_binding('database')
project_type = ProjectType.query.filter(ProjectType.logic == 'flow').first()


def decimalFormat(amount):
    return Decimal(str(amount)).quantize(Decimal('0.0001'))


# class RepaymentMethodOneOnly(unittest.TestCase):

#     def setUp(self):
#         user = UserFactory(username='投标测试', available_amount=10000)
#         borrower = User.query.filter(User.username == '我是借款人').first()
#         repaymethod = RepaymentMethod.query.filter(RepaymentMethod.name == '一次性还款').first()
#         application = ApplicationFactory(user=borrower, repay_method=repaymethod)
#         project = ProjectFactory(
#             name='投标测试', amount=10000,
#             borrowed_amount=1000, application=application, repaymentmethod=repaymethod, type=project_type)
#         self.amount = 1000
#         db_session.commit()

#     def tearDown(self):
#         user = User.query.filter(User.username == '投标测试').first()
#         project = Project.query.filter(Project.name == '投标测试').first()
#         for instance in db_session.query(Investment).filter(Investment.project == project).all():
#             for plan in db_session.query(Plan).filter(Plan.investment == instance).all():
#                 db_session.delete(plan)
#             db_session.delete(instance)
#         for instance in db_session.query(Repayment).filter(Repayment.project == project).all():
#             db_session.delete(instance)
#         db_session.delete(project)
#         db_session.delete(user)
#         db_session.commit()

#     def test_investment(self):
#         user = User.query.filter(User.username == '投标测试').first()
#         project = Project.query.filter(Project.name == '投标测试').first()
#         amount = self.amount
#         results = check_invest(amount=amount, user=user, project=project)
#         if results.get('message'):
#             print(results.get('amount'), results.get('message'))
#         else:
#             data = tender(user=user, project=project, amount=results.get('amount'))  # 投标
#             db_session.commit()
#             plans = data.get('plans')
#             self.assertEqual(1, len(plans))
#             project = data.get('project')
#             interest = (project.rate/100) * project.periods * data.get('amount')
#             interests = decimalFormat(interest)
#             resultsInterest = 0.0
#             for item in plans:
#                 resultsInterest = Decimal(resultsInterest) + Decimal(item.interest)
#                 print(item.plan_time)
#             self.assertEqual(interests, resultsInterest)


# class RepaymentMethodInterestFirst(unittest.TestCase):

#     def setUp(self):
#         user = UserFactory(username='投标测试', available_amount=10000)
#         borrower = User.query.filter(User.username == '我是借款人').first()
#         repaymethod = RepaymentMethod.query.filter(RepaymentMethod.name == '一次性付息到期还本').first()
#         application = ApplicationFactory(user=borrower, repay_method=repaymethod)
#         project = ProjectFactory(
#             name='投标测试', amount=10000,
#             borrowed_amount=1000, application=application, repaymentmethod=repaymethod, type=project_type)
#         self.amount = 1000
#         db_session.commit()

#     def tearDown(self):
#         user = User.query.filter(User.username == '投标测试').first()
#         project = Project.query.filter(Project.name == '投标测试').first()
#         for instance in db_session.query(Investment).filter(Investment.project == project).all():
#             for plan in db_session.query(Plan).filter(Plan.investment == instance).all():
#                 db_session.delete(plan)
#             db_session.delete(instance)
#         for instance in db_session.query(Repayment).filter(Repayment.project == project).all():
#             db_session.delete(instance)
#         db_session.delete(project)
#         db_session.delete(user)
#         db_session.commit()

#     def test_investment(self):
#         user = User.query.filter(User.username == '投标测试').first()
#         project = Project.query.filter(Project.name == '投标测试').first()
#         amount = self.amount
#         results = check_invest(amount=amount, user=user, project=project)
#         if results.get('message'):
#             print(results.get('amount'), results.get('message'))
#         else:
#             data = tender(user=user, project=project, amount=results.get('amount'))  # 投标
#             db_session.commit()
#             plans = data.get('plans')
#             self.assertEqual(2, len(plans))
#             project = data.get('project')
#             interest = (project.rate/100) * project.periods * data.get('amount')
#             interests = decimalFormat(interest)
#             resultsInterest = 0.0
#             for item in plans:
#             	resultsInterest = Decimal(resultsInterest) + Decimal(item.interest)
#             self.assertEqual(interests, resultsInterest)


# class RepaymentMethodCapitalFinal(unittest.TestCase):

#     def setUp(self):
#         user = UserFactory(username='投标测试', available_amount=10000)
#         borrower = User.query.filter(User.username == '我是借款人').first()
#         repaymethod = RepaymentMethod.query.filter(RepaymentMethod.name == '按月付息到期还本').first()
#         application = ApplicationFactory(user=borrower, repay_method=repaymethod)
#         project = ProjectFactory(
#             name='投标测试', amount=10000,
#             borrowed_amount=1000, application=application, repaymentmethod=repaymethod, type=project_type)
#         self.amount = 1000
#         db_session.commit()

#     def tearDown(self):
#         user = User.query.filter(User.username == '投标测试').first()
#         project = Project.query.filter(Project.name == '投标测试').first()
#         for instance in db_session.query(Investment).filter(Investment.project == project).all():
#             for plan in db_session.query(Plan).filter(Plan.investment == instance).all():
#                 db_session.delete(plan)
#             db_session.delete(instance)
#         for instance in db_session.query(Repayment).filter(Repayment.project == project).all():
#             db_session.delete(instance)
#         db_session.delete(project)
#         db_session.delete(user)
#         db_session.commit()

#     def test_investment(self):
#         user = User.query.filter(User.username == '投标测试').first()
#         project = Project.query.filter(Project.name == '投标测试').first()
#         amount = self.amount
#         results = check_invest(amount=amount, user=user, project=project)
#         if results.get('message'):
#             print(results.get('amount'), results.get('message'))
#         else:
#             data = tender(user=user, project=project, amount=results.get('amount'))  # 投标
#             db_session.commit()
#             plans = data.get('plans')
#             project = data.get('project')
#             self.assertEqual(project.periods, len(plans))
#             interest = (project.rate/100) * project.periods * data.get('amount')
#             interests = Decimal(interest).quantize(Decimal('0.01'))
#             resultsInterest = 0.0
#             for item in plans:
#             	resultsInterest = Decimal(resultsInterest) + Decimal(item.interest)
#             	# print('+++', item.id, '  ', item.interest)
#             print('+++每月付息到期还本 计算出来的和+++', resultsInterest)
#             print('+++++每月付息到期还本 公式算出来的++++', interests)
#             # self.assertEqual(interests, resultsInterest)


class RepaymentMethodAverageCaptialPlusInterest(unittest.TestCase):

    def setUp(self):
        user = UserFactory(username='等额本息投标测试', deposit_amount=10000)
        borrower = User.query.filter(User.username == '我是借款人').first()
        repaymethod = RepaymentMethod.query.filter(RepaymentMethod.name == '等额本息').first()
        application = ApplicationFactory(user=borrower, repay_method=repaymethod)
        project = ProjectFactory(
            name='等额本息投标测试', amount=10000,
            borrowed_amount=1000, application=application, repaymentmethod=repaymethod, type=project_type)
        self.amount = 1000
        db_session.commit()

    def tearDown(self):
        user = User.query.filter(User.username == '等额本息投标测试').first()
        project = Project.query.filter(Project.name == '等额本息投标测试').first()
        for instance in db_session.query(Investment).filter(Investment.project == project).all():
            for plan in db_session.query(Plan).filter(Plan.investment == instance).all():
                db_session.delete(plan)
            db_session.delete(instance)
        for instance in db_session.query(Repayment).filter(Repayment.project == project).all():
            db_session.delete(instance)
        for instance in db_session.query(Log).filter(Log.user == user).all():
            db_session.delete(instance)
        db_session.delete(project)
        db_session.delete(user)
        db_session.commit()

    def test_investment(self):
        user = User.query.filter(User.username == '等额本息投标测试').first()
        project = Project.query.filter(Project.name == '等额本息投标测试').first()
        amount = self.amount
        results = check_invest(amount=amount, user=user, project=project)
        if results.get('message'):
            print(results.get('amount'), results.get('message'))
        else:
            data = tender(user=user, project=project, amount=results.get('amount'), session=db_session())  # 投标
            db_session.commit()
            plans = data.get('plans')
            project = data.get('project')
            self.assertEqual(project.periods, len(plans))

            rv = math.pow(1+(project.rate / 100), project.periods)
            interest = ((data.get('amount')) * (project.rate / 100) * rv / (rv - 1)) * (project.periods) - (data.get('amount'))
            interests = decimalFormat(interest)

            resultsInterest = '0.00'
            for item in plans:
                resultsInterest = decimalFormat(resultsInterest) + decimalFormat(item.interest)
                # print('+++', item.id, '  ', item.interest)
            print('+++等额本息 计算出来的和+++', resultsInterest)
            print('+++++等额本息 公式算出来的++++', interests)
            self.assertEqual(
                resultsInterest.quantize(Decimal('0.01')),
                interests.quantize(Decimal('0.01'))
            )

