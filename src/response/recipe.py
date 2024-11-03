from pydantic import BaseModel


class RecipeInfoResponse(BaseModel):
    id: int
    name: str
    description: str
    video_link: str
    rtype: int


class RecipeSearchResponse(BaseModel):
    rid :int # recipe id
    title :str # title
    link :str
    score :float|None