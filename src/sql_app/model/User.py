from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from datetime import datetime, timedelta

from sqlalchemy.orm import relationship

from ..db import Base


class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    username = Column(String(24), nullable=False, unique=True)
    email = Column(String(255), nullable=False, unique=True)
    password = Column(String(24), nullable=False)
    level = Column(Integer, nullable=False)  # permission level
    sessions = relationship('Session', backref='user', passive_deletes=True)


def get_expire_date():
    return datetime.now() + timedelta(days=30)


class Session(Base):
    __tablename__ = 'session'
    uid = Column(Integer, ForeignKey('user.id'), primary_key=True)
    session = Column(String(24), nullable=False, primary_key=True, unique=True)
    expire = Column(DateTime, nullable=True, default=get_expire_date)
