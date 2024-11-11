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

    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "A fire rice recipe",
                "description": "nothing here",
                "video": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "rtype": "fire rice",
                "score": 4.0,
                "comments": [
                    {
                        "username": "bloodnighttw",
                        "content": "I love this recipe!",
                        "score": 5
                    }
                ],
                "iids": [1, 2, 3]
            }
        }
    }


class RecipeSearchResponse(BaseModel):
    rid :int # recipe id
    title :str # title
    link :str
    score :float|None

