from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update, func

from request.video import VideoRequest
from response.utils import SuccessResponse
from sql_app.db import AsyncDBSession
from sql_app.model.User import User
from sql_app.model.Video import Video
from user import token_verify

video_root = APIRouter(
    prefix='/video',
    tags=['video']
)


@video_root.post("/upload")  # only for inner use
async def import_video(db: AsyncDBSession, info: VideoRequest, user: User = Depends(token_verify)) -> SuccessResponse:
    if user.level < 127:
        raise HTTPException(status_code=401, detail='You are not administrator')

    new_vid = Video(title=info.title,
                    description=info.description,
                    yt_link=info.yt_link,
                    thumbnail_url=info.thumbnail_url,
                    author_id=info.author_id,
                    )

    try:
        db.add(new_vid)
        await db.commit()
        await db.refresh(new_vid)
    except Exception as e:
        await db.rollback()
        raise e

    return {"message": "import successfully"}


@video_root.get('/list/{offset}')
async def list_video(db: AsyncDBSession, offset: int, user: User = Depends(token_verify)):
    if user.level < 127:
        raise HTTPException(status_code=401, detail='You are not administrator')
    stmt = select(Video).offset(offset * 100).limit(100)

    result = await db.execute(stmt)
    videos = result.scalars().all()

    return videos


@video_root.get('/count')
async def list_video(db: AsyncDBSession, user: User = Depends(token_verify)):
    if user.level < 127:
        raise HTTPException(status_code=401, detail='You are not administrator')
    stmt = select(func.count()).select_from(select(Video.id))
    result = await db.execute(stmt)
    count = result.scalars().first()

    return {"count": count}


@video_root.post('/mark/{id}/complete')
async def mark_complete(db: AsyncDBSession, id: int, user: User = Depends(token_verify)) -> SuccessResponse:
    if user.level < 127:
        raise HTTPException(status_code=401, detail='You are not administrator')

    stmt = update(Video).where(Video.id == id).values(is_complete=True)

    try:
        await db.execute(stmt)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise e

    return {"message": "mark successfully"}


@video_root.post('/mark/{id}/reviewed')
async def mark_complete(db: AsyncDBSession, id: int, user: User = Depends(token_verify)) -> SuccessResponse:
    if user.level < 127:
        raise HTTPException(status_code=401, detail='You are not administrator')

    stmt = update(Video).where(Video.id == id).values(is_reviewed=True)

    try:
        await db.execute(stmt)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise e

    return {"message": "mark successfully"}


@video_root.post("/mark/{id}/ready")  # ready to detected
async def mark_complete(db: AsyncDBSession, id: int, user: User = Depends(token_verify)) -> SuccessResponse:
    if user.level < 127:
        raise HTTPException(status_code=401, detail='You are not administrator')

    stmt = update(Video).where(Video.id == id).values(is_reviewed=False)

    try:
        await db.execute(stmt)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise e

    return {"message": "mark successfully"}

