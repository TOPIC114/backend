from sqlalchemy.orm import relationship

from ..db import Base
from sqlalchemy import Column, Integer, String


class Recipe(Base):
    __tablename__ = 'Recipe'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(32), index=True, nullable=False)
    type = Column(String(16), index=True, nullable=False)
    intro = Column(String(60), nullable=False)
    video_link = Column(String(60), nullable=True)
    comments = relationship('Comment', backref='Recipe', passive_deletes=True)
    searches = relationship('User', secondary='search', backref='Recipe', passive_deletes=True, lazy='dynamic')