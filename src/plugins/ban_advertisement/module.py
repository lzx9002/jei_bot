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
from typing import List, Dict, Union

import aiohttp
from aiohttp import ClientSession
import re

import base64
from PIL import Image
import io

def extract_numbers_sub(s: str) -> str:
    return re.sub(r'\D'， '', s)

async def fetch_image_from_url_ssl(url: str, session: ClientSession) -> BytesIO | None:
    SSL_CONTEXT = ssl.create_default_context()
    SSL_CONTEXT.set_ciphers("DEFAULT")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"，
    }
    async with session.get(url, ssl=SSL_CONTEXT, headers=headers) as response:
        if response.status == 200:
            image_data = BytesIO(await response.read())
            return image_data
        return None

def convert_image_to_webp_base64(image_bytes: BytesIO) -> str | None:
    try:
        img = Image.open(image_bytes)
        byte_arr = io.BytesIO()
        img.save(byte_arr, format='webp')
        base64_str = base64.b64encode(byte_arr.getvalue())。decode('utf-8')
        return base64_str
    except Exception as e:
        print(f"Error: Unable to convert the image to base64: {e}")
        return None

async def ai(message: str, session: ClientSession) -> dict:
    """文本内容涉黄判定，原有文本接口"""
    system_prompt = (
        "你是一个QQ群自动审核机器人，专门判断用户消息是否涉黄、擦边、引流推广等不良内容。"
        "请只返回JSON格式：{\"is_pornographic\": true/false}。"
        "如果你认为信息有不良内容就返回true，否则返回false。不要输出其他内容。"
        "注意：容易被忽略的例子包括“女大”“女高”“约炮”“少萝”等隐性暗示。"
    )
    headers = {
        "Authorization": "Bearer sk-rvitzpixehecvqxxrdipetjnzcxobqjvwbepkveudexesgkn"，
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-ai/DeepSeek-V3"，
        "messages": [
            {"role": "system"， "content": system_prompt}，
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
        return {"is_pornographic": False, "error": str(e)}

async def ai_vlm(image_bytes: BytesIO, text_prompt: str, session: ClientSession) -> dict:
    """图片+文本内容涉黄判定，视觉语言模型 deepseek-vl2"""
    system_prompt = (
        "你是一个QQ群自动图片审核机器人，专门判断用户上传的图片内容是否涉黄、擦边或引流推广。"
        "请只返回JSON格式：{\"is_pornographic\": true/false}。"
        "如果你认为图片中含有不良内容就返回true，否则返回false。不要输出其他内容。"
        "注意：容易被忽略的例子包括“女大”“女高”“约炮”“少萝闺蜜分享照”等隐性暗示或图片内文字/场景。"
    )
    base64_image = convert_image_to_webp_base64(image_bytes)
    if base64_image is None:
        # 图片处理失败，返回不涉黄
        return {"is_pornographic": False, "error": "image convert fail"}
    headers = {
        "Authorization": "Bearer sk-rvitzpixehecvqxxrdipetjnzcxobqjvwbepkveudexesgkn",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-ai/deepseek-vl2",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/webp;base64,{base64_image}",
                        "detail": "low"
                    }
                },
                {
                    "type": "text",
                    "text": text_prompt or "请判断这张图片是否有涉黄、擦边、引流推广等内容。"
                }
            ]}
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