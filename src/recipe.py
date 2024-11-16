import asyncio
import logging
import os

from fastapi import APIRouter, HTTPException, Depends
from fastapi.params import Query

from sql_app.db import AsyncDBSession
from sqlalchemy import select, delete, func, text

from request.recipe import *
from sql_app.model.Recipe import *
from sql_app.model.User import *
from response.recipe import *
from response.utils import SuccessResponse
from user import token_verify, optional_token_verify
from discord_webhook import DiscordWebhook

recipe_root = APIRouter(prefix="/recipes", tags=['recipe'])
type_webhook = os.getenv("type_webhook")
recipe_webhook = os.getenv("recipe_webhook")

logger = logging.getLogger(__name__)

@recipe_root.post("/create")
async def create_recipe(info: RecipeUpload, db: AsyncDBSession, user: User = Depends(token_verify)) -> SuccessResponse:
    """
    # Create a new recipe (Admin)
    we will convert this to a stuff endpoint in the future
    """
    if user.level <= 64:
        raise HTTPException(status_code=403)
    new_recipe = Recipe(name=info.name, description=info.description,
                        video_link=info.video_link, rtype=info.rtype)
    uid = user.id
    try:
        db.add(new_recipe)
        await db.flush()
        await db.refresh(new_recipe) # to fetch the id
        logger.debug("Added new recipe with id %s", new_recipe.id)

        tasks = []

        tasks.append(db.execute(author.insert().values(uid=uid, rid=new_recipe.id)))
        for i in info.iids:
            tasks.append(db.execute(made.insert().values(rid=new_recipe.id, iid=i, weight=1)))

        await asyncio.gather(*tasks)
        # commit the transaction to save the changes
        await db.commit()

    except Exception as e:
        logger.error("Failed to create recipe, rolling back")
        await db.rollback()
        raise e

    return SuccessResponse(message='upload success')


@recipe_root.post("/type/create")
async def create_recipe_type(info: RecipeTypeRequest, db: AsyncDBSession,
                             user: User = Depends(token_verify)) -> SuccessResponse:
    """
    # Create a new recipe type (Admin Only, don't implement in frontend)
    we may convert this to a stuff endpoint in the future

    """

    if user.level < 128:
        raise HTTPException(status_code=401)

    webhook = DiscordWebhook(url=type_webhook, content=info.name)
    _ = webhook.execute()

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
async def create_recipe_type(db: AsyncDBSession):
    """
    # List all recipe types

    ## Response Body
    - List of recipe types, each recipe type has the following fields:

        - `id`: int, the id of the recipe type

        - `name`: string, the name of the recipe type

    """

    stmt = select(RecipeType)
    result = await db.execute(stmt)
    types = result.scalars().all()

    return types


@recipe_root.get("/list/{offset}")
async def recipe_list(offset: int, db: AsyncDBSession):
    """
    This endpoint is used to list all recipes in the database, you can use this endpoint to get the list of recipes and
    then use the read_recipe endpoint to get the content of the recipe.

    We will refactor this endpoint in the future.

    """

    stmt = select(Recipe).offset(offset * 100).limit(100)
    result = await db.execute(stmt)
    result_list = result.scalars().all()
    return result_list


@recipe_root.get("/count")
async def recipe_count(db: AsyncDBSession):
    """
    # Count the number of recipes in the database

    ## Response Body
    - `count`: int, the number of recipes in the database
    """

    stmt = select(func.count()).select_from(select(Recipe.id))
    result = await db.execute(stmt)
    count = result.scalars().first()

    return {"count": count}


@recipe_root.delete("/type/{tid}")
async def delete_recipe_type(tid: int, db: AsyncDBSession, user: User = Depends(token_verify)) -> SuccessResponse:
    """
    # Delete a recipe type by its id (Admin Only, don't implement in frontend)

    ## Response Body
    - `message`: string, the message of the response, telling the user the recipe type is deleted. You can ignore this
    """

    if user.level < 128:
        raise HTTPException(status_code=401)

    stmt = delete(RecipeType).where(RecipeType.id == tid)
    await db.execute(stmt)
    await db.commit()

    return SuccessResponse(message='delete success')


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
        iid IN :iids
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

search_by_keyword_stmt = text(
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
async def search_by_iid(offset: int, db: AsyncDBSession, iids: List[int] = Query(None)) -> list[RecipeSearchResponse]:
    """
    # Search recipes by ingredient ids

    ## Request Query

    - `iids`: List[int], the list of ingredient ids

    - `offset`: int, the offset of the result list, each page contains 100 recipes

    ## Response Body
    - list of RecipeSearchResponse with the following fields:

        - `rid`: int, the id of the recipe, you will use this to fetch the content of the recipe in the future

        - `title`: string, the title of the recipe

        - `link`: string, the video link of the recipe, format: "https://youtube.com/watch?v={videoid}", if you want
        to fetch video thumbnail, you can use "https://img.youtube.com/vi/{videoid}/hqdefault.jpg" to fetch the image

        - `score`: float, the average score of the recipe

    """

    result = await db.execute(search_by_iids_stmt, {"iids": iids, "offset": offset * 100})

    # Convert results to a list of dictionaries
    response = [
        RecipeSearchResponse(
            rid=row.rid,
            title=row.title,
            link=row.link,
            score=row.score,
        )
        for row in result
    ]

    return response


@recipe_root.get("/search/keyword")
async def search_by_keyword(keyword: str, offset: int, db: AsyncDBSession) -> list[RecipeSearchResponse]:
    """
    # Search recipes by keyword

    ## Request Query

    - `keyword`: string, the keyword to search

    - `offset`: int, the offset of the result list, each page contains 100 recipes

    ## Response Body
    - list of RecipeSearchResponse with the following fields:

        - `rid`: int, the id of the recipe, you will use this to fetch the content of the recipe in the future

        - `title`: string, the title of the recipe

        - `link`: string, the video link of the recipe, format: "https://youtube.com/watch?v={videoid}", if you want
        to fetch video thumbnail, you can use "https://img.youtube.com/vi/{videoid}/hqdefault.jpg" to fetch the image

        - `score`: float, the average score of the recipe

    """
    result = await db.execute(search_by_keyword_stmt, {"keyword": keyword, "offset": offset * 100})

    response = [
        RecipeSearchResponse(
            rid=row.rid,
            title=row.title,
            link=row.link,
            score=row.score,
        )
        for row in result
    ]

    return response


recipe_search = text(
    """
    select
        r.name as title,
        description,
        video_link as video,
        rt.name as rtype,
        username as author
    FROM recipe r
    INNER JOIN backend.recipe_type rt 
        on r.rtype = rt.id
    INNER JOIN backend.author a 
        on r.id = a.rid
    INNER JOIN backend.user u 
        on a.uid = u.id
    where r.id=:rid
    """
)

comment_search_stmt = text(
    """
    select 
        comment.comment as content,
        username,
        rate as score
    FROM comment
    INNER JOIN backend.user u on comment.id = u.id
    WHERE comment.recipe_id = :rid
    """
)

iids_stmt = text(
    """
    select iid
    From made
    WHERE rid=:rid
    """
)

searches = text("""
INSERT INTO backend.search (rid,uid,search_date) VALUES (:rid,:uid,:search_date)
ON DUPLICATE KEY UPDATE search_date=VALUES(search_date)
""")

@recipe_root.get("/content/{rid}", status_code=200)
async def read_recipe(rid: int, db: AsyncDBSession, user = Depends(optional_token_verify)) -> RecipeInfoResponse:
    """
    # Read the content of a recipe by its id

    ## Response Body
    - `title`: string, the title of the recipe
    - `description`: string, the description of the recipe
    - `video`: string, the video link of the recipe
    - `score`: float, the average score of the recipe
    - `rtype`: string, the type of the recipe
    - `author`: string, the author of the recipe
    - `comments`: List[Comment], the list of comments of the recipe
    - `iids`: List[int], the list of ingredient ids of the recipe

    """

    if user:
        logger.debug("Write search history for user %s", user.id)
        await db.execute(searches, {"rid": rid, "uid": user.id, "search_date": datetime.now()})
        await db.commit()

    connect = await db.execute(recipe_search, {"rid": rid})
    recipe = connect.fetchone()

    if recipe == None:
        raise HTTPException(status_code=404)

    ouo = await db.execute(comment_search_stmt, {"rid": rid})
    result = ouo.fetchall()

    comments = [
        {
            "username": i.username,
            "content": i.content,
            "score": i.score
        }
        for i in result
    ]

    if len(comments):
        avg = sum([x["score"] for x in comments]) / len(comments)
    else:
        avg = None

    connect = await db.execute(iids_stmt, {"rid": rid})
    result = connect.fetchall()

    iids = [i.iid for i in result]

    obj = RecipeInfoResponse(
        title=recipe.title,
        description=recipe.description,
        video=recipe.video,
        score=avg,
        rtype=recipe.rtype,
        author=recipe.author,
        comments=comments,
        iids=iids,
    )

    return obj


@recipe_root.delete("/delete/{rid}", status_code=200)
async def delete_recipe(rid: int, db: AsyncDBSession, user: User = Depends(token_verify)) -> SuccessResponse:
    """
    # Delete a recipe by its id (Admin or author itself only)

    ## Response Body
    - `message`: string, the message of the response, telling the user the recipe is deleted. You can ignore this
    """
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


@recipe_root.post("/comment", status_code=200)
async def post_comment(post: CommentCreate, db: AsyncDBSession, user=Depends(token_verify)) -> SuccessResponse:
    """
    # Post a comment to a recipe

    ## Request Body
    - `rid`: int, the id of the recipe

    - `content`: string, the content of the comment

    - `rate`: int, the rate of the recipe, must be between 0 and 5

    ### Response Body
    - `message`: string, the message of the response, telling the user the comment is posted. You can ignore this

    """
    if user.level < 128:
        raise HTTPException(status_code=404)

    if not (0 <= post.rate <= 5):
        raise HTTPException(status_code=400, detail="rate must be between 0 and 5")

    try:
        await db.execute(insert_comment, {"uid": user.id, "rid": post.rid, "comment": post.content, "rate": post.rate})
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise e

    return SuccessResponse(message='comment success')


search_recipe_avg = text(
    """
    SELECT AVG(rate) FROM backend.comment
    GROUP BY comment.recipe_id
    """
)
