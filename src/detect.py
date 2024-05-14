import io
import uuid
from datetime import datetime

import PIL
import aiofiles
import numpy as np
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy import select
from ultralytics import YOLO

from sql_app.db import AsyncDBSession
from sql_app.model.Model import Model
from sql_app.model.User import User
from user import token_verify

detection_router = APIRouter(prefix="/detect", tags=['detect'])


@detection_router.post("/latest/img")
async def detect_image(db: AsyncDBSession, image: UploadFile = File(...)):

    stmt = select(Model).order_by(Model.update_date.desc()).limit(1)
    result = (await db.execute(stmt)).scalars().first()
    model = YOLO(result.file_path)

    contents = await image.read()
    img = PIL.Image.open(io.BytesIO(contents))
    img_np = np.array(img)

    result = model(img_np, 0.5)

    dict = {}

    print(model.names)

    for i in result:
        for j in i.boxes:
            index = int(j.cls)
            name = model.names[index]
            conf = j.conf[0]
            if conf > 0.5:
                dict[name] = 1

    return list(dict.keys())


@detection_router.post("/upload/pt")
async def upload_pt(db: AsyncDBSession, description: str, version: str, user: User = Depends(token_verify),
                    pt: UploadFile = File(...)):
    if user.level <= 127:
        raise HTTPException(status_code=401, detail='You are not administrator')

    filename = f"pt/{uuid.uuid4().hex}.pt"
    size = 0
    async with aiofiles.open(filename, 'wb') as output_file:
        content = await pt.read()
        size = len(content)
        await output_file.write(content)

    # info = {
    #     'description': 'No description',
    #     'version': '1.0'
    # }

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

    return {'message': 'Register success'}
