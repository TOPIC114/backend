import uuid

from fastapi import APIRouter, HTTPException, Security, Depends
from fastapi.security import APIKeyHeader
from sqlalchemy import select, or_, delete
from sqlalchemy.exc import IntegrityError

from request.user import RegisterRequest, LoginRequest
from response.user import UserInfoResponse
from response.utils import SuccessResponse
from sql_app.db import AsyncDBSession
from sql_app.model.Recipe import Recipe
from sql_app.model.User import User, Session, search

user_root = APIRouter(
    prefix='/user',
    tags=['user']
)


@user_root.post('/register', responses={
    409: {"description": "Conflict - Username or email already exists"}
})
async def register_account(info: RegisterRequest, db: AsyncDBSession) -> SuccessResponse:
    """
    # Register a new account

    ### Request Body
    - `username`: string, the username of the account

    - `password`: string, the password of the account

    - `email`: string, the email of the account

    ### Response Body
    - `message`: string, the message of the response, telling the user the register is success. You can ignore this message.

    """
    user = User(username=info.username, password=info.password, email=info.email, level=1)
    try:
        db.add(user)
        await db.commit()
        await db.refresh(user)
    except IntegrityError as _:
        raise HTTPException(status_code=409, detail='Username or email already exists')
    except Exception as e:
        await db.rollback()
        raise e
    return {'message': 'Register success'}


@user_root.post('/login', status_code=200, responses={
    401: {"description": "Unauthorized - Wrong username/email or password"}
})
async def login(info: LoginRequest, db: AsyncDBSession):

    """
    # Login to an account
    the endpoint will return a token for the user to use in the future requests,
    ** you need to save the token in where is safe **

    ### Request Body
    - `username`: string, the username or email of the account

    - `password`: string, the password of the account

    ### Response Body
    - `token`: string, the token for the user to use in the future requests

    ### Send the token in the header
    You need to send the token in the header with the key name `X-API-Key` in the future requests

    """

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
    stmt = select(User).join_from(User, Session).where(Session.session == token).limit(1)
    result = await db.execute(stmt)
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=401, detail='Invalid token')
    return user

@user_root.get('/me', status_code=200, responses={
    401: {"description": "Unauthorized - Invalid token"}
})
async def get_user_info(user: User = Depends(token_verify)) -> UserInfoResponse:
    return {'id': user.id, 'username': user.username, 'email': user.email, 'level': user.level}


@user_root.get('/searches', status_code=200, responses={
    401: {"description": "Unauthorized - Invalid token"}
})
async def get_user_search_history(db: AsyncDBSession, user: User = Depends(token_verify)):
    stmt = select(Recipe).join_from(search, Recipe).where(search.c.uid == user.id)
    result = await db.execute(stmt)
    recipe_list = result.scalars().all()
    return recipe_list


@user_root.get('/logout', status_code=200, responses={
    401: {"description": "Unauthorized - Invalid token"}
})
async def logout(db: AsyncDBSession, token: str = Security(api_key_header)) -> SuccessResponse:

    """
    # Logout the account (**Token required**)
    
    ### Response Body
    - `message`: string, the message of the response, telling the user the logout is success. You can ignore this message

    """

    stmt1 = select(Session).where(Session.session == token).limit(1)
    result = await db.execute(stmt1)
    sessions = result.scalars().first()
    if not sessions:
        raise HTTPException(status_code=401, detail='Invalid token')

    stmt2 = delete(Session).where(Session.session == token)
    await db.execute(stmt2)
    await db.commit()
    return {'message': 'Logout success'}


@user_root.get('/logout/all', status_code=200, responses={
    401: {"description": "Unauthorized - Invalid token"}
})
async def logout(db: AsyncDBSession, user: User = Depends(token_verify)) -> SuccessResponse:
    """
    # Logout all the account sessions (**Token required**)

    ### Response Body
    - `message`: string, the message of the response, telling the user the logout is success. You can ignore this message

    """

    stmt2 = delete(Session).where(Session.uid == user.id)
    await db.execute(stmt2)
    await db.commit()
    return {'message': 'Logout success'}
