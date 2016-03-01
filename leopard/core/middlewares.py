import simplejson as json

from flask import request

from leopard.helpers.utils import get_config

project_config = get_config('project')


def china_mobile_filter(response):
    platfrom = request.headers.get('Platform')

    if platfrom in project_config['BEARER_TOKEN_PLATFORM']:
        if response.content_type == 'application/json':
            data = {}
            data['results'] = json.loads(response.get_data())
            data['code'] = response.status_code
            if response.status_code >= 400:
                response.status_code = 200
            response.set_data(json.dumps(data))
    return response


register_middlewares = [china_mobile_filter]
