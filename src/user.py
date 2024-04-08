from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import IntegrityError

from request.user import RegisterRequest
from response.utils import SuccessResponse
from sql_app.db import AsyncDBSession
from sql_app.model.User import User

user_root = APIRouter(
    prefix='/user',
    tags=['user']
)


@user_root.post('/register', status_code=201, responses={
    409: {"description": "Conflict - Username or email already exists"}
})
async def register_account(info: RegisterRequest, db: AsyncDBSession) -> SuccessResponse:
    user = User(username=info.username, password=info.password, email=info.email, level=1)
    try:
        db.add(user)
        await db.commit()
        await db.refresh(user)
    except IntegrityError as e:
        raise HTTPException(status_code=409, detail='Username or email already exists')
    except Exception as e:
        await db.rollback()
        raise e
    return {'message': 'Register success'}
