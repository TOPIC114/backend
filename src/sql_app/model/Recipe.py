from sqlalchemy.orm import relationship

from ..db import Base
from sqlalchemy import Column, Integer, String, Table, ForeignKey

made = Table(
    'made', Base.metadata,
    Column('rid', Integer, ForeignKey('Recipe.id', ondelete='CASCADE')),
    Column('iid', Integer, ForeignKey('ingredient.id', ondelete='CASCADE'))
)


class Recipe(Base):
    __tablename__ = 'Recipe'
    id = Column(Integer, primary_key=True)
    name = Column(String(32), nullable=False)
    description = Column(String(60), nullable=False)
    video_link = Column(String(256), nullable=True)
    comments = relationship('Comment', backref='Recipe', passive_deletes=True)
    searches = relationship('User', secondary='search', backref='Recipe', passive_deletes=True, lazy='dynamic')
    authors = relationship('User', secondary='author', backref='Recipe', passive_deletes=True, lazy='dynamic')
    made = relationship('Ingredient', secondary=made, backref='Recipe', passive_deletes=True, lazy='dynamic')


class Recipe_Type(Base):
    __tablename__ = 'recipe_type'
    id = Column(Integer, primary_key=True)
    name = Column(String(16), nullable=False)


class Ingredient(Base):
    __tablename__ = 'ingredient'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(32), nullable=False)
    weight = Column(Integer, nullable=False)
    mandarin = Column(String(16), nullable=False)
    made = relationship('Recipe', secondary=made, backref='Ingredient', passive_deletes=True, lazy='dynamic')
