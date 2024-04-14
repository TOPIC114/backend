from pydantic import BaseModel


class RecipeInfoResponse(BaseModel):
    id: int
    name: str
    description: str
    video_link: str
    rtype: int


class SearchRecipeResponse(BaseModel):
    recipes: list[RecipeInfoResponse]
