# -*- coding: utf-8 -*-
# @Project : jei_bot
# @File    : module.py
# @IDE     : PyCharm
# @Author  : lzx9002
# @Time    : 2025/4/6 14:25
import json
import ssl
from argparse import ArgumentParser
from io import BytesIO
from shlex import split
from typing import TypedDict, Literal, List, Dict, Union

import aiohttp
from aiohttp import ClientSession
import re


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

# def extract_numbers_sub(s: str) -> str:
#     return re.sub(r'\D', '', s)

async def ai(session: ClientSession, msg: str="") -> str:
    headers={"Authorization": f"Bearer sk-qpudsdvlvjjrxjitdbbmssfpjdskxunwozcliseuyepryttz","Content-Type": "application/json"}
    messages = [
        {
            "role": "system",
            "content": "你是一个鉴黄机器人,你的任务是当用户输入内容(图片，文字等)含有色情内容(露出隐私部位,嫖娼,卖淫广告链接等)时严格输出小写true,否则输出小写false不要输出其他内容."
        },
        {
            "role": "user",
            "content": msg
        }
    ]
    payload = {
        "model": "deepseek-ai/DeepSeek-V3",
        "messages": messages,
        "stream": False,
        "stop": None,
        "response_format": {"type": "text"},
    }
    async with session.post("https://api.siliconflow.cn/v1/chat/completions", json=payload, headers=headers) as response:
        # data = await response.read()
        data = await response.json()
        return data["choices"][0]["message"]["content"]

def parsing(x: str, a: List[str], k: List[str]) -> Dict[str, Union[List, Dict]]:
    parser = ArgumentParser()
    for arg in a:
        parser.add_argument(arg, action='store_true', dest=arg)
    for kwarg in k:
        parser.add_argument(kwarg, type=str, nargs='?', dest=kwarg, default=None)
    parser.add_argument('command', type=str)
    parser.add_argument('other_args', type=str, nargs='*')
    args_namespace, unknown = parser.parse_known_args(split(x))
    return {
        "command": args_namespace.command,
        "args": [args_namespace.command] + args_namespace.other_args,
        "kwargs": {k: getattr(args_namespace, k) for k in k if getattr(args_namespace, k) is not None}
    }

def extract_numbers_sub(s: str) -> int:
    return int(''.join([i if i.isdigit() else "" for i in s]))