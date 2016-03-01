import unittest
import requests

s = requests.Session()
host = 'http://127.0.0.1:5000/service'
s.get('http://127.0.0.1:5000/service/credit/guarantee')
_csrf_token = s.cookies.get('_csrf_token')
s.headers.update({'X-CSRFToken': _csrf_token})
user = {'username': 'su', 'password': 'toor'}
s.post(host+'/auth/session', data=user)


class MyTestCase(unittest.TestCase):

    def setUp(self):
        pass

    #def testInvetment(self):
    #    investment = {'amount': 10000}
    #    url = host+'/lending/investment/2'
    #    r = s.post(url, data=investment)
    #    data = json.loads(r.text)
    #    if data.get('message'):
    #        print(data['message'])
    #    else:
    #        self.assertEqual(user.get('username'), data.get('user'))

    def testInvetmentGET(self):
        url = host+'/lending/investment'
        r = s.get(url)
        self.assertEqual(200, r.status_code)

    def testInbox(self):
        url = host+'/social/inbox'
        r = s.get(url)
        self.assertEqual(200, r.status_code)

    def testOutbox(self):
        url = host+'/social/outbox'
        r = s.get(url)
        self.assertEqual(200, r.status_code)

    def testPost(self):
        url = host+'/board/post'
        r = s.get(url)
        self.assertEqual(200, r.status_code)

    def testPublicProject(self):
        url = host+'/lending/public_project'
        r = s.get(url)
        self.assertEqual(200, r.status_code)

    def testProject(self):
        url = host+'/lending/project'
        r = s.get(url)
        self.assertEqual(200, r.status_code)

    def testApplication(self):
        url = host+'/lending/application'
        r = s.get(url)
        self.assertEqual(200, r.status_code)

    def testRepayment(self):
        url = host+'/lending/repayment'
        r = s.get(url)
        self.assertEqual(200, r.status_code)

    def testGuarantee(self):
        url = host+'/credit/guarantee'
        r = s.get(url)
        self.assertEqual(200, r.status_code)