import logging

import uvicorn
from fastapi import FastAPI, APIRouter

from sql_app import Base
from sql_app.db import AsyncDBSession,async_engine
from test import test_router

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


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)