from pydantic import BaseModel


class RecipeUpload(BaseModel):
    name: str
    description: str
    video_link: str = None
    rtype: int = None


class RecipeSearch(BaseModel):
    keyword: str


class RecipeContent(RecipeUpload):
    author: str
