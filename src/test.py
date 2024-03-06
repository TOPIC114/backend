from fastapi import APIRouter

router = APIRouter()

@router.get('/test/')
async def hello_world():
    return {'hello': 'world'}