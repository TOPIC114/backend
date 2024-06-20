from typing import List

from pydantic import BaseModel


class MadeUpload(BaseModel):
    rid: int
    iid: int


class MadeUploadList(BaseModel):
    rid: int
    iids: List[int]