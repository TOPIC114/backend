from pydantic import BaseModel


class RecipeUpload(BaseModel):
    name: str
    description: str
    video_link: str = None
    rtype: int = None
    main_iids: list[int]
    sub_iids: list[int]


class RecipeSearch(BaseModel):
    keyword: str


class RecipeTypeRequest(BaseModel):
    name: str

class CommentCreate(BaseModel):
    rid: int
    content:str
    rate:int