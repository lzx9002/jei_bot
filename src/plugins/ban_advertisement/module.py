# -*- coding: utf-8 -*-
# @Project : jei_bot
# @File    : module.py
# @IDE     : PyCharm
# @Author  : lzx9002
# @Time    : 2025/4/6 14:25
import ssl
from datetime import datetime
from enum import Enum
from io import BytesIO

import aiohttp
from aiomysql import create_pool, DictCursor


async def fetch_image_from_url_ssl(url: str, **params) -> BytesIO | None:

    SSL_CONTEXT = ssl.create_default_context()
    SSL_CONTEXT.set_ciphers("DEFAULT")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url, **params, ssl=SSL_CONTEXT) as response:
            if response.status == 200:
                image_data = BytesIO(await response.read())
                return image_data
            return None




class LogLevel(Enum):
    INFO = 'INFO'
    WARNING = 'WARNING'
    ERROR = 'ERROR'

class log:
    def __init__(self, config, plugin_config):
        self.config = config
        self.plugin_config = plugin_config

    async def init(self, test_user: list[int]):
        pool = await create_pool(
            host=self.plugin_config.mysql_host,
            port=self.plugin_config.mysql_port,
            user=self.plugin_config.mysql_user,
            password=self.plugin_config.mysql_password,
            db=self.plugin_config.mysql_database,
            charset="utf8"
        )
        self.config.pool = pool
        self.test_user = test_user

    async def log(self, level: LogLevel, group_id: int, message: str, user_id: int=None, url: str=None):
        if user_id in self.test_user:
            return
        async with self.config.pool.acquire() as conn:
            async with conn.cursor(DictCursor) as cursor:
                await cursor.execute(f"insert into {self.plugin_config.mysql_table} (time, level, group_id, msg, url) value ('{datetime.now()}', '{level.value}', {group_id}, '{message}', '{url}')")
                await conn.commit()

    async def info(self, group_id: int, message: str, user_id: int=None, url: str=None):
        await self.log(LogLevel.INFO, group_id, message, user_id, url)

    async def warning(self, group_id: int, message: str, user_id: int=None, url: str=None):
        await self.log(LogLevel.WARNING, group_id, message, user_id, url)

    async def error(self, group_id: int, message: str, user_id: int=None, url: str=None):
        await self.log(LogLevel.ERROR, group_id, message, user_id, url)