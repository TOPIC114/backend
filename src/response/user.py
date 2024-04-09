from pydantic import BaseModel


class UserInfoResponse(BaseModel):
    id: int
    username: str
    email: str
    level: int
