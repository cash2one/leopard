from flask.ext.script import Manager
from leopard.core.config import get_config

from leopard.core.orm import create_engine, db_session
from leopard.orm import User

manager = Manager()


@manager.command
def add(username, password, email):
    engine = create_engine('database')
    db_session.configure(bind=engine)

    user = User(username, password, email)

    db_session.add(user)
    db_session.commit()


@manager.command
def delete(id_):
    engine = create_engine('database')
    db_session.configure(bind=engine)

    user = User.query.get(int(id_))
    if user:
        db_session.delete(user)
        db_session.commit()


@manager.command
def list():
    engine = create_engine('database')
    db_session.configure(bind=engine)

    users = User.query.all()
    template = '{:<6}{:<16}{:<24}{:<12}{:<12}'
    print(template.format('ID', 'USERNAME', 'EMAIL', 'IS_ACTIVE', 'IS_SUPER'))
    for user in users:
        print(template.format(
            user.id, user.username, user.email, user.is_active, user.is_super))


@manager.command
def active(id_):
    engine = create_engine('database')
    db_session.configure(bind=engine)

    user = User.query.get(int(id_))
    if user:
        user.is_active = not user.is_active
        print(user.is_active)
        db_session.commit()


@manager.command
def super(id_):
    engine = create_engine('database')
    db_session.configure(bind=engine)

    user = User.query.get(int(id_))
    if user:
        user.is_super = not user.is_super
        print(user.is_super)
        db_session.commit()


@manager.command
def staff(id_):
    engine = create_engine('database')
    db_session.configure(bind=engine)

    user = User.query.get(int(id_))
    if user:
        user.is_staff = not user.is_staff
        print(user.is_staff)
        db_session.commit()


@manager.command
def server(id_):
    engine = create_engine('database')
    db_session.configure(bind=engine)

    user = User.query.get(int(id_))
    if user:
        user.is_server = not user.is_server
        print(user.is_server)
        db_session.commit()


@manager.command
def bane(id_):
    engine = create_engine('database')
    db_session.configure(bind=engine)

    user = User.query.get(int(id_))
    if user:
        user.is_bane = not user.is_bane
        print(user.is_bane)
        db_session.commit()


@manager.command
def defaultpermissions(id_):
    engine = create_engine('database')
    db_session.configure(bind=engine)

    config = get_config('leopard.orm.auth')

    user = User.query.get(int(id_))
    if user:
        user._permissions = config['user_default_permissions']
        print(user._permissions)
        db_session.commit()
