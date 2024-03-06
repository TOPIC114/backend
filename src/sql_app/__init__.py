import os

from sqlalchemy import create_engine, String, Column, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


database_uri = os.environ.get('DATABASE_URI') is None and 'sqlite:///./sql_app.sqlite' or os.environ.get('DATABASE_URI')

engine = create_engine(
    database_uri, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

__all__ = ['Base', 'engine', 'SessionLocal', 'utils']
