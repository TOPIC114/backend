from fastapi import APIRouter
from sqlalchemy.orm import Session

from sql_app import engine, SessionLocal
from sql_app.model.User import User

test_router = APIRouter()


@test_router.get('/test/user/write/{name}')
async def write_test_user(name:str):
    db: Session = SessionLocal(bind=engine)
    user = User(name=name, level=5)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@test_router.get('/test/user/read')
async def read_test_user_100():
    db: Session = SessionLocal(bind=engine)
    return db.query(User).limit(100).all()
