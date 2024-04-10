from fastapi import APIRouter, HTTPException, Depends
from sql_app.db import AsyncDBSession
from sqlalchemy import select, delete

from request.recipe import *
from sql_app.model.Recipe import *
from sql_app.model.User import *
from user import token_verify


recipe_root = APIRouter(prefix="/recipes", tags=['recipe'])


@recipe_root.post("/upload", status_code=201)
async def create_recipe(info: RecipeUpload, db: AsyncDBSession, user: User = Depends(token_verify)):
    if user.level < 2:
        raise HTTPException(status_code=404)
    new_recipe = Recipe(name=info.name, description=info.description,
                        video_link=info.video_link, rtype=info.rtype)
    try:
        db.add(new_recipe)
        await db.commit()
        await db.refresh(new_recipe)
    except Exception as e:
        await db.rollback()
        raise e

    return new_recipe


@recipe_root.post("/search", status_code=200)
async def search_recipe(info: RecipeSearch, db: AsyncDBSession):
    stmt = select(Recipe).where(Recipe.name.like("%" + info.keyword + "%"))
    result = await db.execute(stmt)
    recipes = result.scalars().all()

    return recipes


@recipe_root.get("/content/{rid}", status_code=200)
async def read_recipe(rid: int, db: AsyncDBSession, user: User = Depends(token_verify)):
    stmt1 = select(Recipe).where(Recipe.id == rid).limit(1)
    result = await db.execute(stmt1)
    recipe = result.scalars().first()

    recipe_id = recipe.id
    name = recipe.name
    description = recipe.description
    video_link = recipe.video_link
    rtype = recipe.rtype

    if not recipe:
        raise HTTPException(status_code=404)

    stmt2 = (select(Recipe).join_from(search, Recipe)
             .where(search.c.uid == user.id, search.c.rid == rid))
    result = await db.execute(stmt2)
    history = result.scalars().first()

    if history:
        new = (search.update().where(search.c.uid == user.id, search.c.rid == rid)
                  .values(search_date=datetime.now()))
    else:
        new = search.insert().values(uid=user.id, rid=rid, search_date=datetime.now())

    await db.execute(new)
    await db.commit()

    return {"id": recipe_id, "name": name, "description": description, "video_link": video_link, "rtype": rtype}


@recipe_root.get("/delete/{rid}", status_code=200)
async def delete_recipe(rid: int, db: AsyncDBSession, user: User = Depends(token_verify)):
    if user.level < 2:
        raise HTTPException(status_code=404)
    stmt = delete(Recipe).where(Recipe.id == rid)
    await db.execute(stmt)
    await db.commit()
    return {'message': 'deleted recipe'}
