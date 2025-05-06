# -*- coding: utf-8 -*-
# @Project : jei_bot
# @File    : module.py
# @IDE     : PyCharm
# @Author  : lzx9002
# @Time    : 2025/4/6 14:25
import json
import ssl
from io import BytesIO
from typing import TypedDict, Literal

import aiohttp
from aiohttp import ClientSession


async def fetch_image_from_url_ssl(url: str, session: ClientSession) -> BytesIO | None:

    SSL_CONTEXT = ssl.create_default_context()
    SSL_CONTEXT.set_ciphers("DEFAULT")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    }
    async with session.get(url, ssl=SSL_CONTEXT, headers=headers) as response:
        if response.status == 200:
            image_data = BytesIO(await response.read())
            return image_data
        return None
def count_digits_generator(s: str, min_digits: int=4):
    return sum(1 for char in s if char.isdigit()) >= min_digits

async def ai(message: str, group_name: str, session: ClientSession) -> dict[Literal["is_pornographic"], bool]:
    headers={"Authorization": f"Bearer sk-rvitzpixehecvqxxrdipetjnzcxobqjvwbepkveudexesgkn","Content-Type": "application/json"}
    payload = {
        "model": "deepseek-ai/DeepSeek-V3",
        "messages": [
            {
                "role": "system",
                "content": f"\"{message}\"帮我判断是不是色情内容(嫖娼广告等),数字为群号，群号搜索到的群名称是\"{group_name}\",返回{{\"is_pornographic\": true/false}}]"
            }
        ],
        "stream": False,
        "stop": None,
        "response_format": {"type": "json_object"},
    }
    async with session.post("https://api.siliconflow.cn/v1/chat/completions", json=payload, headers=headers) as response:
        # data = await response.read()
        data = await response.json()
        return json.loads(data["choices"][0]["message"]["content"])

# class aiReturn(TypedDict):


