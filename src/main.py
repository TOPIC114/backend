import logging

from fastapi import FastAPI

from sql_app import engine
from sql_app.utils import create_tables, db_logger

logging.basicConfig(level=logging.DEBUG)

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}


# Create database column after startup (all module are loaded)
@app.on_event("startup")
async def startup():
    db_logger.info("Creating tables")
    create_tables(engine)

