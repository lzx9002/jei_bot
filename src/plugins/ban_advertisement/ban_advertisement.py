# -*- coding: utf-8 -*-
# @Project : jei_bot
# @File    : ban_advertisement.py
# @IDE     : PyCharm
# @Author  : lzx9002
# @Time    : 2025/4/6 13:53
import asyncio
import json
import re
import traceback
from datetime import datetime
from shlex import split
from typing import Union, Iterable, Any

import aiohttp
from aiohttp import ClientSession
from nonebot.exception import AdapterException
from nonebot.internal.rule import Rule
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER
from nonebot.rule import to_me
from pyzbar.pyzbar import decode, Decoded
from PIL import Image
from nonebot.plugin.on import on_message, on_command, on_notice, on
from nonebot.adapters.onebot.v11 import Bot as V11Bot, GroupMessageEvent, GroupRecallNoticeEvent, GROUP_MEMBER, Event, \
    PrivateMessageEvent, NoticeEvent, GROUP_ADMIN, GROUP_OWNER, ActionFailed
from nonebot.adapters.onebot.v11.message import Message, MessageSegment

from .config import Config
from .module import fetch_image_from_url_ssl, extract_numbers_sub, ai
from nonebot import require, get_driver, get_plugin_config, get_bot, logger
from nonebot.log import default_format, default_filter

require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler
require("nonebot_plugin_localstore")
import nonebot_plugin_localstore as store

config = get_plugin_config(Config)
driver = get_driver()
ban_logger = logger.bind(ban=True)
aiohttp_session: ClientSession
data_file = store.get_plugin_data_file("key.txt")

data = {
    "user_status": {}
}

key: list = []

@driver.on_startup
async def startup():
    global aiohttp_session
    aiohttp_session = aiohttp.ClientSession()

    global key
    with data_file.open(mode="r", encoding="utf-8") as f:
        key = f.read().splitlines()

    logger.add("log/log_{time:YYYY-MM-DD}.log", level=0,
               format=default_format, rotation="2 days", retention="3 weeks", enqueue=True, filter=lambda record: not "ban" in record["extra"] and default_filter(record))
    logger.add("log/ban/log_{time:YYYY-MM-DD}.log", level=0,
               format=default_format, rotation="2 days", retention="3 weeks", enqueue=True, filter=lambda record: "ban" in record["extra"] and default_filter(record))

@driver.on_shutdown
async def shutdown():
    global aiohttp_session
    await aiohttp_session.close()

def is_allowed_group(group: Iterable) -> Rule:
    async def check_group(bot: V11Bot, event: Event) -> bool:
        return event.group_id in group
    return Rule(check_group)
def Having_title(no_cache=False) -> Rule:
    async def title(bot: V11Bot, event: GroupMessageEvent) -> bool:
        group_member_title=await bot.get_group_member_info(group_id=event.group_id,user_id=event.user_id,no_cache=no_cache)
        return not bool(group_member_title["title"])
    return Rule(title)

message = on_message(rule=is_allowed_group(config.group_id) & Having_title(), permission=GROUP_MEMBER, priority=100, block=False)

@message.handle()
async def _(event: GroupMessageEvent, bot: V11Bot):
    # 本地检测
    status = tuple(await asyncio.gather(
        img(event.message["image"]),
        qun_share(event.message["json"]),
        text_msg(event.message["text"])
    ))

    # AI判定：异常也兜底
    try:
        ai_result = await ai(event.get_plaintext(), aiohttp_session)
        ai_bad = ai_result.get("is_pornographic", False)
    except Exception as e:
        ai_bad = False
        ban_logger.warning(f"AI接口异常: {e}")

    # 合并判定：只要AI或本地有一个为True就处罚
    is_bad = ai_bad or any(status)

    if not is_bad:
        return

    # 撤回违规消息
    await bot.delete_msg(message_id=event.message_id)
    data["user_status"][event.user_id] = data["user_status"].get(event.user_id, 0) + 1

    ban_time_value = (
        config.ban_time[data["user_status"][event.user_id]-1]
        if event.user_id in data["user_status"]
        else None
    )
    if ban_time_value is True:
        send_msg = message.send(Message([
            MessageSegment.text("用户"),
            MessageSegment.at(event.user_id),
            MessageSegment.text(f"({event.user_id})警告多次无效，执行纪律")
        ]))
        ban_user = bot.set_group_kick(group_id=event.group_id, user_id=event.user_id, reject_add_request=True)
        await asyncio.gather(send_msg, ban_user)
        del data["user_status"][event.user_id]
        ban_logger.info(f"踢出用户{event.user_id} 来自群:{event.group_id}")
    elif ban_time_value:
        send_msg = message.send(Message([
            MessageSegment.text("用户"),
            MessageSegment.at(event.user_id),
            MessageSegment.text(f"({event.user_id})违反发言规则,警告{data['user_status'][event.user_id]}次")
        ]))
        ban_user = bot.set_group_ban(group_id=event.group_id, user_id=event.user_id, duration=ban_time_value*60)
        await asyncio.gather(send_msg, ban_user)
        ban_logger.info(f"警告用户{event.user_id} 来自群:{event.group_id}")

async def img(image: Message) -> bool:
    for i in image:
        img_bytesio = await fetch_image_from_url_ssl(i.data["url"], aiohttp_session)
        result: list[Decoded] = decode(Image.open(img_bytesio))
        return bool(result)
    return False

async def qun_share(json_card: Message) -> bool:
    for i in json_card:
        return json.loads(i.data["data"])["bizsrc"] == "qun.share"
    return False

async def text_msg(text: Message) -> bool:
    # 本地关键词判定
    local_bad = any(substring in text.extract_plain_text() for substring in key)
    if local_bad:
        return True
    # AI判定
    try:
        ai_result = await ai(text.extract_plain_text(), aiohttp_session)
        return ai_result.get("is_pornographic", False)
    except Exception as e:
        ban_logger.warning(f"AI接口异常: {e}")
        return False

add_key = on_command("添加关键词", rule=is_allowed_group(config.group_id) & to_me(), permission=GROUP_OWNER | GROUP_ADMIN | SUPERUSER, priority=50, block=False)

@add_key.handle()
async def _(event: GroupMessageEvent, bot: V11Bot, args: Message = CommandArg()):
    add_keys=split(args.extract_plain_text())
    try:
        global key
        error = []
        for i in add_keys:
            if i in key:
                add_keys.remove(i)
                error.append(i)
        with data_file.open(mode="a+", encoding="utf-8") as f:
            f.writelines([i+"\n" for i in add_keys])
        with data_file.open(mode="r", encoding="utf-8") as f:
            key = f.read().splitlines()
        if error:
            raise KeyError(f"关键词{','.join(error)}已存在")
    except Exception as e:
        await add_key.finish(Message([
            MessageSegment.reply(event.message_id),
            MessageSegment.at(event.user_id),
            MessageSegment.text(f"添加关键词失败:\n{type(e).__name__}: {str(e)}")
        ]))
    else:
        await add_key.finish(Message([
                MessageSegment.reply(event.message_id),
                MessageSegment.at(event.user_id),
                MessageSegment.text(f"成功添加关键词{','.join(add_keys)}")
        ]))

# ... 其余管理命令和定时任务部分保持原样 ...
@scheduler.scheduled_job("cron", hour=7, minute=0, second=0,)
async def clear_guoup():
    data["user_status"].clear()
    for i in config.group_id:
        ban_logger.info(f"操作执行 -重置群数据 来自 [群:{i}]")