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

def extract_numbers_sub(s: str) -> str:
    return re.sub(r'\D', '', s)

async def ai(message: str, session: ClientSession) -> dict:
    system_prompt = (
        "你是一个在QQ群里反黄推的人工智能，用户稍后发送过来的信息便是QQ群中用户发送的信息，如果你认为用户发的信息有不良的意思（涉黄，擦边等）或存在引流推广，那么请返回true，否则返回false，自动化程序将根据你的回答决定是否撤回和禁言，不要输出其他的！！！\n"
        "下面是容易被忽略的例子“女大”“女高”“约炮”等具有隐性的暗示\n"
        "例子：“女大交流群：123456789“,”少萝照分享“‘\n"
        "“少萝闺蜜分享照”这段文本是否含有色情内容,\"is_pornographic\": true/false\n"
    )
    headers = {"Authorization": "Bearer sk-rvitzpixehecvqxxrdipetjnzcxobqjvwbepkveudexesgkn", "Content-Type": "application/json"}
    payload = {
        "model": "deepseek-ai/DeepSeek-V3",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ],
        "stream": False,
        "stop": None,
        "response_format": {"type": "json_object"},
    }
    try:
        async with session.post("https://api.siliconflow.cn/v1/chat/completions", json=payload, headers=headers) as response:
            data = await response.json()
            return json.loads(data["choices"][0]["message"]["content"])
    except Exception as e:
        # 异常时返回默认值，认为不是不良内容
        return {"is_pornographic": False, "error": str(e)}

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