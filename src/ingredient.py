from fastapi import APIRouter
from sqlalchemy import select

from sql_app.db import AsyncDBSession
from sql_app.model.Recipe import Ingredient

i_router = APIRouter(prefix="/ingredient", tags=['ingredient'])


@i_router.get('/list')
async def list_ingredient(db: AsyncDBSession):
    stmt = select(Ingredient)
    result = await db.execute(stmt)
    return result.scalars().all()
