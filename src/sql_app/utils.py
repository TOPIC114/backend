from sql_app import Base
import logging


def create_tables(engine):
    Base.metadata.create_all(engine)


def drop_tables(engine):
    Base.metadata.drop_all(bind=engine)


db_logger = logging.getLogger('db')
