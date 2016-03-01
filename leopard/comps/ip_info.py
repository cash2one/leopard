import requests


def query(ip):
    resp = requests.get('http://ip.taobao.com/service/getIpInfo.php', params=dict(ip=ip))
    return resp.json()
