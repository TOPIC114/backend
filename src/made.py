from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update, and_, text

from request.made import MadeUpload, MadeUploadList
from sql_app.db import AsyncDBSession
from sql_app.model.Recipe import made, Recipe
from sql_app.model.User import User
from user import token_verify

m_router = APIRouter(prefix="/made", tags=['made'])

update_weight = text(
    """
    UPDATE backend.made
    INNER JOIN (
        SELECT
            rid,
            iid,
            COUNT(iid) AS weight
        FROM backend.recipe
        INNER JOIN backend.made
            ON recipe.id = made.rid
        GROUP BY rtype,iid
    ) AS b
    ON backend.made.rid = b.rid and backend.made.iid=b.iid
    SET
        backend.made.weight = b.weight
    where
        backend.made.weight<>b.weight;
    """
)

@m_router.post('/create')
async def by_id(db: AsyncDBSession, request: MadeUpload, user: User = Depends(token_verify)):
    if user.level <= 127:
        print(user.level)
        raise HTTPException(status_code=401, detail='You are not administrator')
    mades = made.insert().values(rid=request.rid, iid=request.iid, weight=1.0)

    try:
        await db.execute(mades)
        await db.commit()
        await db.execute(update_weight)
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
        temp = made.insert().values(rid=request.rid, iid=iid, weight=1.0)
        try:
            await db.execute(temp)
            await db.commit()
        except Exception as e:
            await db.rollback()
            raise e

    try:
        await db.execute(update_weight)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise e
    return {'message': 'upload success'}
