import unittest
from decimal import Decimal
from leopard.core.business import tender, check_invest
from leopard.core.config import get_config
from leopard.core.logging import setup_logging
from leopard.orm import Project, User, RepaymentMethod, Investment, Repayment, Plan, ProjectType, Log
from leopard.core.orm import create_engine_with_binding, db_session
from leopard.orm import UserFactory, ApplicationFactory, ProjectFactory

setup_logging()
enums = get_config('enum')
create_engine_with_binding('database')
repaymethods = '等额本息'
project_type = ProjectType.query.filter(ProjectType.logic == 'flow').first()


def decimalFormat(amount):
    return Decimal(str(amount)).quantize(Decimal('0.01'))


class MyTestCase(unittest.TestCase):

    def setUp(self):
        user = UserFactory(username='投标成功测试', deposit_amount=10000)
        borrower = User.query.filter(User.username == '我是借款人').first()
        repaymethod = RepaymentMethod.query.filter(RepaymentMethod.name == repaymethods).first()
        application = ApplicationFactory(user=borrower, repay_method=repaymethod)
        project = ProjectFactory(
            name='投标成功测试', amount=10000,
            borrowed_amount=1000, application=application, repaymentmethod=repaymethod, type=project_type)
        self.amount = 100.56
        self.expect_amount = 100.56
        self.user_availableAmount = 9899.44
        self.project_borrowedAmount = 1100.56
        db_session.commit()

    def tearDown(self):
        user = User.query.filter(User.username == '投标成功测试').first()
        project = Project.query.filter(Project.name == '投标成功测试').first()
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
        user = User.query.filter(User.username == '投标成功测试').first()
        project = Project.query.filter(Project.name == '投标成功测试').first()
        borrower_user_available_amount = project.user.available_amount
        amount = self.amount

        results = check_invest(amount=amount, user=user, project=project)
        if results.get('message'):
            print(' --MyTestCase: \n\t', results.get('amount'), results.get('message'))
        else:
            self.assertEqual(decimalFormat(self.expect_amount), decimalFormat(results.get('amount')))  # 检查返回的amount
            data = tender(user=user, project=project, amount=results.get('amount'), session=db_session())  # 投标
            db_session.commit()
            db_session.refresh(project)

            plans = data.get('plans')
            self.assertEqual(self.expect_amount, data.get('amount'))  # 返回的amount的比较
            self.assertEqual(decimalFormat(self.user_availableAmount), 
                decimalFormat(data.get('investment').user.available_amount))  # user的available_amount的比较

            self.assertEqual(decimalFormat(self.project_borrowedAmount), decimalFormat(data.get('project').borrowed_amount))  # project的borrowed_amount的比较
            self.assertEqual(decimalFormat(self.expect_amount),
                decimalFormat(data.get('investment').amount))  # investment的amount的比较
            self.assertEqual(decimalFormat(self.expect_amount), 
                decimalFormat(data.get('repayment').amount))  # repayment的amount比较

            borrower_amount = Decimal(borrower_user_available_amount) + Decimal(self.expect_amount)
            self.assertEqual(decimalFormat(borrower_amount), decimalFormat(project.user.available_amount))
            print(' --MyTestCase: ')
            print('\t用户输入amount: ', self.amount, '; 实际操作amount: ', data.get('amount'))
            for item in plans:
                print('\tplan.item_time: ', item.plan_time)


class UserAmountTest(unittest.TestCase):
    # 用户可用资金不足
    def setUp(self):
        user = UserFactory(username='用户可用资金不足', deposit_amount=0)
        borrower = User.query.filter(User.username == '我是借款人').first()
        repaymethod = RepaymentMethod.query.filter(RepaymentMethod.name == repaymethods).first()
        application = ApplicationFactory(user=borrower, repay_method=repaymethod)
        project = ProjectFactory(name='用户可用资金不足', amount=10000,
                                 borrowed_amount=1000, application=application, repaymentmethod=repaymethod, type=project_type)
        self.amount = 1000
        self.expect_amount = 1000
        db_session.commit()

    def test_investment(self):
        user = User.query.filter(User.username == '用户可用资金不足').first()
        project = Project.query.filter(Project.name == '用户可用资金不足').first()
        amount = self.amount
        results = check_invest(amount=amount, user=user, project=project)
        if results.get('message'):
            self.assertEqual(decimalFormat(self.expect_amount), decimalFormat(results.get('amount')))  # check_invest的amount返回
            print(' --UserAmountTest: \n\t', results.get('amount'), results.get('message'))
        else:
            data = tender(user=user, project=project, amount=results.get('amount'))  # 投标
            db_session.commit()
            project = data.get('project')
            print(' --UserAmountTest: ')
            print('\tproject:', project)

    def tearDown(self):
        user = User.query.filter(User.username == '用户可用资金不足').first()
        project = Project.query.filter(Project.name == '用户可用资金不足').first()
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


class InvestAmountMoreThanTest(unittest.TestCase):
    # 投标金额大于标金额
    def setUp(self):
        user = UserFactory(username='投标金额大于标金额', deposit_amount=100000)
        borrower = User.query.filter(User.username == '我是借款人').first()
        repaymethod = RepaymentMethod.query.filter(RepaymentMethod.name == repaymethods).first()
        application = ApplicationFactory(user=borrower, repay_method=repaymethod)
        project = ProjectFactory(name='投标金额大于标金额', amount=10000,
                                 borrowed_amount=1000, application=application, repaymentmethod=repaymethod, type=project_type)
        self.amount = 20000
        self.expect_amount = 9000
        self.user_availableAmount = 91000
        self.project_borrowedAmount = 10000
        db_session.commit()

    def test_investment(self):
        user = User.query.filter(User.username == '投标金额大于标金额').first()
        project = Project.query.filter(Project.name == '投标金额大于标金额').first()
        borrower_user_available_amount = project.user.available_amount
        amount = self.amount
        results = check_invest(amount=amount, user=user, project=project)
        if results.get('message'):
            print(' --InvestAmountMoreThanTest: \n\t', results.get('amount'), results.get('message'))
        else:
            self.assertEqual(self.expect_amount, results.get('amount'))
            data = tender(user=user, project=project, amount=results.get('amount'), session=db_session())
            db_session.commit()
            db_session.refresh(project)

            self.assertEqual(self.expect_amount, data.get('amount'))  # 返回的amount的比较
            self.assertEqual(decimalFormat(self.user_availableAmount), 
                decimalFormat(data.get('investment').user.available_amount))  # user的available_amount的比较
            self.assertEqual(decimalFormat(self.project_borrowedAmount),
                decimalFormat(data.get('project').borrowed_amount))  # project的borrowed_amount的比较
            self.assertEqual(decimalFormat(self.expect_amount),
                decimalFormat(data.get('investment').amount))  # investment的amount的比较
            self.assertEqual(decimalFormat(self.expect_amount), 
                decimalFormat(data.get('repayment').amount))  # repayment的amount比较

            borrower_amount = Decimal(borrower_user_available_amount) + Decimal(self.expect_amount)
            self.assertEqual(decimalFormat(borrower_amount), decimalFormat(project.user.available_amount))
            print(' --InvestAmountMoreThanTest:')
            project = data.get('project')
            print('\tproject:', project)

    def tearDown(self):
        user = User.query.filter(User.username == '投标金额大于标金额').first()
        project = Project.query.filter(Project.name == '投标金额大于标金额').first()
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


class InvestAmountLessThanTest(unittest.TestCase):
    # 投标金额小于最小投标金额
    def setUp(self):
        user = UserFactory(username='投标金额小于最小投标金额', deposit_amount=100000)
        borrower = User.query.filter(User.username == '我是借款人').first()
        repaymethod = RepaymentMethod.query.filter(RepaymentMethod.name == repaymethods).first()
        application = ApplicationFactory(user=borrower, repay_method=repaymethod)
        project = ProjectFactory(name='投标金额小于最小投标金额', amount=10000,
                                 borrowed_amount=1000, application=application, repaymentmethod=repaymethod, type=project_type)
        self.amount = 10
        self.expect_amount = 10
        db_session.commit()

    def test_investment(self):
        user = User.query.filter(User.username == '投标金额小于最小投标金额').first()
        project = Project.query.filter(Project.name == '投标金额小于最小投标金额').first()
        amount = self.amount
        results = check_invest(amount=amount, user=user, project=project)
        if results.get('message'):
            self.assertEqual(decimalFormat(self.expect_amount), decimalFormat(results.get('amount')))   # check_invest的amount返回
            print(' --InvestAmountLessThanTest: \n\t', results.get('amount'), results.get('message'))
        else:
            data = tender(user=user, project=project, amount=results.get('amount'))
            db_session.commit()
            project = data.get('project')
            print(' --InvestAmountLessThanTest: \n\t用户输入amount: ', self.amount, '; 实际操作amount: ', data.get('amount'), '\n\tproject:', project)

    def tearDown(self):
        user = User.query.filter(User.username == '投标金额小于最小投标金额').first()
        project = Project.query.filter(Project.name == '投标金额小于最小投标金额').first()
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


class InvestAmountFormatTest(unittest.TestCase):
    #投标金额格式错误
    def setUp(self):
        user = UserFactory(username='投标金额格式错误', deposit_amount=100000)
        borrower = User.query.filter(User.username == '我是借款人').first()
        repaymethod = RepaymentMethod.query.filter(RepaymentMethod.name == repaymethods).first()
        application = ApplicationFactory(user=borrower, repay_method=repaymethod)
        project = ProjectFactory(name='投标金额格式错误', amount=10000,
                                 borrowed_amount=1000, application=application, repaymentmethod=repaymethod, type=project_type)
        # self.amount = -10000 #负数
        self.amount = 'abcs'  # string
        self.expect_amount = 'abcs'
        db_session.commit()

    def test_investment(self):
        user = User.query.filter(User.username == '投标金额格式错误').first()
        project = Project.query.filter(Project.name == '投标金额格式错误').first()
        amount = self.amount
        results = check_invest(amount=amount, user=user, project=project)
        if results.get('message'):
            self.assertEqual(self.expect_amount, results.get('amount'))  # check_invest的amount返回
            print(' --InvestAmountFormatTest: \n\t', results.get('amount'), results.get('message'))
        else:
            data = tender(user=user, project=project, amount=results.get('amount'))
            db_session.commit()
            project = data.get('project')
            print(' --InvestAmountFormatTest: \n\t用户输入amount: ', self.amount, '; 实际操作amount: ', data.get('amount'), '\n\tproject:', project)

    def tearDown(self):
        user = User.query.filter(User.username == '投标金额格式错误').first()
        project = Project.query.filter(Project.name == '投标金额格式错误').first()
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


class ProjectFullTest(unittest.TestCase):
    #标已经满
    def setUp(self):
        user = UserFactory(username='标已经满', deposit_amount=100000)
        borrower = User.query.filter(User.username == '我是借款人').first()
        repaymethod = RepaymentMethod.query.filter(RepaymentMethod.name == repaymethods).first()
        application = ApplicationFactory(user=borrower, repay_method=repaymethod)
        project = ProjectFactory(name='标已经满', amount=10000,
                                 borrowed_amount=10000, application=application, repaymentmethod=repaymethod, type=project_type)
        db_session.commit()

    def test_investment_Usual(self):
        user = User.query.filter(User.username == '标已经满').first()
        project = Project.query.filter(Project.name == '标已经满').first()
        amount = 1000
        expect_amount = 1000
        results = check_invest(amount=amount, user=user, project=project)
        if results.get('message'):
            self.assertEqual(decimalFormat(expect_amount), decimalFormat(results.get('amount')))  # check_invest的amount返回
            print(' --ProjectFullTest(Usual): \n\t', results.get('amount'), results.get('message'))
        else:
            data = tender(user=user, project=project, amount=results.get('amount'), session=db_session())
            db_session.commit()
            project = data.get('project')
            print(' --ProjectFullTest(Usual): \n\tproject:', project)

    def test_investment_Format(self):
        user = User.query.filter(User.username == '标已经满').first()
        project = Project.query.filter(Project.name == '标已经满').first()
        amount = -1000
        expect_amount = -1000
        results = check_invest(amount=amount, user=user, project=project)
        if results.get('message'):
            self.assertEqual(expect_amount, results.get('amount'))  # check_invest的amount返回
            print(' --ProjectFullTest(Format): \n\t', results.get('amount'), results.get('message'))
        else:
            data = tender(user=user, project=project, amount=results.get('amount'))
            db_session.commit()
            project = data.get('project')
            print(' --ProjectFullTest(Format): \n\tproject:', project)

    def test_investment_LessThan(self):
        user = User.query.filter(User.username == '标已经满').first()
        project = Project.query.filter(Project.name == '标已经满').first()
        amount = 10
        expect_amount = 10
        results = check_invest(amount=amount, user=user, project=project)
        if results.get('message'):
            self.assertEqual(expect_amount, results.get('amount'))  # check_invest的amount返回
            print(' --ProjectFullTest(LessThan): \n\t', results.get('amount'), results.get('message'))
        else:
            data = tender(user=user, project=project, amount=results.get('amount'), session=db_session())
            db_session.commit()
            project = data.get('project')
            print(' --ProjectFullTest(LessThan): \n\tproject:', project)

    def test_investment_MoreThan(self):
        user = User.query.filter(User.username == '标已经满').first()
        project = Project.query.filter(Project.name == '标已经满').first()
        amount = 100000
        expect_amount = 100000
        results = check_invest(amount=amount, user=user, project=project)
        if results.get('message'):
            self.assertEqual(expect_amount, results.get('amount'))  # check_invest的amount返回
            print(' --ProjectFullTest(MoreThan): \n\t', results.get('amount'), results.get('message'))
        else:
            data = tender(user=user, project=project, amount=results.get('amount'), session=db_session())
            db_session.commit()
            project = data.get('project')
            print(' --ProjectFullTest(MoreThan): \n\tproject:', project)

    def test_investment_AvailableLess(self):
        user = User.query.filter(User.username == '标已经满').first()
        project = Project.query.filter(Project.name == '标已经满').first()
        amount = 200000
        expect_amount = 200000
        results = check_invest(amount=amount, user=user, project=project)
        if results.get('message'):
            self.assertEqual(expect_amount, results.get('amount'))  # check_invest的amount返回
            print(' --ProjectFullTest(AvailableLess): \n\t', results.get('amount'), results.get('message'))
        else:
            data = tender(user=user, project=project, amount=results.get('amount'), session=db_session())
            db_session.commit()
            project = data.get('project')
            print(' --ProjectFullTest(AvailableLess): \n\tproject:', project)

    def tearDown(self):
        user = User.query.filter(User.username == '标已经满').first()
        project = Project.query.filter(Project.name == '标已经满').first()
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


#标未满 但剩余金额小于投资资金
class projectSurplusAmountLessThanUsualTest(unittest.TestCase):
    #标未满 但剩余金额小于投资资金 正常
    def setUp(self):
        user = UserFactory(username='剩余金额小于投资资金', deposit_amount=100000)
        borrower = User.query.filter(User.username == '我是借款人').first()
        repaymethod = RepaymentMethod.query.filter(RepaymentMethod.name == repaymethods).first()
        application = ApplicationFactory(user=borrower, repay_method=repaymethod)
        project = ProjectFactory(name='剩余金额小于投资资金', amount=10000,
                                 borrowed_amount=9990, application=application, repaymentmethod=repaymethod, type=project_type)
        self.amount = 1000
        self.expect_amount = 10
        self.user_availableAmount = 99990
        self.project_borrowedAmount = 10000
        db_session.commit()

    def test_investment(self):
        user = User.query.filter(User.username == '剩余金额小于投资资金').first()
        project = Project.query.filter(Project.name == '剩余金额小于投资资金').first()
        borrower_user_available_amount = project.user.available_amount
        amount = self.amount
        results = check_invest(amount=amount, user=user, project=project)
        if results.get('message'):
            print(' --projectSurplusAmountLessThanTest(Usual): \n\t', results.get('amount'), results.get('message'))
        else:
            self.assertEqual(decimalFormat(self.expect_amount), decimalFormat(results.get('amount')))
            data = tender(user=user, project=project, amount=results.get('amount'), session=db_session())
            db_session.commit()
            db_session.refresh(project)

            self.assertEqual(decimalFormat(self.expect_amount), decimalFormat(data.get('amount')))  # 返回的amount的比较
            self.assertEqual(decimalFormat(self.user_availableAmount), 
                decimalFormat(data.get('investment').user.available_amount))  # user的available_amount的比较
            self.assertEqual(decimalFormat(self.project_borrowedAmount),
                decimalFormat(data.get('project').borrowed_amount))  # project的borrowed_amount的比较
            self.assertEqual(decimalFormat(self.expect_amount),
                decimalFormat(data.get('investment').amount))  # investment的amount的比较
            self.assertEqual(decimalFormat(self.expect_amount), 
                decimalFormat(data.get('repayment').amount))  # repayment的amount比较
            borrower_amount = Decimal(borrower_user_available_amount) + Decimal(self.expect_amount)
            self.assertEqual(decimalFormat(borrower_amount), decimalFormat(project.user.available_amount))
            print(' --projectSurplusAmountLessThanTest(Usual): \n\t输入的amount:', self.amount, '; 实际运行的amount: ', data.get('amount'))
            project = data.get('project')
            print('\tproject:', project)

    def tearDown(self):
        user = User.query.filter(User.username == '剩余金额小于投资资金').first()
        project = Project.query.filter(Project.name == '剩余金额小于投资资金').first()
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


class projectSurplusAmountLessThanAvailableLessTest(unittest.TestCase):
    #标未满 但剩余金额小于投资资金 余额不足
    def setUp(self):
        user = UserFactory(username='剩余金额小于投资资金', deposit_amount=5)
        borrower = User.query.filter(User.username == '我是借款人').first()
        repaymethod = RepaymentMethod.query.filter(RepaymentMethod.name == repaymethods).first()
        application = ApplicationFactory(user=borrower, repay_method=repaymethod)
        project = ProjectFactory(name='剩余金额小于投资资金', amount=10000,
                                 borrowed_amount=9990, application=application, repaymentmethod=repaymethod, type=project_type)
        self.amount = 1000
        self.expect_amount = 1000
        db_session.commit()

    def test_investment(self):
        user = User.query.filter(User.username == '剩余金额小于投资资金').first()
        project = Project.query.filter(Project.name == '剩余金额小于投资资金').first()
        amount = self.amount
        results = check_invest(amount=amount, user=user, project=project)
        if results.get('message'):
            self.assertEqual(self.expect_amount, results.get('amount'))  # check_invest的amount返回
            print(' --projectSurplusAmountLessThanTest(AvailableLess): \n\t', results.get('amount'), results.get('message'))
        else:
            data = tender(user=user, project=project, amount=results.get('amount'), session=db_session())
            db_session.commit()
            print(' --projectSurplusAmountLessThanTest(AvailableLess): \n\t输入的amount:', self.amount, '; 实际运行的amount: ', data.get('amount'))
            project = data.get('project')
            print('\tproject:', project)

    def tearDown(self):
        user = User.query.filter(User.username == '剩余金额小于投资资金').first()
        project = Project.query.filter(Project.name == '剩余金额小于投资资金').first()
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


class projectSurplusAmountLessThanMoreThanTest(unittest.TestCase):
    #标未满 但剩余金额小于投资资金 投资金额大于最大投资金额
    def setUp(self):
        user = UserFactory(username='剩余金额小于投资资金', deposit_amount=100000)
        borrower = User.query.filter(User.username == '我是借款人').first()
        repaymethod = RepaymentMethod.query.filter(RepaymentMethod.name == repaymethods).first()
        application = ApplicationFactory(user=borrower, repay_method=repaymethod)
        project = ProjectFactory(name='剩余金额小于投资资金', amount=10000,
                                 borrowed_amount=9990, application=application, repaymentmethod=repaymethod, type=project_type)
        self.amount = 100000
        self.expect_amount = 10
        self.user_availableAmount = 99990
        self.project_borrowedAmount = 10000
        db_session.commit()

    def test_investment(self):
        user = User.query.filter(User.username == '剩余金额小于投资资金').first()
        project = Project.query.filter(Project.name == '剩余金额小于投资资金').first()
        borrower_user_available_amount = project.user.available_amount
        amount = self.amount
        results = check_invest(amount=amount, user=user, project=project)
        if results.get('message'):
            print(' --projectSurplusAmountLessThanTest(MoreThan): \n\t', results.get('amount'), results.get('message'))
        else:
            self.assertEqual(decimalFormat(self.expect_amount), decimalFormat(results.get('amount')))
            data = tender(user=user, project=project, amount=results.get('amount'), session=db_session())
            db_session.commit()
            db_session.refresh(project)

            self.assertEqual(decimalFormat(self.expect_amount), decimalFormat(data.get('amount')))  # 返回的amount的比较
            self.assertEqual(decimalFormat(self.user_availableAmount), 
                decimalFormat(data.get('investment').user.available_amount))  # user的available_amount的比较
            self.assertEqual(decimalFormat(self.project_borrowedAmount),
                decimalFormat(data.get('project').borrowed_amount))  # project的borrowed_amount的比较
            self.assertEqual(decimalFormat(self.expect_amount),
                decimalFormat(data.get('investment').amount)) # investment的amount的比较
            self.assertEqual(decimalFormat(self.expect_amount), 
                decimalFormat(data.get('repayment').amount))  # repayment的amount比较
            borrower_amount = Decimal(borrower_user_available_amount) + Decimal(self.expect_amount)
            self.assertEqual(decimalFormat(borrower_amount), decimalFormat(project.user.available_amount))
            print(' --projectSurplusAmountLessThanTest(MoreThan): ')
            project = data.get('project')
            print('\tproject:', project)

    def tearDown(self):
        user = User.query.filter(User.username == '剩余金额小于投资资金').first()
        project = Project.query.filter(Project.name == '剩余金额小于投资资金').first()
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


class projectSurplusAmountLessThanLessThanTest(unittest.TestCase):
    #标未满 但剩余金额小于投资资金 投资金额小于最小投资金额且小于剩余金额
    def setUp(self):
        user = UserFactory(username='剩余金额小于投资资金', deposit_amount=1000)
        borrower = User.query.filter(User.username == '我是借款人').first()
        repaymethod = RepaymentMethod.query.filter(RepaymentMethod.name == repaymethods).first()
        application = ApplicationFactory(user=borrower, repay_method=repaymethod)
        project = ProjectFactory(name='剩余金额小于投资资金', amount=10000,
                                 borrowed_amount=9990, application=application, repaymentmethod=repaymethod, type=project_type)
        self.amount = 5
        self.expect_amount = 5
        db_session.commit()

    def test_investment(self):
        user = User.query.filter(User.username == '剩余金额小于投资资金').first()
        project = Project.query.filter(Project.name == '剩余金额小于投资资金').first()
        amount = self.amount
        results = check_invest(amount=amount, user=user, project=project)
        if results.get('message'):
            self.assertEqual(self.expect_amount, results.get('amount'))  # check_invest的amount返回
            print(' --projectSurplusAmountLessThanTest(LessThan): \n\t', results.get('amount'), results.get('message'))
        else:
            data = tender(user=user, project=project, amount=results.get('amount'), session=db_session())
            db_session.commit()
            print(' --projectSurplusAmountLessThanTest(LessThan): \n\t输入的amount:', self.amount, '; 实际运行的amount: ', data.get('amount'))
            project = data.get('project')
            print('\tproject:', project)

    def tearDown(self):
        user = User.query.filter(User.username == '剩余金额小于投资资金').first()
        project = Project.query.filter(Project.name == '剩余金额小于投资资金').first()
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


class projectSurplusAmountLessThanLessThanMoreThanAmountLessTest(unittest.TestCase):
    #标未满 但剩余金额小于投资资金 投资金额小于最小投资金额但大于剩余金额
    def setUp(self):
        user = UserFactory(username='剩余金额小于投资资金', deposit_amount=1000)
        borrower = User.query.filter(User.username == '我是借款人').first()
        repaymethod = RepaymentMethod.query.filter(RepaymentMethod.name == repaymethods).first()
        application = ApplicationFactory(user=borrower, repay_method=repaymethod)
        project = ProjectFactory(name='剩余金额小于投资资金', amount=10000,
                                 borrowed_amount=9990, application=application, repaymentmethod=repaymethod, type=project_type)
        self.amount = 20
        self.expect_amount = 10
        self.user_availableAmount = 990
        self.project_borrowedAmount = 10000
        db_session.commit()

    def test_investment(self):
        user = User.query.filter(User.username == '剩余金额小于投资资金').first()
        project = Project.query.filter(Project.name == '剩余金额小于投资资金').first()
        borrower_user_available_amount = project.user.available_amount
        amount = self.amount
        results = check_invest(amount=amount, user=user, project=project)
        if results.get('message'):
            print(' --projectSurplusAmountLessThanTest(LessThanMoreThanAmountLess): \n\t', results.get('amount'), results.get('message'))
        else:
            data = tender(user=user, project=project, amount=results.get('amount'), session=db_session())
            db_session.commit()
            db_session.refresh(project)

            self.assertEqual(self.expect_amount, data.get('amount'))  # 返回的amount的比较
            self.assertEqual(decimalFormat(self.user_availableAmount), 
                decimalFormat(data.get('investment').user.available_amount))  # user的available_amount的比较
            self.assertEqual(decimalFormat(self.project_borrowedAmount),
                decimalFormat(data.get('project').borrowed_amount))  # project的borrowed_amount的比较
            self.assertEqual(decimalFormat(self.expect_amount),
                decimalFormat(data.get('investment').amount))  # investment的amount的比较
            self.assertEqual(decimalFormat(self.expect_amount), 
                decimalFormat(data.get('repayment').amount))  # repayment的amount比较
            borrower_amount = Decimal(borrower_user_available_amount) + Decimal(self.expect_amount)
            self.assertEqual(decimalFormat(borrower_amount), decimalFormat(project.user.available_amount))
            print(' --projectSurplusAmountLessThanTest(LessThanMoreThanAmountLess):')
            project = data.get('project')
            print('\tproject:', project)

    def tearDown(self):
        user = User.query.filter(User.username == '剩余金额小于投资资金').first()
        project = Project.query.filter(Project.name == '剩余金额小于投资资金').first()
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