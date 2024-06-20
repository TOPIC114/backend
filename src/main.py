import logging

from fastapi import FastAPI, APIRouter

from detect import detection_router
from made import m_router
from sql_app.ingredient import i_router
from test import test_router
from user import user_root
from recipe import recipe_root

logging.basicConfig(level=logging.DEBUG)
app = FastAPI()
router = APIRouter()


@router.get("/")
async def root():
    return {"message": "Hello World"}


@router.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}


app.include_router(router)
app.include_router(test_router)
app.include_router(user_root)
app.include_router(recipe_root)
app.include_router(detection_router)
app.include_router(i_router)
app.include_router(m_router)
