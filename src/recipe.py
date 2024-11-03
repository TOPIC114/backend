import os
from typing import List

from fastapi import APIRouter, HTTPException, Depends
from fastapi.params import Query

from sql_app.db import AsyncDBSession
from sqlalchemy import select, delete, and_, func, text

from request.recipe import *
from sql_app.model.Recipe import *
from sql_app.model.User import *
from response.recipe import *
from response.utils import SuccessResponse
from user import token_verify
from discord_webhook import DiscordWebhook


recipe_root = APIRouter(prefix="/recipes", tags=['recipe'])
type_webhook = os.getenv("type_webhook")
recipe_webhook = os.getenv("recipe_webhook")

@recipe_root.post("/create")
async def create_recipe(info: RecipeUpload, db: AsyncDBSession, user: User = Depends(token_verify)):
    if user.level < 128:
        raise HTTPException(status_code=404)
    new_recipe = Recipe(name=info.name, description=info.description,
                        video_link=info.video_link, rtype=info.rtype)
    uid = user.id
    try:
        db.add(new_recipe)
        await db.commit()
        await db.refresh(new_recipe)
        rid = new_recipe.id
        await db.execute(author.insert().values(uid=uid, rid=rid))
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise e

    webhook = DiscordWebhook(url=recipe_webhook, content=f"# {rid}.{info.name}\n{info.description}")
    response = webhook.execute()

    return {"rid": rid}

@recipe_root.post("/type/create")
async def create_recipe_type(info: RecipeTypeRequest, db: AsyncDBSession, user: User = Depends(token_verify)) -> SuccessResponse:
    if user.level < 128:
        raise HTTPException(status_code=401)
    
    webhook = DiscordWebhook(url=type_webhook, content=info.name)
    response = webhook.execute()

    new_type = RecipeType(name=info.name)
    try:
        db.add(new_type)
        await db.commit()
        await db.refresh(new_type)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise e

    return {'message': 'upload success'}


@recipe_root.get("/type/list")
async def create_recipe_type( db: AsyncDBSession):
    stmt = select(RecipeType)
    result = await db.execute(stmt)
    types = result.scalars().all()

    return types

@recipe_root.get("/list/{offset}")
async def recipe_list(offset: int, db: AsyncDBSession):
    stmt = select(Recipe).offset(offset * 100).limit(100)
    result = await db.execute(stmt)
    list = result.scalars().all()
    return list


@recipe_root.get("/count")
async def recipe_count(db: AsyncDBSession):
    stmt = select(func.count()).select_from(select(Recipe.id))
    result = await db.execute(stmt)
    count = result.scalars().first()

    return {"count": count}

@recipe_root.delete("/type/{tid}")
async def delete_recipe_type(tid: int, db: AsyncDBSession, user: User = Depends(token_verify)) -> SuccessResponse:
    if user.level < 128:
        raise HTTPException(status_code=401)

    stmt = delete(RecipeType).where(RecipeType.id == tid)
    await db.execute(stmt)
    await db.commit()

    return {'message': 'delete success'}

search_by_iids_stmt = text(
    """
    select
        made.rid as rid,
        r.name as title,
        video_link as link,
        score.s as score
    FROM backend.made
    INNER JOIN backend.recipe r
        on made.rid = r.id
    INNER JOIN backend.author a
        on backend.made.rid = a.rid
    INNER JOIN backend.user u
        on a.uid = u.id
    INNER JOIN backend.recipe_type rt
        on r.rtype = rt.id
    LEFT OUTER JOIN (
        SELECT AVG(comment.rate) as s,comment.recipe_id
        FROM comment
        GROUP BY comment.recipe_id
    ) as score
    ON score.recipe_id = r.id
    WHERE
        iid IN (17,73,30,15)
    GROUP BY rid
    HAVING
        SUM(made.weight) <> 0
    ORDER BY
        SUM(made.weight) desc,
        COUNT(made.weight) desc,
        rid
    LIMIT 100
    OFFSET :offset
    """
)

search_by_keyword = text(
    """
    select
        r.id as rid,
        r.name as title,
        r.video_link as link,
        score.s as score
    FROM backend.recipe r
    INNER JOIN backend.author a
        ON r.id = a.rid
    INNER JOIN backend.user
        ON a.uid = user.id
    INNER JOIN backend.recipe_type rt
        on r.rtype = rt.id
    INNER JOIN (
        SELECT rid, COUNT(iid) as count
        FROM made
        GROUP BY rid
    ) as ic
    ON ic.rid = r.id
    LEFT OUTER JOIN (
        SELECT AVG(comment.rate) as s,comment.recipe_id
        FROM comment
        GROUP BY comment.recipe_id
    ) as score
    ON score.recipe_id = r.id
    WHERE
        r.name LIKE CONCAT('%',:keyword,'%') OR
        r.description LIKE CONCAT('%',:keyword,'%') OR
        rt.name LIKE CONCAT('%',:keyword,'%') OR
        username LIKE CONCAT('%',:keyword,'%')
    ORDER BY
        CASE
            WHEN rt.name = :keyword THEN 1
            WHEN rt.name LIKE CONCAT('%',:keyword,'%') THEN 2
            ELSE 3
        END,
        CASE
            WHEN title = :keyword THEN 1
            WHEN title LIKE CONCAT('%',:keyword,'%') THEN 2
            ELSE 3
        END,
        ic.count
        ,
        CASE
            WHEN username = :keyword THEN 1
            WHEN username LIKE CONCAT('%',:keyword,'%') THEN 2
            ELSE 3
        END,
        r.id
    LIMIT 100
    OFFSET :offset
    """
)

@recipe_root.get("/search/iid")
async def search_by_iid(offset:int, db: AsyncDBSession, iids:List[int] = Query(None)) -> List[RecipeSearchResponse]:
    result = await db.execute(search_by_iids_stmt,{"iids":iids,"offset":offset*100})
    rows = result.fetchall()

    # Convert results to a list of dictionaries
    response = [
        {
            "rid": row.rid,
            "title": row.title,
            "link": row.link,
            "score":row.score,
        }
        for row in rows
    ]

    return response

@recipe_root.get("/search/keyword")
async def search_by_keyword(keyword:str, offset:int, db: AsyncDBSession) -> List[RecipeSearchResponse]:
    result = await db.execute(search_by_iids_stmt,{"keyword":f"\"{keyword}\"","offset":offset*100})
    rows = result.fetchall()
    response = [
        {
            "rid": row.rid,
            "title": row.title,
            "link": row.link,
            "score": row.score,
        }
        for row in rows
    ]

    return response

@recipe_root.get("/content/{rid}", status_code=200)
async def read_recipe(rid: int, db: AsyncDBSession, user: User = Depends(token_verify)) -> RecipeInfoResponse:
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
             .where(and_(search.c.uid == user.id, search.c.rid == rid)))
    result = await db.execute(stmt2)
    history = result.scalars().first()

    if history:
        new = (search.update().where(and_(search.c.uid == user.id, search.c.rid == rid))
               .values(search_date=datetime.now()))
    else:
        new = search.insert().values(uid=user.id, rid=rid, search_date=datetime.now())

    await db.execute(new)
    await db.commit()

    return {"id": recipe_id, "name": name, "description": description, "video_link": video_link, "rtype": rtype}


@recipe_root.delete("/delete/{rid}", status_code=200)
async def delete_recipe(rid: int, db: AsyncDBSession, user: User = Depends(token_verify)) -> SuccessResponse:
    if user.level < 128:
        raise HTTPException(status_code=404)

    stmt1 = select(Recipe).where(Recipe.id == rid).limit(1)
    result = await db.execute(stmt1)
    recipe = result.scalars().first()
    if not recipe:
        raise HTTPException(status_code=404)

    stmt1 = select(User).join_from(author, User).where(author.c.uid == user.id)
    result = await db.execute(stmt1)
    recipe_author = result.scalars().first()

    if not recipe_author:
        raise HTTPException(status_code=404)

    if user.level == 127 or user.id == recipe_author.id:
        stmt2 = delete(Recipe).where(Recipe.id == rid)
        await db.execute(stmt2)
        await db.commit()
        stmt3 = delete(author).where(author.c.rid == rid)
        await db.execute(stmt3)
        await db.commit()
    else:
        raise HTTPException(status_code=404)

    return {'message': 'deleted recipe'}

insert_comment = text(
    """
    INSERT INTO backend.comment (id, recipe_id, comment, rate) VALUE (:uid, :rid, :comment, :rate)
    ON DUPLICATE KEY UPDATE comment=VALUES(comment),rate=VALUES(rate)
    """
)

@recipe_root.post("/comment/{rid}", status_code=200)
async def post_comment(post:CommentCreate, db:AsyncDBSession, user = Depends(token_verify)):
    if user.level < 128:
        raise HTTPException(status_code=404)

    if not ( 0 <= post.rate <= 5):
        raise HTTPException(status_code=400, detail="rate must be between 0 and 5")

    try:
        await db.execute(insert_comment,{"uid":user.id,"rid":post.rid,"comment":post.content,"rate":post.rate})
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise e

    return {"message": "comment posted"}

search_recipe_avg = text(
    """
    SELECT AVG(rate) FROM backend.comment
    GROUP BY comment.recipe_id
    """
)
