from fastapi import APIRouter, Depends, HTTPException

from request.made import MadeUpload, MadeUploadList
from sql_app.db import AsyncDBSession
from sql_app.model import Recipe
from sql_app.model.User import User
from user import token_verify

m_router = APIRouter(prefix="/made", tags=['made'])


@m_router.post('/create')
async def by_id(db: AsyncDBSession, request: MadeUpload, user: User = Depends(token_verify)):
    if user.level <= 127:
        print(user.level)
        raise HTTPException(status_code=401, detail='You are not administrator')
    made = Recipe.made.insert().values(rid=request.rid, iid=request.iid, weight=1.0)
    try:
        await db.execute(made)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise e
    return {'message': 'upload success'}


@m_router.post('/create/list')
async def by_id(db: AsyncDBSession, request: MadeUploadList, user: User = Depends(token_verify)):
    if user.level <= 127:
        print(user.level)
        raise HTTPException(status_code=401, detail='You are not administrator')
    for iid in request.iids:
        made = Recipe.made.insert().values(rid=request.rid, iid=iid, weight=1.0)
        try:
            await db.execute(made)
            await db.commit()
        except Exception as e:
            await db.rollback()
            raise e
    return {'message': 'upload success'}

