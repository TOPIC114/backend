from pydantic import BaseModel


class UserInfoResponse(BaseModel):
    username: str
    email: str
    level: int

    model_config = {
        "json_schema_extra": {
            "example": {
                "username": "bloodnighttw",
                "email": "bbeenn1227@gmail.com",
                "level": 1
            }
        }
    }
