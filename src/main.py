import os

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from detect import detection_router
from ingredient import i_router
from made import made_root
from user import user_root
from recipe import recipe_root
from video import video_root

description = """
# BACKEND

### This is the backend of the project. It provides the API for the frontend to interact with the database and the AI model.

## Implemented Guidelines
1. If the endpoint has a detailed description, you can implement the endpoint directly. Because this type of endpoint
is considered as stable.

2. If the endpoint has no detailed description, you are still able to implement the endpoint, but you should be aware
that the endpoint may change in the future.

3. If the endpoint description said that it's not implemented, you should not implement the endpoint, 
because the endpoint is not implemented in the backend yet.
4. The endpoint that is described as "Token Required" means that the endpoint requires a token to access, you should put 
the token in the header with the key name `X-API-Key`.

5. The endpoint that is described as "Admin Only" means that the endpoint requires the user to have the admin permission 
level to access, so you should also put the token in the header with the key name 'X-API-Key'. The admin permission 
level is 128.

6. The endpoint that is described as "Stuffs" means that the endpoint is not implemented yet or only can be accessed by 
admin, but it will be implemented in the future.

7. The endpoint under /video is only for inner use, so you should not implement the endpoint under /video.

## Note
FastAPI is using the OpenAPI standard, so you can use this Swagger UI to interact with the API.

You can also generate the client code from the OpenAPI standard, so you can use the client code to interact with the API.


### That's all the guidelines for now. If you have any questions, please ask in line/discord.

"""


app = FastAPI(
    description=description,
)

app.include_router(user_root)
app.include_router(recipe_root)
app.include_router(detection_router)
app.include_router(i_router)
app.include_router(video_root)
app.include_router(made_root)

origins = [
    "http://localhost",
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs('img', exist_ok=True)
app.mount("/img", StaticFiles(directory="img"), name="img")
