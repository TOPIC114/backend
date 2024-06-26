import io
import logging
import os
import uuid
from datetime import datetime

import PIL
import aiofiles
import numpy as np
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy import select, update, delete
from starlette.concurrency import run_in_threadpool
from ultralytics import YOLO

from sql_app.db import AsyncDBSession
from sql_app.model.Model import Model
from sql_app.model.Recipe import Ingredient
from sql_app.model.User import User
from user import token_verify

import cv2

detection_router = APIRouter(prefix="/detect", tags=['detect'])
limit = 0.1  # seconds


logger = logging.getLogger(__name__)

@detection_router.post("/latest/img")
async def detect_image(db: AsyncDBSession, image: UploadFile = File(...)):
    stmt = select(Model).order_by(Model.update_date.desc()).limit(1)
    result = (await db.execute(stmt)).scalars().first()
    model = YOLO(result.file_path)

    contents = await image.read()
    img = PIL.Image.open(io.BytesIO(contents))
    img_np = np.array(img)

    result = await run_in_threadpool(model, img_np, 0.5)

    dict = {}

    for i in result:
        for j in i.boxes:
            index = int(j.cls)
            name = model.names[index]
            conf = j.conf[0]
            print(name, conf)
            if conf > 0.5:
                dict[name] = 1

    return list(dict.keys())


@detection_router.post("/{version}/img")
async def detect_image(version: str, db: AsyncDBSession, image: UploadFile = File(...)):
    stmt = select(Model).where(Model.version == version).order_by(Model.update_date.desc()).limit(1)
    result = (await db.execute(stmt)).scalars().first()

    if not result:
        raise HTTPException(status_code=404, detail='Model not found')
    model = YOLO(result.file_path)

    contents = await image.read()
    img = PIL.Image.open(io.BytesIO(contents))
    img_np = np.array(img)

    result = await run_in_threadpool(model, img_np, 0.5)

    dict = {}

    print(model.names)

    for i in result:
        for j in i.boxes:
            index = int(j.cls)
            name = model.names[index]
            conf = j.conf[0]
            print(name, conf)
            if conf > 0.5:
                dict[name] = 1

    return list(dict.keys())


@detection_router.post("/upload/pt")
async def upload_pt(db: AsyncDBSession, description: str, version: str,
                    user: User = Depends(token_verify),
                    pt: UploadFile = File(...)):
    if user.level <= 127:
        raise HTTPException(status_code=401, detail='You are not administrator')

    filepath = pt.filename
    extension = ""

    if filepath.endswith('.pt'):
        extension = 'pt'
    elif filepath.endswith('.engine'):
        extension = 'engine'
    else:
        raise HTTPException(status_code=400, detail='Not supported file type')

    filename = f"pt/{uuid.uuid4().hex}.{extension}"
    async with aiofiles.open(filename, 'wb') as output_file:
        content = await pt.read()
        size = len(content)
        await output_file.write(content)

    # info = {
    #     'description': 'No description',
    #     'version': '1.0'
    # }

    stmt = select(Model).where(Model.version == version)
    result = (await db.execute(stmt)).scalars().first()

    if result:
        path: str = result.file_path
        os.remove(path)
        stmt = (update(Model).where(Model.version == version).values(
            file_path=filename,
            description=description,
            size=size,
            update_date=datetime.now()
        ))
        try:
            await db.execute(stmt)
            await db.commit()
        except Exception as e:
            await db.rollback()
            raise e

    else:
        model_information = Model(
            file_path=filename,
            description=description,
            size=size,
            version=version,
            update_date=datetime.now()
        )

        try:
            db.add(model_information)
            await db.commit()
            await db.refresh(model_information)
        except Exception as e:
            await db.rollback()
            raise e

    model = YOLO(filename)

    for _, j in model.names.items():
        stmt = select(Ingredient).where(Ingredient.name == j)
        result = (await db.execute(stmt)).scalars().first()
        if not result:
            try:
                igr = Ingredient(name=j, mandarin="還沒有翻譯")
                db.add(igr)
                await db.commit()
                await db.refresh(igr)
            except Exception as e:
                await db.rollback()
                raise e

    return {'message': 'Register success'}


@detection_router.get("/versions")
async def get_versions(db: AsyncDBSession):
    stmt = select(Model).distinct()
    result = (await db.execute(stmt)).scalars().all()
    return result


@detection_router.delete("/{version}/delete")
async def delete_version(version: str, db: AsyncDBSession, user: User = Depends(token_verify)):
    if user.level <= 127:
        raise HTTPException(status_code=401, detail='You are not administrator')

    stmt = select(Model).where(Model.version == version)
    result = (await db.execute(stmt)).scalars().first()

    if not result:
        raise HTTPException(status_code=404, detail='Model not found')

    path = result.file_path
    os.remove(path)

    stmt = select(Model).where(Model.version == version)
    result = (await db.execute(stmt)).scalars().first()

    if not result:
        raise HTTPException(status_code=404, detail='Model not found')

    stmt = delete(Model).where(Model.version == version)

    try:
        await db.execute(stmt)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise e

    return {'message': 'Delete success'}


def video_processing(model, filename):
    cap = cv2.VideoCapture(filename)
    framerate = cap.get(cv2.CAP_PROP_FPS)

    list_of_detected = {}
    continue_detect = {}
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        results = model(frame, 0.5, verbose=False)

        detect_obj = {}
        for i in results:
            for j in i.boxes:
                index = int(j.cls)
                name = model.names[index]
                conf = j.conf[0]
                if conf > 0.5:
                    detect_obj[name] = True

        for i in detect_obj.keys():
            if i in continue_detect:
                continue_detect[i] = continue_detect[i] + 1
            else:
                continue_detect[i] = 1

        for key, value in continue_detect.items():
            if value > framerate * limit:
                list_of_detected[key] = 1
                continue_detect[key] = 0

        for key in list_of_detected.keys():
            if key not in continue_detect:  # not continue detected the object so remove from it.
                del continue_detect[key]

    os.remove(filename)
    return list(list_of_detected.keys())


# only support mp4 file
@detection_router.post('/latest/video')
async def detect_video(db: AsyncDBSession, video: UploadFile = File(...)):
    stmt = select(Model).order_by(Model.update_date.desc()).limit(1)
    result = (await db.execute(stmt)).scalars().first()
    model = YOLO(result.file_path, task='detect')

    contents = await video.read()

    filename = f"temp/{uuid.uuid4().hex}.mp4"

    async with aiofiles.open(filename, 'wb') as output_file:
        await output_file.write(contents)

    time_old = datetime.now()
    result = await run_in_threadpool(video_processing, model, filename)
    logger.info(f"take {datetime.now() - time_old} to detect video")

    return result


@detection_router.post('/{version}/video')
async def detect_video(version: str, db: AsyncDBSession, video: UploadFile = File(...)):
    stmt = select(Model).where(Model.version == version).order_by(Model.update_date.desc()).limit(1)
    result = (await db.execute(stmt)).scalars().first()
    model = YOLO(result.file_path, task='detect')

    contents = await video.read()

    filename = f"temp/{uuid.uuid4().hex}.mp4"

    async with aiofiles.open(filename, 'wb') as output_file:
        await output_file.write(contents)

    time_old = datetime.now()
    result = await run_in_threadpool(video_processing, model, filename)
    logger.info(f"Take {datetime.now() - time_old} to detect video")
    return result
