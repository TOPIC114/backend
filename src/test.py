from fastapi import APIRouter

test_router = APIRouter()


@test_router.get('/test/')
async def hello_world():
    return {'hello': 'world'}
