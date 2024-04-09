import uuid

from fastapi import APIRouter, HTTPException, Security, Depends
from fastapi.security import APIKeyHeader
from sqlalchemy import select, or_
from sqlalchemy.exc import IntegrityError

from request.user import RegisterRequest, LoginRequest
from response.utils import SuccessResponse
from sql_app.db import AsyncDBSession
from sql_app.model.User import User, Session

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


@user_root.post('/login', status_code=200, responses={
    401: {"description": "Unauthorized - Wrong username/email or password"}
})
async def login(info: LoginRequest, db: AsyncDBSession):
    stmt = select(User).where(or_(User.username == info.username, User.email == info.username)).limit(1)
    result = await db.execute(stmt)
    user = result.scalars().first()
    if not user or user.password != info.password:
        raise HTTPException(status_code=401, detail='Wrong username/email or password')

    token = uuid.uuid4().hex
    session = Session(uid=user.id, session=token)

    try:
        db.add(session)
        await db.commit()
        await db.refresh(session)
    except Exception as e:
        await db.rollback()
        raise e

    return {'token': token}


api_key_header = APIKeyHeader(name='X-API-Key')


async def token_verify(db: AsyncDBSession, token: str = Security(api_key_header)):
    stmt = select(Session).where(Session.session == token).limit(1)
    result = await db.execute(stmt)
    session = result.scalars().first()
    if not session:
        raise HTTPException(status_code=401, detail='Invalid token')
    return session.uid


@user_root.get('/me', status_code=200)
async def get_user_info(uid: int = Depends(token_verify)):
    return {'uid': uid}
