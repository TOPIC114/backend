from fastapi import APIRouter

from request.user import RegisterRequest
from sql_app.db import AsyncDBSession
from sql_app.model.User import User

user_root = APIRouter(
    prefix='/user',
    tags=['user']
)


@user_root.post('/register')
async def register_account(info: RegisterRequest, db: AsyncDBSession):
    user = User(username=info.username, password=info.password, email=info.email, level=1)
    try:
        db.add(user)
        await db.commit()
        await db.refresh(user)
    except Exception as e:
        await db.rollback()
        raise e
    return user
    pass
