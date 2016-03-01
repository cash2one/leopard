from flask import Blueprint
from flask.ext.restful import abort, Resource, marshal
from leopard.core.config import get_config

from leopard.helpers import (authenticate, filtering, get_field,
                             pagination, sorting, get_enum)
from leopard.orm import Post, Banner

config = get_config("leopard.services.auth")

board = Blueprint('board', __name__, url_prefix='/board')


class PostResoure(Resource):
    method_decorators = [authenticate]

    urls = ['/post', '/post/<int:post_id>']
    endpoint = 'post'

    def get(self, post_id=None):
        if post_id:
            post = Post.query.get(post_id)
            if not post or not post.is_active:
                abort(404)
            return marshal(post, get_field('post_detail'))
        posts = pagination(
            filtering(
                sorting(
                    Post.query.filter_by(
                        is_active=True
                    ).order_by('priority desc')
                )
            )
        ).all()
        return marshal(posts, get_field('post_list'))
    get.authenticated = False


class BannerResoure(Resource):
    method_decorators = []

    urls = ['/banners']
    endpoint = 'banners'

    def get(self):
        banners = pagination(
            filtering(
                sorting(
                    Banner.query.filter_by(
                        is_show=True, location=get_enum('BANNER_WECHAT')
                    ).order_by('priority desc', 'id desc')
                )
            )
        ).all()
        return marshal(banners, get_field('banner_list'))


class StudentApplyBannerResoure(Resource):

    method_decorators = []

    urls = ['/banners/student']
    endpoint = 'student_banner'

    def get(self):
        banner = pagination(
            filtering(
                sorting(
                    Banner.query.filter_by(
                        is_show=True,
                        location=get_enum('BANNER_STUDENT_APPLY')
                    ).order_by('priority desc', 'id desc')
                )
            )
        ).first()
        return marshal(banner, get_field('banner_detail'))
