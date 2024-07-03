from pydantic import BaseModel


class ChangeNameRequest(BaseModel):
    iid: int
    name: str