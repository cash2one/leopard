#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os

from flask import Flask
from flask.ext.script import Command, Manager, Option
from flask.ext.migrate import Migrate, MigrateCommand
from flask.ext.sqlalchemy import SQLAlchemy

from scripts.angular import manager as angular_manager
from scripts.database import manager as database_manager
from scripts.user import manager as user_manager

from leopard.core.orm import Base
from leopard.core.config import get_config

app = Flask(__name__, instance_path=os.path.dirname(os.path.abspath(__file__)))

app.config['SQLALCHEMY_DATABASE_URI'] = get_config('database')['URI']
manager = Manager(app)

db = SQLAlchemy(app)
db.Model = Base
migrate = Migrate(app, db)

manager.add_command('db', database_manager)
manager.add_command('ng', angular_manager)
manager.add_command('user', user_manager)
manager.add_command('dba', MigrateCommand)


@manager.shell
def make_shell_context():
    from leopard.core.orm import Base, create_engine_with_binding, db_session

    create_engine_with_binding('database')
    return dict(db_session=db_session, **Base._decl_class_registry)


class Server(Command):

    option_list = (
        Option('--host', '-H', dest='host', default='127.0.0.1'),
        Option('--port', '-p', dest='port', default=5001),
    )

    def run(self, host, port):
        from werkzeug.serving import run_simple
        from leopard.core.wsgi import create_wsgi

        app = create_wsgi()
        run_simple(host, port, app, use_reloader=True, use_debugger=True,
                   use_evalex=True)


class Generate(Command):

    def run(self):
        from leopard.core.orm import create_engine, db_session
        from leopard.helpers.utils import (generate_custom_config,
                                           generate_index_html,
                                           build_front)
        engine = create_engine('database')
        db_session.configure(bind=engine)
        generate_index_html()
        generate_custom_config()
        build_front()


manager.add_command('runserver', Server())
manager.add_command('generate', Generate())

if __name__ == '__main__':
    manager.run()
