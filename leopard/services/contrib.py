from flask import Blueprint
from flask.ext.restful import Resource

from leopard.comps import ip_info
from leopard.helpers import get_parser

contrib = Blueprint('contrib', __name__, url_prefix='/contrib')


class IPInfoResource(Resource):
    method_decorators = []

    urls = ['/ip_info']
    endpoint = 'ip_info'

    def get(self):
        args = get_parser('ip_info').parse_args()
        ip = args['ip']
        rv = ip_info.query(ip)
        return rv
