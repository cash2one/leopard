import sqlalchemy
from flask import Blueprint
from flask.ext.restful import abort, marshal_with, Resource

from leopard.core.orm import db_session
from leopard.helpers import (assert_current_user, authenticate, filtering,
                          get_current_user, get_field, get_parser, pagination,
                          sorting)
from leopard.orm import Message, User

social = Blueprint('social', __name__, url_prefix='/social')


class InboxResource(Resource):
    method_decorators = [authenticate]

    urls = ['/inbox', '/inbox/<int:message_id>']
    endpoint = 'inbox'

    @marshal_with(get_field('message'))
    def get(self, message_id=None):
        if message_id:
            message = Message.query.filter(Message.id == message_id, Message.to_user_show == True).first()
            assert_current_user(message, 'to_user')
            return message
        user = get_current_user()
        messages = pagination(
            filtering(
                sorting(
                    Message.query.filter_by(to_user=user, to_user_show=True)
                )
            )
        ).all()
        return messages

    @marshal_with(get_field('message'))
    def put(self, message_id):
        message = Message.query.filter(Message.id == message_id, Message.to_user_show == True).first()
        assert_current_user(message, 'to_user')
        message.is_read = True
        db_session.commit()
        return message

    def delete(self, message_id=None):
        user = get_current_user()
        if message_id:
            message = Message.query.filter(Message.id == message_id, Message.to_user_show == True).first()
            assert_current_user(message, 'to_user')
            message.to_user_show = False
            db_session.commit()
            return dict(message='删除成功')
        for i in user.inbox:
            if i.to_user_show:
                i.to_user_show = False
        db_session.commit()
        return dict(message='删除成功')
