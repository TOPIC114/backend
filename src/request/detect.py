from pydantic import BaseModel


class PTInfo(BaseModel):
    description: str
    version: str
