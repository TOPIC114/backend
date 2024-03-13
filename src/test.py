from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from sql_app.db import AsyncDBSession
from sql_app.model.User import User
from sql_app.model.Recipe import Recipe

test_router = APIRouter()


@test_router.get('/test/async/User_read')
async def read_test_user_100_async(db: AsyncDBSession):
    stmt = select(User).where(User.name == "test1").limit(1)
    result = await db.execute(stmt)
    items = result.scalars().first()  # list

    if not items:
        raise HTTPException(status_code=404)

    return items


@test_router.get('/test/async/User_write', status_code=201)  # no message return
async def write_test_user_100_async(db: AsyncDBSession):
    user = User(name="test1", level=5)
    try:
        db.add(user)
        await db.commit()
        await db.refresh(user)
    except Exception as e:
        await db.rollback()
        raise e
    return user

@test_router.get('/test/async/Recipe_read')
async def read_recipe_async(db: AsyncDBSession):
    stmt = select(Recipe).where(Recipe.name == "Recipe_1")
    result = await db.execute(stmt)
    items = result.scalars().first()

    if not items:
        raise HTTPException(status_code=404)

    return items

@test_router.get('/test/async/Recipe_write', status_code=201)
async def write_recipe_async(db:AsyncDBSession):
    new_recipe = Recipe(name="Recipe_1",type="type_1",intro="test_intro",video_link="test_link")
    try:
        db.add(new_recipe)
        await db.commit()
        await db.refresh(new_recipe)
    except Exception as e:
        await db.rollback()
        raise e
    return new_recipe




