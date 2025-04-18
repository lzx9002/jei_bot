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

from nonebot.internal.rule import Rule
from nonebot.params import CommandArg
from nonebot.rule import to_me
from pyzbar.pyzbar import decode, Decoded
from PIL import Image
from nonebot.plugin.on import on_message, on_command, on_notice, on
from nonebot.adapters.onebot.v11 import Bot as V11Bot, GroupMessageEvent, GroupRecallNoticeEvent, GROUP_MEMBER, Event, \
    PrivateMessageEvent
from nonebot.adapters.onebot.v11.message import Message, MessageSegment

from .config import Config
from .module import fetch_image_from_url_ssl
from nonebot import require, get_driver, get_plugin_config, get_bot

require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler

import logging
logging.basicConfig(filename='log/log.log', level = logging.INFO,format = '%(asctime)s %(levelname)s - %(message)s', encoding = 'utf-8')
logger = logging.getLogger(__name__)

config = get_plugin_config(Config)

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
def is_allowed_group() -> Rule:
    async def check_group(bot: V11Bot, event: Event) -> bool:
        return event.group_id in config.group_id
    return Rule(check_group)
recall = on_notice(rule=is_allowed_group())

@recall.handle()
async def _(event: GroupRecallNoticeEvent, bot: V11Bot):
    if event.group_id in config.group_id:
        if event.operator_id == 2854196310:
            await asyncio.sleep(2)
            img_msg_data=await bot.call_api("get_msg", message_id=event.message_id)
            for i in img_msg_data["message"]:
                if i["type"] == "image":
                    logger.info(f"群{event.group_id}收到图片{i["data"]["url"]}")
                    img = Image.open(await fetch_image_from_url_ssl(i["data"]["url"]))
                    result: list[Decoded] = decode(img)
                    if result:
                        data["user_status"][event.user_id] = data["user_status"].get(event.user_id, 0) + 1
                        logger.info(f"群{event.group_id}成功解析图片:\"{i["data"]["url"]}\"内容{json.dumps([i.data.decode() for i in result])}")
            if ban_time[data["user_status"].get(event.user_id,0)-1] is True:
                await recall.send(Message([
                    MessageSegment.text("用户"),
                    MessageSegment.at(event.user_id),
                    MessageSegment.text(f"({event.user_id})警告多次无效，执行纪律")
                ]))
                await bot.call_api("set_group_kick", group_id=event.group_id, user_id=event.user_id, reject_add_request=True)
                del data["user_status"][event.user_id]
                logger.info(f"群{event.group_id}用户{event.user_id}多次刷屏打广告,警告无效,已踢出群聊")
                return
            elif ban_time[data["user_status"].get(event.user_id,0)-1]:
                await recall.send(Message([
                    MessageSegment.text("用户"),
                    MessageSegment.at(event.user_id),
                    # MessageSegment.text(f"({event.user_id})打广告{data["user_status"][event.user_id]}次,禁言{ban_time[data["user_status"][event.user_id]]}min")
                    MessageSegment.text(f"({event.user_id})打广告{data["user_status"][event.user_id]}次")
                ]))
                await bot.call_api("set_group_ban", group_id=event.group_id, user_id=event.user_id, duration=ban_time[data["user_status"][event.user_id]-1]*60)
                # logger.info(f"用户{event.user_id}尝试刷屏{data["user_status"][event.user_id]}次,禁言{ban_time[data["user_status"][event.user_id]]}min")
                logger.info(f"群{event.group_id}用户{event.user_id}尝试打广告{data["user_status"][event.user_id]}次")


log = on_command("log")

@log.handle()
async def _(event: PrivateMessageEvent, bot: V11Bot, age: Message = CommandArg()):
    age = age.extract_plain_text().split(" ")[0:1]
    with open("log/log.log", "r", encoding="utf-8") as f:
        data_list: list = f.readlines()
        len_line: int = int(age[0] or 0)
        await log.finish("".join(data_list[-len_line:]))

@scheduler.scheduled_job("cron", hour=7, minute=0, second=0, id="job_0")
async def run_every_2_hour():
    global data
    bot = get_bot()
    data = {"user_status": {}}
    for i in config.group_id:
        await bot.call_api("send_group_msg", group_id=i, message="重置群数据", auto_escape=True)
        logger.info(f"群{i}重置群数据")
