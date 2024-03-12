from sqlalchemy import Column, Integer, String

from ..db import Base


class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    name = Column(String(24), nullable=False)
    level = Column(Integer, nullable=False)

