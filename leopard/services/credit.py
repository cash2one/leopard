from flask import Blueprint
from flask.ext.restful import abort, Resource, marshal

from leopard.helpers import (authenticate, filtering, get_field, pagination,
                          sorting)
from leopard.orm import Guarantee

credit = Blueprint('credit', __name__, url_prefix='/credit')


class GuaranteeResoure(Resource):
    method_decorators = [authenticate]

    urls = ['/guarantee', '/guarantee/<int:guarantee_id>']
    endpoint = 'guarantee'

    def get(self, guarantee_id=None):
        if guarantee_id:
            guarantee = Guarantee.query.get(guarantee_id)
            if not guarantee:
                abort(404)
            return marshal(guarantee, get_field('guarantee_detail'))
        guarantees = pagination(
            filtering(
                sorting(
                    Guarantee.query.filter_by()
                )
            )
        ).all()
        return marshal(guarantees, get_field('guarantee_list'))
    get.authenticated = False
