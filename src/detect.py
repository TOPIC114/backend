import copy
import io
import json
import logging
import os
import uuid
from datetime import datetime
from typing import List

import PIL
import aiofiles
import numpy as np
import requests
from PIL import Image, ImageDraw
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy import select, update, delete
from starlette.concurrency import run_in_threadpool
from ultralytics import YOLO
from sahi import AutoDetectionModel
from sahi.predict import get_sliced_prediction
import asyncio
import concurrent.futures

from sql_app.db import AsyncDBSession
from sql_app.model.Model import Model
from sql_app.model.Recipe import Ingredient
from sql_app.model.User import User
from user import token_verify

import cv2
import ffmpeg

import google.generativeai as genai
from google.ai.generativelanguage_v1beta.types import content

detection_router = APIRouter(prefix="/detect", tags=['detect'])
limit = 0.2  # seconds

logger = logging.getLogger(__name__)

detect_process_pool = concurrent.futures.ProcessPoolExecutor(max_workers=2)

# each ingredient's confidence threshold
confidence_filter = {
    "mushroom": 0.85,
    "okra": 0.75,
    "heim": 0.85,
    "beef": 0.4,
    "chicken": 0.4,
    "pork": 0.4,
    "noodle": 0.85,
    "carrot": 0.5,
    "common": 0.65  # the ingridient which is not in the filter
}


def result_processing(img, results):  # results:[{"key":[(x1,x2,y1,y2)]}]
    path = {}
    for key, points in results.items():
        img_cp = img.copy()
        img_draw = ImageDraw.Draw(img_cp)
        random_name = f"img/{uuid.uuid4().hex}.jpg"
        for point in points:
            x1, x2, y1, y2 = point
            img_draw.rectangle([(x1, y1), (x2, y2)], outline="red", width=3)
        path[key] = random_name
        img_cp.save(random_name)
    return path


def image_processing(image, model_path):
    model = AutoDetectionModel.from_pretrained(
        model_type="yolov8",
        device="cuda:0",
        model_path=model_path,
    )
    results = get_sliced_prediction(image, model, slice_height=500, slice_width=500, overlap_height_ratio=0.2,
                                    overlap_width_ratio=0.2)
    result = {}

    print("%-5s %-20s %-15s %s %s" % ("index", "name", "confidence", "status", "threshold"))

    for idx, det in enumerate(results.object_prediction_list):

        show_log = lambda status, th: print(
            "%-5d %-20s %.13f %-6s %s" % (idx, det.category.name, det.score.value, status, th))

        if det.category.name not in confidence_filter:
            threshold = confidence_filter['common']
        else:
            threshold = confidence_filter[det.category.name]

        if det.score.value < threshold:
            show_log("ignore", threshold)
            continue

        show_log("keep", threshold)

        if det.category.name not in result:
            result[det.category.name] = []
        result[det.category.name].append([det.bbox.minx, det.bbox.maxx, det.bbox.miny, det.bbox.maxy])

    return result


@detection_router.post("/latest/img")
async def detect_image(db: AsyncDBSession, image: UploadFile = File(...)) -> dict[str, str]:
    stmt = select(Model).order_by(Model.update_date.desc()).limit(1)
    result = (await db.execute(stmt)).scalars().first()

    contents = await image.read()
    img = PIL.Image.open(io.BytesIO(contents))
    img_np = np.array(img)
    # img_np = img_np[:, :, ::-1]

    loop = asyncio.get_event_loop()
    time_old = datetime.now()
    det_result = await loop.run_in_executor(detect_process_pool, image_processing, img_np, result.file_path)
    print(f"take {datetime.now() - time_old} to detect image")
    result = await loop.run_in_executor(detect_process_pool, result_processing, img, det_result)

    return result


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

    temp = {}

    print(model.names)

    for i in result:
        print(i.plot())  # show image!
        for j in i.boxes:
            index = int(j.cls)
            name = model.names[index]
            conf = j.conf[0]

            if conf > 0.5:
                if name not in temp:
                    temp[name] = []
                x1, y1, x2, y2 = j.xyxy[0]
                img_copy = img.copy()
                img_draw = ImageDraw.Draw(img_copy)
                img_draw.rectangle([(x1, y1), (x2, y2)], outline='red', width=4)

                random_name = uuid.uuid4().hex
                img_copy.save(f"img/{random_name}.jpg")

                temp[name].append(f"img/{random_name}.jpg")

    return list(temp.keys())


@detection_router.post("/upload/pt")
async def upload_pt(db: AsyncDBSession, description: str, version: str,
                    user: User = Depends(token_verify),
                    pt: UploadFile = File(...)):
    if user.level <= 127:
        raise HTTPException(status_code=401, detail='You are not administrator')

    filepath = pt.filename

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
    ffmpeg.input(f"{filename}").filter('fps', fps=30).filter('scale', height='1080', width='-2').output(
        f"{filename}-convert.mp4").run()

    cap = cv2.VideoCapture(f"{filename}-convert.mp4")
    framerate = cap.get(cv2.CAP_PROP_FPS)

    result = {}
    continue_detect = {}
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        results = model(frame, 0.3, verbose=False)

        detect_obj = {}
        for i in results:
            for j in i.boxes:
                conf = j.conf[0]
                if conf > 0.5:
                    index = int(j.cls)
                    name = model.names[index]
                    pos = j.xyxy[0]
                    if name not in detect_obj:
                        detect_obj[name] = []
                    detect_obj[name].append(pos)

        del_list = []

        for key in continue_detect.keys():
            if key not in detect_obj:  # not continue detected the object so remove from it.
                del_list.append(key)

        for i in del_list:
            del continue_detect[i]

        for key in detect_obj.keys():
            if key not in continue_detect:
                continue_detect[key] = 0
            else:
                continue_detect[key] = continue_detect[key] + 1

        for key, value in continue_detect.items():
            if value == int(framerate * limit):
                if key not in result:
                    result[key] = []
                random_name = f"img/{uuid.uuid4().hex}.jpg"

                result[key].append(random_name)

                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                img = Image.fromarray(frame.astype('uint8'))
                img_draw = ImageDraw.Draw(img)

                for x1, y1, x2, y2 in detect_obj[key]:
                    img_draw.rectangle([(x1, y1), (x2, y2)], outline='red', width=4)
                img.save(random_name)

    os.remove(filename)
    # os.remove(f"{filename}-convert.mp4")
    return result


# only support mp4 file
@detection_router.post('/latest/video')
async def detect_video(db: AsyncDBSession, video: UploadFile = File(...)):
    stmt = select(Model).order_by(Model.update_date.desc()).limit(1)
    result = (await db.execute(stmt)).scalars().first()
    model = YOLO(result.file_path, task='detect')

    contents = await video.read()

    filename = f"temp/{uuid.uuid4().hex}"

    async with aiofiles.open(filename, 'wb') as output_file:
        await output_file.write(contents)

    time_old = datetime.now()
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(detect_process_pool, video_processing, model, filename)
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


# The code to implement the

# GOOGLE API KEY
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
BASE_URL = "https://generativelanguage.googleapis.com"

genai.configure(api_key=GOOGLE_API_KEY)

chat_session = None
lock = asyncio.Lock()


# If ingredients change, server will need to restart to update the chat session
async def get_chat_session(ingredients):
    async with lock:
        global chat_session
        if chat_session is None:
            await run_in_threadpool(init_session, ingredients)
        return copy.deepcopy(chat_session)


def init_session(ingredients):
    global chat_session

    generation_config = {
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 8192,
        "response_schema": content.Schema(
            type=content.Type.OBJECT,
            properties={
                "result": content.Schema(
                    type=content.Type.ARRAY,
                    items=content.Schema(
                        type=content.Type.STRING,
                    ),
                ),
            },
        ),
        "response_mime_type": "application/json",
    }

    model = genai.GenerativeModel(
        model_name="gemini-1.5-pro",
        generation_config=generation_config,
        system_instruction="Detect food in image (but not text) and map to the name I provided.",
    )

    history = [
        {
            "role": "user",
            "parts": [
                "Detect these shape of food which is on the list " + str(
                    ingredients) + "on these images down below, ,than map the detected ingredients to the name i provided as an array with field name \"result\". "
            ],
        },
    ]

    chat_session = model.start_chat(
        history=history
    )


# This function only supports .jpg or .png files,
# and if the file is not a .jpg or .png file, it will return None
# Why rein
# TODO: make it async call
def upload2gemini(path):
    # Using Pillow to check if the file is a .jpg or .png file
    try:
        with PIL.Image.open(path) as img:
            if img.format not in ['JPEG', 'PNG']:
                raise HTTPException(status_code=415, detail='This endpoint only support jpg or png file')
    except PIL.UnidentifiedImageError:
        return None

    size_of_file = os.path.getsize(path)

    headers = {
        'X-Goog-Upload-Protocol': 'resumable',
        'X-Goog-Upload-Command': 'start',
        'Content-Type': 'application/json',
        'X-Goog-Upload-Header-Content-Length': str(size_of_file),  # header only support str, not int
    }

    params = {
        'key': GOOGLE_API_KEY,
    }

    filename = os.path.basename(path)

    data = "{'file': {'display_name': '" + filename + "'}}"

    response = requests.post(
        f'{BASE_URL}/upload/v1beta/files',
        params=params,
        headers=headers,
        data=data
    )

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Error when upload image to gemini server. details: " + response.text)

    upload_url = response.headers["x-goog-upload-url"]

    headers = {
        'X-Goog-Upload-Offset': '0',
        'X-Goog-Upload-Command': 'upload, finalize',
        'Content-Type': 'application/x-www-form-urlencoded',
    }

    with open(path, 'rb') as f:
        data = f.read()

    res = requests.post(f'{upload_url}', headers=headers, data=data).json()['file']
    args = {
        'name': res['name'],
        'display_name': res['displayName'],
        'mime_type': res['mimeType'],
        'sha256_hash': res['sha256Hash'],
        'size_bytes': res['sizeBytes'],
        'state': res['state'],
        'uri': res['uri'],
        'create_time': res['createTime'],
        'expiration_time': res['expirationTime'],
        'update_time': res['updateTime']
    }
    return genai.types.File(args)

def detect_files(session,file,ingredients_sets):
    response = session.send_message(file)
    output = json.loads(response.text)
    result = []

    # ensure all the ingredients in output are on the set of ingredients
    for i in output['result']:
        if i in ingredients_sets:
            result.append(i)
        else:
            print(f"Warning: {i} is not in the list of ingredients.")

    return result

# TODO: depends on get_chat_session with auto fetching ingredients list
@detection_router.post("/gemini")
async def detect_by_gemini(files:List[UploadFile] = File(...)):
    ingredients = ['asparagus', 'avocado', 'bamboo_shoots', 'beans_green', 'beetroot', 'cassava', 'chayote', 'cinnamon',
                   'coriander', 'corn', 'egg', 'bean_mung', 'cabbage_napa', 'carrot', 'chicken', 'crab', 'garlic',
                   'mint', 'pepper_bell', 'potato', 'chili', 'eggplant', 'gourd_bitter', 'gourd_bottle',
                   'gourd_pointed', 'ham', 'jackfruit', 'lemon', 'mushroom_enoki', 'onion', 'pork', 'potato_sweet',
                   'rice', 'almond', 'apple', 'artichoke', 'banana', 'blueberry', 'broccoli', 'broccoli_white',
                   'mustard_greens', 'spinach', 'turnip', 'butter', 'cheese', 'milk', 'pasta', 'strawberry',
                   'ash_gourd', 'beans_red', 'bokchoy', 'bread', 'brocolli_chinese', 'cabbage', 'cucumber', 'edamame',
                   'fish', 'mushroom', 'noodle', 'okra', 'oyster', 'pumpkin', 'radish', 'seaweed', 'taro', 'tomato',
                   'tomato_cherry', 'clam', 'burdock', 'peanut', 'spinach_water', 'leek', 'gourd_sponge', 'salmon',
                   'apple_wax', 'chives', 'coconut', 'dragon_fruit', 'duck', 'durian', 'frog', 'ginger', 'grape',
                   'guava', 'heim', 'kiwi', 'lettuce', 'mango', 'melon_water', 'orange', 'papaya', 'passion_fruit',
                   'pineapple', 'potato_leaves', 'prawn', 'spinach_chinese', 'squid', 'tofu', 'zuccini', 'bean_green',
                   'beef', 'melon_winter', 'lamb', 'lime', 'bean_sprout', 'tofu_dried', 'tofu_skin', 'ketchup',
                   'truffle_sauce', 'miso', 'mayonnaise', 'scallop', 'oats', 'lotus_seed', 'goji', 'jujube', 'quinoa',
                   'tomato_paste', 'tomato_can', 'sesame_sauce', 'century_egg', 'baby_corn', 'chili_bean_sauce',
                   'basil', 'thyme', 'stokvis', 'sweet_bean_sauce', 'shallot', 'curry', 'yogurt', 'celery', 'stock',
                   'sesame', 'soy_sauce', 'lobster', 'crabstick', 'tofu_puff', 'honey', 'yam', 'matcha', 'bean_soy',
                   'kimchi', 'sugar_brown', 'egg_salted', 'bacon', 'cream_whip', 'tuna_can', 'paprika',
                   'worcestershire_sauce', 'star_anise', 'tsaoko', 'clove', 'sichuan_pepper', 'lotus_root',
                   'dried_shrimp', 'sesame_oil', 'mirin', 'sake', 'oyster_sauce', 'chinese_sauerkraut', 'chestnut',
                   'shaoxing_wine', 'Chinese_spirits', 'bay_leaf', 'red_wine', 'konjac', 'fish_sauce', 'ginseng',
                   'dried_clove_fish', 'bottle_gourd', 'dried_orange_peel', 'dry_beancurd_shreds', 'shacha_sauce',
                   'pasta_sauce', 'rice_cake', 'flour', 'gochujang_sause', 'rice-wine', 'rosemary', 'bockwurst',
                   'indian_buead', 'euryale_seed', 'coix_seed', 'chinese_angelica', 'longan', 'whisky', 'yeast',
                   'sichuan_lovage_rhizome', 'radix_astragali', 'cmnamomi_mmulus', 'blood', 'nutmeg', 'dumpling_skin',
                   'black_garlic', 'drinking_yogurt']
    session = await get_chat_session(ingredients)

    upload_coroutine = []

    for file in files:
        random_name = uuid.uuid4().hex
        async with aiofiles.open(f"./img/{random_name}", 'wb') as output_file:
            await output_file.write(await file.read())
        upload_coroutine.append(run_in_threadpool(upload2gemini, f"./img/{random_name}"))

    upload_files = await asyncio.gather(*upload_coroutine)

    response = await run_in_threadpool(detect_files,session,upload_files,set(ingredients))
    return response


# TODO: make it admin only.
@detection_router.post("/gemini/reset")
async def reset_chat_session():
    global chat_session
    async with lock:
        chat_session = None
    return {'message': 'Reset success'}