import logging
from http.client import HTTPException

from fastapi import APIRouter, Depends
from sqlalchemy import text

from request.made import MadeUpdate, MadeDelete
from response.utils import SuccessResponse
from sql_app.db import AsyncDBSession
from user import token_verify

made_root = APIRouter(prefix='/made', tags=['made'])
logger = logging.getLogger(__name__)

update_stmt = text(
    """
    INSERT INTO backend.made (rid,iid,main,weight) VALUES (:rid,:iid,:main,1)
    ON DUPLICATE KEY UPDATE main=:main
    """
)

@made_root.post('/update')
async def update_recipe(r:MadeUpdate,db:AsyncDBSession,user=Depends(token_verify)) -> SuccessResponse:
    """
    # Insert or update the ingredient main/sub in the recipe (Admin only)

    ## Request Body
    - rid: recipe id
    - iid: ingredient id
    - main: main or sub ingredient

    ## Response code
    - 200: success
    - 400: failed
    - 403: permission denied / token expired / invalid token

    ## Response Body
    - message: success , if failed, return this field will be empty.

    """

    if user.level < 129:
        raise HTTPException(status_code=403,detail='permission denied')

    try:
        await db.execute(update_stmt,{'rid':r.rid,'iid':r.iid,'main':r.main})
        await db.commit()
        return SuccessResponse(message='success')
    except Exception as e:
        await db.rollback()
        logger.exception(e)
        raise HTTPException(status_code=400)


delete_stmt = text(
    """
    DELETE FROM made WHERE rid=:rid AND iid=:iid
    """
)

@made_root.delete('/delete')
async def delete_recipe(r:MadeDelete,db:AsyncDBSession,user=Depends(token_verify)) -> SuccessResponse:
    logger.debug("delete_recipe")
    """
    # Delete the ingredient in the recipe (Admin only)

    ## Request Body
    - rid: recipe id
    - iid: ingredient id

    ## Response code
    - 200: success
    - 400: failed
    - 403: permission denied / token expired / invalid token

    """

    if user.level < 129:
        raise HTTPException(status_code=403,detail='permission denied')

    rid = r.rid
    iid = r.iid

    try:
        await db.execute(delete_stmt,{'rid':rid,'iid':iid})
        await db.commit()
        return SuccessResponse(message='success')
    except Exception as e:
        await db.rollback()
        logger.exception(e)
        raise HTTPException(status_code=400)