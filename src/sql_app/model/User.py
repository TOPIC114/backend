from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Table
from datetime import datetime, timedelta

from sqlalchemy.orm import relationship

from ..db import Base

search = Table('search', Base.metadata,
               Column('uid', Integer, ForeignKey('user.id'), primary_key=True),
               Column('rid', Integer, ForeignKey('recipe.id'), primary_key=True),
               Column('search_date', DateTime, nullable=False)
               )

author = Table('author', Base.metadata,
               Column('uid', Integer, ForeignKey('user.id'), primary_key=True),
               Column('rid', Integer, ForeignKey('recipe.id'), primary_key=True)
               )


class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    username = Column(String(24), nullable=False, unique=True)
    email = Column(String(255), nullable=False, unique=True)
    password = Column(String(24), nullable=False)
    level = Column(Integer, nullable=False)  # permission level
    sessions = relationship('Session', backref='user', passive_deletes=True)
    comments = relationship('Comment', backref='user', passive_deletes=True)
    searches = relationship('Recipe', secondary=search, backref='user', passive_deletes=True, lazy='dynamic')
    authors = relationship('Recipe', secondary=author, backref='user', passive_deletes=True, lazy='dynamic')


def get_expire_date():
    return datetime.now() + timedelta(days=30)


class Session(Base):
    __tablename__ = 'session'
    uid = Column(Integer, ForeignKey('user.id'), primary_key=True)
    session = Column(String(24), nullable=False, primary_key=True, unique=True)
    expire = Column(DateTime, nullable=True, default=get_expire_date)


class Comment(Base):
    __tablename__ = 'comment'
    uid = Column(Integer, ForeignKey('user.id'), primary_key=True)
    rid = Column(Integer, ForeignKey('recipe.id'), primary_key=True)
    comment = Column(String, nullable=False)
    rate = Column(Integer, nullable=False)
