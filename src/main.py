import logging

from fastapi import FastAPI, APIRouter

from sql_app import engine
from sql_app.utils import create_tables, db_logger
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


# Create database column after startup (all module are loaded)
@app.on_event("startup")
async def startup():
    db_logger.info("Creating tables")
    create_tables(engine)


app.include_router(router)
app.include_router(test_router)
