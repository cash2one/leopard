import sqlalchemy

from leopard.core.config import get_config

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.mutable import Mutable
from sqlalchemy.orm import scoped_session, sessionmaker

db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False))

Base = declarative_base()
Base.query = db_session.query_property()


def register_shutdown_handler(app):
    def shutdown_session(exception=None):
        db_session.remove()

    app.teardown_appcontext(shutdown_session)


def create_engine(config_id):
    config = get_config(config_id)

    engine = sqlalchemy.create_engine(config['URI'],
                                      echo=config['ECHO'])

    return engine


def create_engine_with_binding(config_id):
    engine = create_engine(config_id)
    db_session.configure(bind=engine)


def create_all(engine):
    Base.metadata.create_all(bind=engine)


def drop_all(engine):
    Base.metadata.drop_all(bind=engine)


def drop_cascade():
    try:
        for table in Base.metadata.tables:
            execution = 'DROP TABLE "{}" CASCADE'.format(table)
            db_session.execute(execution)
        db_session.commit()
    except sqlalchemy.exc.ProgrammingError as e:
        print(e)


class MutableList(Mutable, list):

    def append(self, value):
        list.append(self, value)
        self.changed()

    @classmethod
    def coerce(cls, key, value):
        if not isinstance(value, MutableList):
            if isinstance(value, list):
                return MutableList(value)
            return Mutable.coerce(key, value)
        else:
            return value
