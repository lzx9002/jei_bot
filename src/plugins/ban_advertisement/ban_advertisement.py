# -*- coding: utf-8 -*-
# @Project : jei_bot
# @File    : ban_advertisement.py
# @IDE     : PyCharm
# @Author  : lzx9002
# @Time    : 2025/4/6 13:53
import json
from pyzbar.pyzbar import decode
from nonebot.plugin.on import on_message, on_command, on_notice, on
from nonebot.adapters.onebot.v11 import Bot as V11Bot, GroupMessageEvent, GroupRecallNoticeEvent, GROUP_MEMBER
from nonebot.adapters.onebot.v11.message import Message, MessageSegment

message = on_message(permission=GROUP_MEMBER)
data = {
    "user_status": {}
}
ban_time = [
    None,
    2,
    10,
    30,
    True,
]

@message.handle()
async def _(event: GroupMessageEvent, bot: V11Bot):
    for i in event.message:
        if i.type == "image":
            data["user_status"][event.user_id] = data["user_status"].get(event.user_id,0)+1
    await message.send(str(data))

recall = on_notice()

@recall.handle()
async def _(event: GroupRecallNoticeEvent, bot: V11Bot):
    if event.operator_id == 2854196310:
        if ban_time[data["user_status"].get(event.user_id,0)] is True:
            await recall.send(Message([
                MessageSegment.text("用户"),
                MessageSegment.at(event.user_id),
                MessageSegment.text(f"({event.user_id})警告多次无效，执行纪律")
            ]))
            await bot.call_api("set_group_kick", group_id=event.group_id, user_id=event.user_id, reject_add_request=True)
            del data["user_status"][event.user_id]
            return
        elif ban_time[data["user_status"].get(event.user_id,0)]:
            await recall.send(Message([
                MessageSegment.text("用户"),
                MessageSegment.at(event.user_id),
                MessageSegment.text(f"({event.user_id})尝试刷屏{data["user_status"][event.user_id]}次,禁言{ban_time[data["user_status"][event.user_id]]}min，请群友引以为戒")
            ]))
            await bot.call_api("set_group_ban", group_id=event.group_id, user_id=event.user_id, duration=ban_time[data["user_status"][event.user_id]]*60)
    await recall.send(str(data))