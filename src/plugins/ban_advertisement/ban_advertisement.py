# -*- coding: utf-8 -*-
# @Project : jei_bot
# @File    : ban_advertisement.py
# @IDE     : PyCharm
# @Author  : lzx9002
# @Time    : 2025/4/6 13:53
# import logging
import asyncio
import json
import re
from datetime import datetime
from typing import Union, Iterable, Any

import aiohttp
from aiohttp import ClientSession
from nonebot.internal.rule import Rule
from nonebot.params import CommandArg
from nonebot.rule import to_me
from pyzbar.pyzbar import decode, Decoded
from PIL import Image
from nonebot.plugin.on import on_message, on_command, on_notice, on
from nonebot.adapters.onebot.v11 import Bot as V11Bot, GroupMessageEvent, GroupRecallNoticeEvent, GROUP_MEMBER, Event, \
    PrivateMessageEvent, NoticeEvent
from nonebot.adapters.onebot.v11.message import Message, MessageSegment

from .config import Config
from .module import fetch_image_from_url_ssl, count_digits_generator, ai
from nonebot import require, get_driver, get_plugin_config, get_bot, logger
from nonebot.log import default_format, default_filter

require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler

config = get_plugin_config(Config)
driver = get_driver()
ban_logger = logger.bind(ban=True)
aiohttp_session: ClientSession

data = {
    "user_status": {}
}

ban_time = [
    None,
    1,
    5,
    60,
    True,
]

@driver.on_startup
async def startup():
    global aiohttp_session
    aiohttp_session = aiohttp.ClientSession()

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


message = on_message(rule=is_allowed_group(config.group_id), permission=GROUP_MEMBER)

@message.handle()
async def _(event: GroupMessageEvent, bot: V11Bot):
    for i in event.message["image"]:
        ban_logger.info(f"图片url -{i.data["url"]} 来自 {event.user_id}@[群:{event.group_id}]")
        img_bytesio = await fetch_image_from_url_ssl(i.data["url"], aiohttp_session)
        img = Image.open(img_bytesio)
        result: list[Decoded] = decode(img)
        if result:
            await bot.delete_msg(message_id=event.message_id)
            data["user_status"][event.user_id] = data["user_status"].get(event.user_id, 0) + 1
            ban_logger.info(f"解析图片url -{i.data["url"]} 来自 {event.user_id}@[群:{event.group_id}]] '{json.dumps([i.data.decode() for i in result])}'")
    for i in event.message["json"]:
        if json.loads(i.data["data"])["bizsrc"] == "qun.share":
            await bot.delete_msg(message_id=event.message_id)
            data["user_status"][event.user_id] = data["user_status"].get(event.user_id, 0) + 1
            ban_logger.info(f"消息 -推荐群聊 来自 {event.user_id}@[群:{event.group_id}]")
    if count_digits_generator(event.message.extract_plain_text()):
        group_name = (await bot.get_group_info(group_id=event.group_id, no_cache=True))["group_name"]
        text_message = event.message.extract_plain_text()
        ban_logger.info(f"消息 -收到 来自 {event.user_id}@[群:{event.group_id}] {text_message}")
        if (await ai(text_message, group_name, aiohttp_session))["is_pornographic"]:
            await bot.delete_msg(message_id=event.message_id)
            data["user_status"][event.user_id] = data["user_status"].get(event.user_id, 0) + 1
            ban_logger.info(f"消息 -确定 来自 {event.user_id}@[群:{event.group_id}] {text_message}")
        # await message.finish(str(count_digits_generator(event.message.extract_plain_text())))

    if ban_time[data["user_status"].get(event.user_id,0)] is True:
        await message.send(Message([
            MessageSegment.text("用户"),
            MessageSegment.at(event.user_id),
            MessageSegment.text(f"({event.user_id})警告多次无效，执行纪律")
        ]))
        await bot.set_group_kick(group_id=event.group_id, user_id=event.user_id, reject_add_request=True)
        del data["user_status"][event.user_id]
        ban_logger.info(f"操作执行 -踢出用户 来自 {event.user_id}@[群:{event.group_id}]")
    elif ban_time[data["user_status"].get(event.user_id,0)]:
        await message.send(Message([
            MessageSegment.text("用户"),
            MessageSegment.at(event.user_id),
            # MessageSegment.text(f"({event.user_id})打广告{data["user_status"][event.user_id]}次,禁言{ban_time[data["user_status"][event.user_id]]}min")
            MessageSegment.text(f"({event.user_id})打广告{data["user_status"][event.user_id]}次")
        ]))
        await bot.set_group_ban(group_id=event.group_id, user_id=event.user_id, duration=ban_time[data["user_status"][event.user_id]]*60)
        # logger.info(f"用户{event.user_id}尝试刷屏{data["user_status"][event.user_id]}次,禁言{ban_time[data["user_status"][event.user_id]]}min")
        ban_logger.info(f"操作执行 -警告用户 来自 {event.user_id}@[群:{event.group_id}]")


# log = on_command("log")
#
# @log.handle()
# async def _(event: PrivateMessageEvent, bot: V11Bot, age: Message = CommandArg()):
#     age = age.extract_plain_text().split(" ")[0:1]
#     with open("log/log.log", "r", encoding="utf-8") as f:
#         data_list: list = f.readlines()
#         len_line: int = int(age[0] or 0)
#         await log.finish("".join(data_list[-len_line:]))

@scheduler.scheduled_job("cron", hour=7, minute=0, second=0, id="job_0")
async def run_every_2_hour():
    global data
    # bot = get_bot()
    data = {"user_status": {}}
    for i in config.group_id:
        # await bot.call_api("send_group_msg", group_id=i, message="重置群数据", auto_escape=True)
        ban_logger.info(f"操作执行 -重置群数据 来自 [群:{i}]")
