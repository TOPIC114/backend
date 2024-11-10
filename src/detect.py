import asyncio
import copy
import json
import logging
import os
import uuid
from typing import List

import PIL
import aiofiles
import google.generativeai as genai
import aiohttp
from PIL import Image
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks
from google.ai.generativelanguage_v1beta.types import content
from sqlalchemy import select
from starlette.concurrency import run_in_threadpool

from sql_app.db import AsyncDBSession
from sql_app.model.Recipe import Ingredient


detection_router = APIRouter(prefix="/detect", tags=['detect'])

# GOOGLE API KEY
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
BASE_URL = "https://generativelanguage.googleapis.com"

genai.configure(api_key=GOOGLE_API_KEY)

chat_session = None
list_of_i = []
ingredients_set = set()
lock = asyncio.Lock()

logger = logging.getLogger(__name__)


# If ingredients change, server will need to restart to update the chat session
async def get_chat_session(db:AsyncDBSession):

    async with lock:
        global chat_session, list_of_i, ingredients_set

        result = await db.execute(select(Ingredient.name))
        ingredients = [i.name for i in result]

        if list_of_i != ingredients:
            logger.debug("Ingredients changed or not inited.")
            chat_session = None  # reset chat session
            list_of_i = ingredients
            ingredients_set = set(ingredients)
        if chat_session is None:
            await run_in_threadpool(init_session, ingredients)
        return copy.deepcopy(chat_session)


def init_session(ingredients):
    global chat_session

    logger.debug("Init chat session with ingredients: %s", ingredients)

    generation_config = {
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 8192,
        "response_schema": content.Schema(type=content.Type.OBJECT, properties={
            "result": content.Schema(type=content.Type.ARRAY,items=content.Schema(type=content.Type.STRING)),
        }),
        "response_mime_type": "application/json",
    }

    model = genai.GenerativeModel(model_name="gemini-1.5-pro", generation_config=generation_config,
                                  system_instruction="Detect food in image (but not text) and map to the name I provided.", )

    history = [{
        "role": "user",
        "parts": [
            "Detect these shape of food which is on the list " +
            str(ingredients) + " on these images down below," +
            "than map the detected ingredients to the name i provided as an array with field name \"result\". "
        ],
    }]

    chat_session = model.start_chat(history=history)


# This function only supports .jpg or .png files,
# and if the file is not a .jpg or .png file, it will
async def upload2gemini(path):
    # Using Pillow to check if the file is a .jpg or .png file

    try:
        with PIL.Image.open(path) as img:
            if img.format not in ['JPEG', 'PNG']:
                raise HTTPException(status_code=415, detail='This endpoint only support jpg or png file')
    except PIL.UnidentifiedImageError:
        raise HTTPException(status_code=415, detail='We can\'t recognize the file type')

    size_of_file = os.path.getsize(path)

    headers = {
        'X-Goog-Upload-Protocol': 'resumable',
        'X-Goog-Upload-Command': 'start',
        'Content-Type': 'application/json',
        'X-Goog-Upload-Header-Content-Length': str(size_of_file) # header only support str, not int
    }

    params = {'key': GOOGLE_API_KEY}

    filename = os.path.basename(path)

    data = "{'file': {'display_name': '" + filename + "'}}"

    # response = requests.post(f'{BASE_URL}/upload/v1beta/files', params=params, headers=headers, data=data)
    async with aiohttp.ClientSession() as session:
        async with session.post(f'{BASE_URL}/upload/v1beta/files', params=params, headers=headers, data=data) as response:
            logger.debug("Init the session to upload image to gemini server response: %s", response.status)
            if response.status != 200:
                raise HTTPException(status_code=response.status,
                                    detail="Error when upload image to gemini server. details: " + str(await response.json()))

        upload_url = response.headers["x-goog-upload-url"]

        headers = {
            'X-Goog-Upload-Offset': '0',
            'X-Goog-Upload-Command': 'upload, finalize',
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        async with aiofiles.open(path, 'rb') as file:
            data = await file.read()

        # res = requests.post(f'{upload_url}', headers=headers, data=data).json()['file']
        async with session.post(f'{upload_url}', headers=headers, data=data) as response:
            logger.debug("Upload image to gemini server with response: %s", response.status)
            if response.status != 200:
                raise HTTPException(status_code=response.status,
                                    detail="Error when upload image to gemini server. details: " + str(await response.json()))
            res = (await response.json())['file']

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


def detect_files(session, file):
    response = session.send_message(file)
    output = json.loads(response.text)
    result = []

    # ensure all the ingredients in output are on the set of ingredients
    for i in output['result']:
        if i in ingredients_set:
            result.append(i)
        else:
            logger.warning(f"{i} is not in the list of ingredients.")

    return result




@detection_router.post("/gemini")
async def detect_by_gemini(background:BackgroundTasks,session = Depends(get_chat_session),files: List[UploadFile] = File(...)) -> List[str]:
    """
    Detect the ingredients in the image by using the gemini API

    :param files: List of images
    """

    logger.info("Detect the ingredients in the image by using the gemini API")

    upload_coroutine = []

    for file in files:
        random_name = uuid.uuid4().hex
        logger.debug("Saving the file with random name: img/%s......", random_name)
        async with aiofiles.open(f"./img/{random_name}", 'wb') as output_file:
            await output_file.write(await file.read())
            logger.debug("Save the file with random name: img/%s", random_name)
        upload_coroutine.append(upload2gemini(f"./img/{random_name}"))

    upload_files = await asyncio.gather(*upload_coroutine)

    response = await run_in_threadpool(detect_files, session, upload_files)
    for i in upload_files:
        logger.debug("Delete the file(%s) in gemini server in background.....", i.name)
        background.add_task(run_in_threadpool,i.delete)

    return response
