from pydantic import BaseModel


class Config(BaseModel):
    """Plugin Config Here"""
    group_id: list[int] = []
