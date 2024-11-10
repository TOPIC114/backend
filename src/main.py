import logging
import os

from fastapi import FastAPI, APIRouter
from starlette.staticfiles import StaticFiles

from detect import detection_router
from made import m_router
from ingredient import i_router
from user import user_root
from recipe import recipe_root
from video import video_root

logging.basicConfig(level=logging.DEBUG)
app = FastAPI()
router = APIRouter()

app.include_router(router)
app.include_router(user_root)
app.include_router(recipe_root)
app.include_router(detection_router)
app.include_router(i_router)
app.include_router(m_router)
app.include_router(video_root)

os.makedirs('img', exist_ok=True)
app.mount("/img", StaticFiles(directory="img"), name="img")
