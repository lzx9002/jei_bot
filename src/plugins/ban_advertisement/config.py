from pydantic import BaseModel


class Config(BaseModel):
    """Plugin Config Here"""
    group_id: list[int] = []
    test_user: list[int] = []
    mysql_host: str = ""
    mysql_port: int = 3306
    mysql_user: str = ""
    mysql_password: str = ""
    mysql_database: str = ""
    mysql_table: str = ""
