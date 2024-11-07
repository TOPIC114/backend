from typing import List

from pydantic import BaseModel

class CommentResponse(BaseModel):
    username :str
    content :str
    score : int

class RecipeInfoResponse(BaseModel):
    title: str
    description: str
    video: str
    rtype: str
    score: float|None
    comments :List[CommentResponse]
    iids :List[int]


class RecipeSearchResponse(BaseModel):
    rid :int # recipe id
    title :str # title
    link :str
    score :float|None

