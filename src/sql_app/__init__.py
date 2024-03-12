import os

from sqlalchemy.ext.declarative import declarative_base

database_uri = os.environ.get('DATABASE_URI') is None and 'sqlite+aiosqlite:///./sql_app.sqlite' or os.environ.get('DATABASE_URI')

Base = declarative_base()

__all__ = ['Base', 'utils', 'database_uri',]
