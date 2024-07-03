from pydantic import BaseModel


class ChangeNameRequest(BaseModel):
    iid: int
    name: str


class AddSubIngredient(BaseModel):
    iid: int
    name: str
    mandarin: str
