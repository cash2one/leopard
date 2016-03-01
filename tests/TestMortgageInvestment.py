#import unittest
#from decimal import Decimal
#from leopard.core.business import tender, check_invest
#from leopard.core.config import get_config
#from leopard.core.logging import setup_logging
#from leopard.orm import Project, User, RepaymentMethod, Investment, Repayment, Plan, ProjectType, Config, Log
#from leopard.core.orm import create_engine_with_binding, db_session
#from leopard.orm import UserFactory, ApplicationFactory, ProjectFactory
#
#setup_logging()
#enums = get_config('enum')
#create_engine_with_binding('database')
#repaymethods = '等额本息'
#project_type = ProjectType.query.filter(ProjectType.logic == 'flow').first()
#
#
#def decimalFormat(amount):
#    return Decimal(str(amount)).quantize(Decimal('0.01'))
#
#
## 服务费
#def service_fee(project):
#    survery_fee = Config.get_config('COMMISSION_INVEST_BORROWER_FIXED')
#    survery_fee = Decimal(str(survery_fee))
#
#    service_charge_rate = Config.get_config('COMMISSION_INVEST_BORROWER_RATE') / 100
#    shortfall = project.periods - Config.get_config('COMMISSION_INVEST_STEP_START')
#    step_rate = Config.get_config('COMMISSION_INVEST_STEP_RATE') / 100
#    if shortfall > 0:
#        service_charge_rate += shortfall * step_rate
#    service_fee = project.amount * Decimal(str(service_charge_rate))
#
#    return survery_fee + service_fee
#
#
## 抵押标 投标 之后标未满
#class MyTestCase(unittest.TestCase):
#
#    def setUp(self):
#        user = UserFactory(username='投标成功测试', deposit_amount=10000)
#        borrower = User.query.filter(User.username == '我是借款人').first()
#        repaymethod = RepaymentMethod.query.filter(RepaymentMethod.name == repaymethods).first()
#        application = ApplicationFactory(user=borrower, repay_method=repaymethod)
#        project = ProjectFactory(
#            name='投标成功测试', amount=10000,
#            borrowed_amount=1000, application=application, repaymentmethod=repaymethod, type=project_type)
#        self.amount = 100.56
#        self.expect_amount = 100.56
#        self.user_available_amount = 9899.44
#        self.project_borrowed_amount = 1100.56
#        db_session.commit()
#
#    def tearDown(self):
#        user = User.query.filter(User.username == '投标成功测试').first()
#        for instance in db_session.query(Log).filter(Log.user == user).all():
#            db_session.delete(instance)  # 资金记录
#        project = Project.query.filter(Project.name == '投标成功测试').first()
#        for instance in db_session.query(Investment).filter(Investment.project == project).all():
#            for plan in db_session.query(Plan).filter(Plan.investment == instance).all():
#                db_session.delete(plan)
#            db_session.delete(instance)
#        for instance in db_session.query(Repayment).filter(Repayment.project == project).all():
#            db_session.delete(instance)
#        for instance in db_session.query(Log).filter(Log.user == user).all():
#            db_session.delete(instance)
#
#        db_session.delete(project)
#        db_session.delete(user)
#        db_session.commit()
#
#    def test_investment(self):
#        user = User.query.filter(User.username == '投标成功测试').first()
#        user_blocked_amount = user.blocked_amount
#        project = Project.query.filter(Project.name == '投标成功测试').first()
#        borrower_user_available_amount = project.user.available_amount
#
#        amount = self.amount
#
#        results = check_invest(amount=amount, user=user, project=project)
#        if results.get('message'):
#            print(' --MyTestCase: \n\t', results.get('amount'), results.get('message'))
#        else:
#            self.assertEqual(decimalFormat(self.expect_amount), decimalFormat(results.get('amount')))  # 检查返回的amount
#            data = tender(user=user, project=project, amount=results.get('amount'), session=db_session())  # 投标
#            db_session.commit()
#            db_session.refresh(project)
#
#            plans = data.get('plans')
#            self.assertEqual(0, len(plans))  #抵押标中 plans的长度比较
#
#            self.assertEqual(decimalFormat(self.expect_amount), decimalFormat(data.get('amount')))  # 返回的amount的比较
#
#            self.assertEqual(decimalFormat(self.user_available_amount),
#                decimalFormat(data.get('investment').user.available_amount))  # user的available_amount的比较
#            user_blocked_amount = Decimal(user_blocked_amount) + Decimal(self.expect_amount)
#            self.assertEqual(decimalFormat(user_blocked_amount), decimalFormat(data.get('investment').user.blocked_amount))  # 抵押标中user的blocked_amount的比较
#
#            self.assertEqual(decimalFormat(self.project_borrowed_amount),
#                             decimalFormat(data.get('project').borrowed_amount))  # project的borrowed_amount的比较
#
#            borrower_available_amount = Decimal(borrower_user_available_amount) + Decimal(self.expect_amount)
#            self.assertNotEqual(decimalFormat(borrower_available_amount), decimalFormat(project.user.available_amount))  # 借款人的available_amount 的比较
#
#            self.assertEqual(decimalFormat(self.expect_amount),
#                decimalFormat(data.get('investment').amount))  # investment的amount的比较
#            self.assertEqual(decimalFormat(self.expect_amount),
#                decimalFormat(data.get('repayment').amount))  # repayment的amount比较
#
#            print(' --MyTestCase: ')
#            print('\t用户输入amount: ', self.amount, '; 实际操作amount: ', data.get('amount'))
#
#
## # 抵押标 投标 之后满标
## class ProjectFullTest(unittest.TestCase):
#
##     def setUp(self):
##         user = UserFactory(username='投标测试', available_amount=10000)
##         borrower = User.query.filter(User.username == '我是借款人').first()
##         repaymethod = RepaymentMethod.query.filter(RepaymentMethod.name == repaymethods).first()
##         application = ApplicationFactory(user=borrower, repay_method=repaymethod)
##         project = ProjectFactory(
##             name='投标测试', amount=10000,
##             borrowed_amount=9899.44, application=application, repaymentmethod=repaymethod, type=project_type)
##         self.amount = 100.56
##         self.expect_amount = 100.56
##         self.user_available_amount = 9899.44
##         self.project_borrowed_amount = 10000
##         db_session.commit()
#
##     def tearDown(self):
##         user = User.query.filter(User.username == '投标测试').first()
##         for instance in db_session.query(Log).filter(Log.user == user).all():
##             db_session.delete(instance)  # 资金记录
##         project = Project.query.filter(Project.name == '投标测试').first()
##         for instance in db_session.query(Investment).filter(Investment.project == project).all():
##             for plan in db_session.query(Plan).filter(Plan.investment == instance).all():
##                 db_session.delete(plan)
##             db_session.delete(instance)
##         for instance in db_session.query(Repayment).filter(Repayment.project == project).all():
##             db_session.delete(instance)
##         for instance in db_session.query(Log).filter(Log.user == user).all():
##             db_session.delete(instance)
##         db_session.delete(project)
##         db_session.delete(user)
##         db_session.commit()
#
##     def test_investment(self):
##         user = User.query.filter(User.username == '投标测试').first()
##         user_blocked_amount = user.blocked_amount
##         project = Project.query.filter(Project.name == '投标测试').first()
##         borrower_user_available_amount = project.user.available_amount
#
##         amount = self.amount
#
##         results = check_invest(amount=amount, user=user, project=project)
##         if results.get('message'):
##             print(' --ProjectFullTest: \n\t', results.get('amount'), results.get('message'))
##         else:
##             self.assertEqual(decimalFormat(self.expect_amount), decimalFormat(results.get('amount')))  # 检查返回的amount
##             data = tender(user=user, project=project, amount=results.get('amount'))  # 投标
##             db_session.commit()
##             db_session.refresh(project)
#
##             self.assertEqual(decimalFormat(self.expect_amount), decimalFormat(data.get('amount')))  # 返回的amount的比较
#
##             self.assertEqual(decimalFormat(self.user_available_amount),
##                 decimalFormat(data.get('investment').user.available_amount))  # user的available_amount的比较
##             user_blocked_amount = Decimal(user_blocked_amount) + Decimal(self.expect_amount)
##             self.assertNotEqual(decimalFormat(user_blocked_amount), decimalFormat(data.get('investment').user.blocked_amount))  # 抵押标中user的blocked_amount的比较
#
##             self.assertEqual(decimalFormat(self.project_borrowed_amount),
##                 decimalFormat(data.get('project').borrowed_amount))  # project的borrowed_amount的比较
#
##             self.assertEqual(decimalFormat(self.expect_amount),
##                 decimalFormat(data.get('investment').amount)) # investment的amount的比较
##             self.assertEqual(decimalFormat(self.expect_amount),
##                 decimalFormat(data.get('repayment').amount))  # repayment的amount比较
#
##             service_fees = service_fee(project)
##             borrower_amount = Decimal(borrower_user_available_amount) + Decimal(project.amount) - Decimal(service_fees)
##             self.assertEqual(decimalFormat(borrower_amount), decimalFormat(project.user.available_amount)) # 借款人的available_amount比较
##             expect_length = int(project.periods) * int(len(project.investments))
##             plans = data.get('plans')
##             self.assertEqual(expect_length, len(plans))