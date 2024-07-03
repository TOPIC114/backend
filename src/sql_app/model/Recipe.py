from sqlalchemy.orm import relationship

from ..db import Base
from sqlalchemy import Column, Integer, String, Table, ForeignKey, FLOAT

made = Table(
    'made', Base.metadata,
    Column('rid', Integer, ForeignKey('recipe.id', ondelete='CASCADE'), primary_key=True),
    Column('iid', Integer, ForeignKey('ingredient.id', ondelete='CASCADE'), primary_key=True),
    Column('weight', FLOAT, nullable=False, default=1.0)
)


class Recipe(Base):
    __tablename__ = 'recipe'
    id = Column(Integer, primary_key=True)
    name = Column(String(32), nullable=False)
    description = Column(String(60), nullable=False)
    video_link = Column(String(256), nullable=True)
    rtype = Column(Integer, ForeignKey('recipe_type.id', ondelete='SET NULL'), nullable=True)
    comments = relationship('Comment', backref='Recipe', passive_deletes=True)
    searches = relationship('User', secondary='search', backref='Recipe', passive_deletes=True, lazy='dynamic')
    authors = relationship('User', secondary='author', backref='author', passive_deletes=True, lazy='dynamic')
    made = relationship('Ingredient', secondary=made, backref='Recipe', passive_deletes=True, lazy='dynamic')


class RecipeType(Base):
    __tablename__ = 'recipe_type'
    id = Column(Integer, primary_key=True)
    name = Column(String(16), nullable=False)
    recipes = relationship('Recipe', backref='RecipeType', lazy='dynamic')


class Ingredient(Base):
    __tablename__ = 'ingredient'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(32), nullable=False)
    mandarin = Column(String(16), nullable=False)
    made = relationship('Recipe', secondary=made, backref='Ingredient', passive_deletes=True, lazy='dynamic')


class SubIngredient(Base):
    __tablename__ = 'sub_ingredient'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(32), nullable=False)
    mandarin = Column(String(16), nullable=False)
    parent = Column(Integer, ForeignKey('ingredient.id'), unique=True)
