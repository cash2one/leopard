from .ip_info import query as query_ip

_handlers = []


def strange_land_handler(func):
    _handlers.append(func)
    return func


def inpsect(last_login_ip, current_login_ip):
    last_ip = last_login_ip
    current_ip = current_login_ip
    if not last_ip or not current_ip:
        return
    last_ip_rv = query_ip(last_ip)
    current_ip_rv = query_ip(current_ip)
    last_pc_tuple = (last_ip_rv['data']['region_id'], last_ip_rv['data']['city_id'])
    current_pc_tuple = (current_ip_rv['data']['region_id'], current_ip_rv['data']['city_id'])
    if last_pc_tuple == current_pc_tuple:
        return
    for handler in _handlers:
        handler()
