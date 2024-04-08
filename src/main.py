import logging

from fastapi import FastAPI, APIRouter

from test import test_router
from user import user_root

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
