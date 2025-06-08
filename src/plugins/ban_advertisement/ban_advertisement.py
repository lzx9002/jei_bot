# -*- coding: utf-8 -*-
# @Project : jei_bot
# @File    : ban_advertisement.py
# @IDE     : PyCharm
# @Author  : lzx9002
# @Time    : 2025/4/6 13:53
# import logging
import asyncio
import base64
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
from nonebot.plugin.on import on_message, on_command, on_notice, on, on_request
from nonebot.adapters.onebot.v11 import Bot as V11Bot, GroupMessageEvent, GroupRecallNoticeEvent, GroupRequestEvent, GROUP_MEMBER, Event, \
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
    status = tuple(await asyncio.gather(img(event.message["image"]), qun_share(event.message["json"]), text_msg(event.message["text"])))
    if not any(status): # 文本消息关键词判断
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
        await message.send(Message([
            MessageSegment.text("用户"),
            MessageSegment.at(event.user_id),
            MessageSegment.text(f"({event.user_id})警告多次无效，执行纪律")
        ]))
        await bot.set_group_kick(group_id=event.group_id, user_id=event.user_id, reject_add_request=True)
        del data["user_status"][event.user_id]
        ban_logger.info(f"踢出用户{event.user_id} 来自群:{event.group_id}")
    elif ban_time_value:
        await message.send(Message([
            MessageSegment.text("用户"),
            MessageSegment.at(event.user_id),
            # MessageSegment.text(f"({event.user_id})打广告{data["user_status"][event.user_id]}次,禁言{ban_time[data["user_status"][event.user_id]]}min")
            MessageSegment.text(f"({event.user_id})违反发言规则,警告{data["user_status"][event.user_id]}次")
        ]))
        await bot.set_group_ban(group_id=event.group_id, user_id=event.user_id, duration=ban_time_value*60)
        # logger.info(f"用户{event.user_id}尝试刷屏{data["user_status"][event.user_id]}次,禁言{ban_time[data["user_status"][event.user_id]]}min")
        ban_logger.info(f"警告用户{event.user_id} 来自群:{event.group_id}")

async def img(image: Message) -> bool:
    for i in image:
        img_bytesio = await fetch_image_from_url_ssl(i.data["url"], aiohttp_session)
        result: list[Decoded] = decode(Image.open(img_bytesio))
        if result:
            return True
        else:
            img_base64 = base64.b64encode(img_bytesio.read()).decode('utf-8')
            ai_result = await ai(aiohttp_session, url=img_base64, model="deepseek-ai/deepseek-vl2")
            if ai_result == "true" or ai_result == "True":
                return True
            elif ai_result == "false" or ai_result == "False":
                return False
            else:
                return True
    return False

async def qun_share(json_card: Message) -> bool:
    for i in json_card:
        return json.loads(i.data["data"])["bizsrc"] == "qun.share"
    return False

async def text_msg(text: Message) -> bool:
    # if extract_numbers_sub(event.message.extract_plain_text())
    return any(substring in text.extract_plain_text() for substring in key)

request = on_request(rule=is_allowed_group(config.group_id))

@request.handle()
async def _(event: GroupRequestEvent, bot: V11Bot):
    user_data = await bot.get_stranger_info(user_id=event.user_id)
    is_approve = user_data["level"] <= 7
    await bot.set_group_add_request(flag=event.flag, sub_type=event.sub_type, approve=is_approve)
    if is_approve:

        pass
    else:
        pass

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

# rm_key = on_command("删除关键词", rule=is_allowed_group(config.group_id) & to_me(), permission=GROUP_OWNER | GROUP_ADMIN, priority=50, block=False)
#
# @rm_key.handle()
# async def _(event: GroupMessageEvent, bot: V11Bot, args: Message = CommandArg()):
#     rm_keys=split(args.extract_plain_text())
#     try:
#         global key
#         error = []
#         for i in rm_keys:
#             if not i in key:
#                 rm_keys.remove(i)
#                 error.append(i)
#         # 读取所有行并去除换行符
#         with data_file.open('r', encoding='utf-8') as file:
#             lines = [line.strip() for line in file]
#
#         # 将保留的键写回文件
#         with data_file.open('w', encoding='utf-8') as file:
#             for i in sorted(set(lines) - set(rm_keys)):
#                 file.write(i + '\n')
#
#         with data_file.open('r', encoding='utf-8') as file:
#             key = file.read().splitlines()
#         if error:
#             raise KeyError(f"关键词{','.join(error)}不存在")
#     except Exception as e:
#         await rm_key.finish(Message([
#             MessageSegment.reply(event.message_id),
#             MessageSegment.at(event.user_id),
#             MessageSegment.text(f"删除关键词失败:\n{type(e).__name__}: {str(e)}")
#         ]))
#     else:
#         await rm_key.finish(Message([
#             MessageSegment.reply(event.message_id),
#             MessageSegment.at(event.user_id),
#             MessageSegment.text(f"成功删除关键词{','.join(rm_keys)}")
#         ]))

# reset = on_command("重置", rule=is_allowed_group(config.group_id), permission=GROUP_OWNER | GROUP_ADMIN, priority=50, block=True)
#
# @reset.handle()
# async def _(event: GroupMessageEvent, bot: V11Bot, args_message: Message = CommandArg()):
#     args_str = ""
#     for i in args_message:
#         if i.type == "text":
#             args_str+=i.data["text"]
#         elif i.type == "at":
#             args_str+=i.data["qq"]
#     args = split(args_str)
#     if not args:
#         data["user_status"].clear()
#         await reset.finish(Message([
#             MessageSegment.reply(event.message_id),
#             MessageSegment.at(event.user_id),
#             MessageSegment.text(f"已成功重置所有用户")
#         ]))
#     if not all(item.isdigit() for item in args):
#         await reset.finish(Message([
#             MessageSegment.reply(event.message_id),
#             MessageSegment.at(event.user_id),
#             MessageSegment.text(" 参数不合法"),
#         ]))
#     success=[]
#     fail=[]
#     for i in args:
#         if not data["user_status"].pop(int(i), False) is False:
#             success.append(int(i))
#         else:
#             fail.append(int(i))
#     await reset.finish(Message([
#         MessageSegment.reply(event.message_id),
#         MessageSegment.at(event.user_id),
#         MessageSegment.text(f"{f"\n成功重置用户:{",".join(map(str, success))}" if success else ""}{f"\n未成功重置用户:{",".join(map(str, fail))}\nwhy:\n\t1.无该用户的记录\n\t2.输错用户id或@错人" if fail else ""}"),
#     ]))
#
# record = on_command("hhh")
#
# @record.handle()
# async def _(event: GroupMessageEvent, bot: V11Bot):
#     await bot.group_poke(group_id=event.group_id, user_id=event.user_id)

# log = on_command("log")
#
# @log.handle()
# async def _(event: PrivateMessageEvent, bot: V11Bot, age: Message = CommandArg()):
#     age = age.extract_plain_text().split(" ")[0:1]
#     with open("log/log.log", "r", encoding="utf-8") as f:
#         data_list: list = f.readlines()
#         len_line: int = int(age[0] or 0)
#         await log.finish("".join(data_list[-len_line:]))



@scheduler.scheduled_job("cron", hour=7, minute=0, second=0,)
async def clear_guoup():
    # bot = get_bot()
    data["user_status"].clear()
    for i in config.group_id:
        # await bot.call_api("send_group_msg", group_id=i, message="重置群数据", auto_escape=True)
        ban_logger.info(f"操作执行 -重置群数据 来自 [群:{i}]")
