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
    author :str # author name
    description :str # description
    rtype : str # rtype name