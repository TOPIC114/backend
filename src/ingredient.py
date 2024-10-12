from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update, insert

from request.ingredient import ChangeNameRequest, AddSubIngredient, IngredientCreate
from sql_app.db import AsyncDBSession
from sql_app.model.Recipe import Ingredient, SubIngredient
from sql_app.model.User import User
from user import token_verify

i_router = APIRouter(prefix="/ingredient", tags=['ingredient'])


@i_router.get('/list')
async def list_ingredient(db: AsyncDBSession):
    stmt = select(Ingredient)
    result = await db.execute(stmt)
    return result.scalars().all()


@i_router.post('/mandarin')
async def change_mandarin(db: AsyncDBSession, data: ChangeNameRequest):
    stmt = update(Ingredient).where(Ingredient.id == data.iid).values(mandarin=data.name)
    try:
        await db.execute(stmt)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise e

    return {'message': 'upload success'}


@i_router.post('/create/sub')
async def add_sub(db: AsyncDBSession, data: AddSubIngredient):
    stmt = insert(SubIngredient).values(iid=data.iid, name=data.name, mandarin=data.mandarin)
    try:
        await db.execute(stmt)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise e

    return {'message': 'upload success'}


@i_router.post("/create")
async def create_recipe(info: IngredientCreate, db: AsyncDBSession, user: User = Depends(token_verify)):
    if user.level < 128:
        raise HTTPException(status_code=404)
    stmt = Ingredient(name=info.name, mandarin=info.mandarin)
    try:
        db.add(stmt)
        await db.commit()
        await db.refresh(stmt)
    except Exception as e:
        await db.rollback()
        raise e

    return{'message': 'upload success'}