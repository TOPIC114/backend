from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from sql_app.db import AsyncDBSession
from sql_app.model.User import User

test_router = APIRouter()


@test_router.get('/test/async/read')
async def read_test_user_100_async(db: AsyncDBSession):
    stmt = select(User).where(User.name == "test1").limit(1)
    result = await db.execute(stmt)
    items = result.scalars().first()  # list

    if not items:
        raise HTTPException(status_code=404)

    return items
