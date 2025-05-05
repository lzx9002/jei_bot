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