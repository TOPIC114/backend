from typing import Generator, Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from . import database_uri

async_engine = create_async_engine(
    database_uri, pool_pre_ping=True
)

async_session_factory = async_sessionmaker(
    autocommit=False, autoflush=False, bind=async_engine
)


async def get_async_session() -> AsyncSession:
    async with async_session_factory() as session:
        yield session

AsyncDBSession = Annotated[AsyncSession, Depends(get_async_session)]
