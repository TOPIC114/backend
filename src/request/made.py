from typing import List

from pydantic import BaseModel


class MadeUpdate(BaseModel):
    rid: int
    iid: int
    main: bool

class MadeDelete(BaseModel):
    rid: int
    iid: int
