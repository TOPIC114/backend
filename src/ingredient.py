from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update

from request.ingredient import ChangeNameRequest, IngredientCreate
from sql_app.db import AsyncDBSession
from sql_app.model.Recipe import Ingredient
from sql_app.model.User import User
from user import token_verify

i_router = APIRouter(prefix="/ingredient", tags=['ingredient'])


@i_router.get('/list')
async def list_ingredient(db: AsyncDBSession):
    """
    # List all ingredients
    it will return a list of all ingredients in the database, note that in other endpoints, you will only see id of the
    ingredient, so you can and should use this endpoint to get full details of the ingredient.

    ## Response Body
    - List of ingredients, each ingredient has the following fields:

        - `id`: int, the id of the ingredient

        - `name`: string, the name of the ingredient

        - `mandarin`: string, the mandarin name of the ingredient
    """

    stmt = select(Ingredient)
    result = await db.execute(stmt)
    return result.scalars().all()


@i_router.post('/mandarin')
async def change_mandarin(db: AsyncDBSession, data: ChangeNameRequest):
    """
    # Change the mandarin name of an ingredient (Admin Only, don't implement in frontend)

    ### Request Body
    - `iid`: int, the id of the ingredient

    - `name`: string, the new mandarin name of the ingredient

    """
    stmt = update(Ingredient).where(Ingredient.id == data.iid).values(mandarin=data.name)
    try:
        await db.execute(stmt)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise e

    return {'message': 'upload success'}

@i_router.post("/create")
async def create_recipe(info: IngredientCreate, db: AsyncDBSession, user: User = Depends(token_verify)):
    """
    # Create a new ingredient (Admin Only, don't implement in frontend)

    """

    if user.level < 128:
        raise HTTPException(status_code=403, detail='permission denied')
    stmt = Ingredient(name=info.name, mandarin=info.mandarin)
    try:
        db.add(stmt)
        await db.commit()
        await db.refresh(stmt)
    except Exception as e:
        await db.rollback()
        raise e

    return{'message': 'upload success'}