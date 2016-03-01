from bs4 import BeautifulSoup

from leopard.orm import IdCardLog
from leopard.helpers import generate_order_number

def generate_xml(data):
    soup = BeautifulSoup(features='xml')
    soup.append(soup.new_tag('condition'))
    for i in data.keys():
        item = soup.new_tag('item')
        name = soup.new_tag('name')
        name.string = i
        item.append(name)
        value = soup.new_tag('value')
        value.string = data[i]
        item.append(value)
        soup.condition.append(item)
    return soup.decode(eventual_encoding='GBK')


def sign(authentication):
    check_log = IdCardLog()
    check_log.order = generate_order_number()
    check_log.user = authentication.user
    check_log.name = authentication.fields[1].value
    check_log.id_card = authentication.fields[0].value
    data = {
        'name': check_log.name,
        'documentNo': check_log.id_card,
        'subreportIDs': '10602',
        'refID': check_log.order
    }
    return check_log, generate_xml(data)


def checkInternet():
    pass
