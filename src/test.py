from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from datetime import date

from sql_app.db import AsyncDBSession
from sql_app.model.User import User
from sql_app.model.Recipe import Recipe
from sql_app.model.Model import Model

test_router = APIRouter()


@test_router.get('/test/async/user/read')
async def read_test_user_100_async(db: AsyncDBSession):
    stmt = select(User).where(User.username == "test1").limit(1)
    result = await db.execute(stmt)
    items = result.scalars().first()  # list

    if not items:
        raise HTTPException(status_code=404)

    return items


@test_router.get('/test/async/user/write', status_code=201)  # no message return
async def write_test_user_100_async(db: AsyncDBSession):
    user = User(username="test1", password="hi", email="123", level=5)
    try:
        db.add(user)
        await db.commit()
        await db.refresh(user)
    except Exception as e:
        await db.rollback()
        raise e
    return user


@test_router.get('/test/async/recipe/read')
async def read_recipe_async(db: AsyncDBSession):
    stmt = select(Recipe).where(Recipe.name == "Recipe_1")
    result = await db.execute(stmt)
    items = result.scalars().all()

    if not items:
        raise HTTPException(status_code=404)

    return items


@test_router.get('/test/async/recipe/write', status_code=201)
async def write_recipe_async(db: AsyncDBSession):
    new_recipe = Recipe(name="Recipe_1", type="type_1", intro="test_intro", video_link="test_link")
    try:
        db.add(new_recipe)
        await db.commit()
        await db.refresh(new_recipe)
    except Exception as e:
        await db.rollback()
        raise e
    return new_recipe


@test_router.get('/test/async/model/read')
async def read_model_async(db: AsyncDBSession):
    stmt = select(Model).where(Model.version == "version1")
    result = await db.execute(stmt)
    items = result.scalars().all()

    if not items:
        raise HTTPException(status_code=404)

    return items


@test_router.get('/test/async/model/write', status_code=201)
async def write_model_async(db: AsyncDBSession):
    new_model = Model(file_path="test_file_path", description="test_description", size="test_size", version="version1",
                      update_date=date.today())
    try:
        db.add(new_model)
        await db.commit()
        await db.refresh(new_model)
    except Exception as e:
        await db.rollback()
        raise e
    return new_model
