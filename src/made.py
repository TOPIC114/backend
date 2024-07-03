from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update, and_

from request.made import MadeUpload, MadeUploadList
from sql_app.db import AsyncDBSession
from sql_app.model.Recipe import made, Recipe
from sql_app.model.User import User
from user import token_verify

m_router = APIRouter(prefix="/made", tags=['made'])


@m_router.post('/create')
async def by_id(db: AsyncDBSession, request: MadeUpload, user: User = Depends(token_verify)):
    if user.level <= 127:
        print(user.level)
        raise HTTPException(status_code=401, detail='You are not administrator')
    mades = made.insert().values(rid=request.rid, iid=request.iid, weight=1.0)

    try:
        await db.execute(mades)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise e

    stmt = select(Recipe).where(Recipe.id == request.rid).limit(1)
    result = await db.execute(stmt)
    recipe = result.scalars().first()

    stmt = select(Recipe).where(Recipe.name == recipe.name)
    result = await db.execute(stmt)
    recipes = result.scalars().all()

    count = 0.0

    iids = []

    for i in recipes:
        result = await db.execute(i.made)
        ingridents = result.scalars().all()
        for j in ingridents:
            if j.id == request.iid:
                count = count+1
                iids.append(i.id)

    for i in iids:
        stmt = update(made).where(and_(made.c.rid == i, made.c.iid == request.iid)).values(weight=count)
        try:
            await db.execute(stmt)
            await db.commit()
        except Exception as _: # ignore
            await db.rollback()

    # stmt = select(made.c.weight).where(made.c.rid==1)
    #
    # print(stmt)
    #
    # result = await db.execute(stmt)
    # r = result.scalars().first()
    # print(r)

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

        stmt = select(Recipe).where(Recipe.id == request.rid).limit(1)
        result = await db.execute(stmt)
        recipe = result.scalars().first()

        stmt = select(Recipe).where(Recipe.name == recipe.name)
        result = await db.execute(stmt)
        recipes = result.scalars().all()

        count = 0.0

        iids = []

        for i in recipes:
            result = await db.execute(i.made)
            ingridents = result.scalars().all()
            for j in ingridents:
                if j.id == iid:
                    count = count+1
                    iids.append(i.id)

        for i in iids:
            stmt = update(made).where(and_(made.c.rid == i, made.c.iid == iid)).values(weight=count)
            try:
                await db.execute(stmt)
                await db.commit()
            except Exception as _: # ignore
                await db.rollback()
    return {'message': 'upload success'}
