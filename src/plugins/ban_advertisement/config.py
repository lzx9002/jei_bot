from pydantic import BaseModel
from typing import Union


class Config(BaseModel):
    """Plugin Config Here"""
    group_id: list[int] = []
    ban_time: list[Union[int, bool]] = [1,30,True]
