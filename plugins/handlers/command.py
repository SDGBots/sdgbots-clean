# SCP-079-CLEAN - Filter specific types of messages
# Copyright (C) 2019 SCP-079 <https://scp-079.org>
#
# This file is part of SCP-079-CLEAN.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging
import re
from copy import deepcopy

from pyrogram import Client, Filters, Message

from .. import glovar
from ..functions.channel import ask_for_help, forward_evidence, get_debug_text, send_debug, share_data
from ..functions.etc import bold, code, get_command_context, get_command_type, get_now, thread, user_mention
from ..functions.file import save
from ..functions.filters import is_class_c, test_group
from ..functions.group import delete_message
from ..functions.ids import init_group_id
from ..functions.telegram import delete_messages, get_group_info, send_message, send_report_message

# Enable logging
logger = logging.getLogger(__name__)


@Client.on_message(Filters.incoming & Filters.group & ~test_group
                   & Filters.command(["config"], glovar.prefix))
def config(client: Client, message: Message) -> bool:
    # Request CONFIG session
    try:
        gid = message.chat.id
        mid = message.message_id
        # Check permission
        if is_class_c(None, message):
            # Check command format
            command_type = get_command_type(message)
            if command_type and re.search(f"^{glovar.sender}$", command_type, re.I):
                now = get_now()
                # Check the config lock
                if now - glovar.configs[gid]["lock"] > 310:
                    # Set lock
                    glovar.configs[gid]["lock"] = now
                    # Ask CONFIG generate a config session
                    group_name, group_link = get_group_info(client, message.chat)
                    share_data(
                        client=client,
                        receivers=["CONFIG"],
                        action="config",
                        action_type="ask",
                        data={
                            "project_name": glovar.project_name,
                            "project_link": glovar.project_link,
                            "group_id": gid,
                            "group_name": group_name,
                            "group_link": group_link,
                            "user_id": message.from_user.id,
                            "config": glovar.configs[gid],
                            "default": glovar.default_config
                        }
                    )
                    # Send a report message to debug channel
                    text = get_debug_text(client, message.chat)
                    text += (f"群管理：{code(message.from_user.id)}\n"
                             f"操作：{code('创建设置会话')}\n")
                    thread(send_message, (client, glovar.debug_channel_id, text))

        thread(delete_message, (client, gid, mid))

        return True
    except Exception as e:
        logger.warning(f"Config error: {e}", exc_info=True)

    return False


@Client.on_message(Filters.incoming & Filters.group & ~test_group
                   & Filters.command(["config_clean"], glovar.prefix))
def config_directly(client: Client, message: Message) -> bool:
    # Config the bot directly
    try:
        gid = message.chat.id
        mid = message.message_id
        # Check permission
        if is_class_c(None, message):
            aid = message.from_user.id
            success = True
            reason = "已更新"
            new_config = deepcopy(glovar.configs[gid])
            text = f"管理员：{code(aid)}\n"
            # Check command format
            command_type, command_context = get_command_context(message)
            if command_type:
                if command_type == "show":
                    text += (f"操作：{code('查看设置')}\n"
                             f"设置：{code((lambda x: '默认' if x else '自定义')(new_config.get('default')))}\n")
                    for name in glovar.types["all"]:
                        text += (f"{glovar.names[name]}："
                                 f"{code((lambda x: '过滤' if x else '忽略')(new_config.get(name)))}\n")

                    for name in glovar.types["function"]:
                        text += (f"{glovar.names[name]}："
                                 f"{code((lambda x: '启用' if x else '禁用')(new_config.get(name)))}\n")

                    thread(send_report_message, (30, client, gid, text))
                    thread(delete_message, (client, gid, mid))
                    return True

                now = get_now()
                # Check the config lock
                if now - new_config["lock"] > 310:
                    if command_type == "default":
                        if not new_config.get("default"):
                            new_config = deepcopy(glovar.default_config)
                    else:
                        if command_context:
                            if command_type in glovar.types["all"] + glovar.types["function"]:
                                if command_context == "off":
                                    new_config[command_type] = False
                                elif command_context == "on":
                                    new_config[command_type] = True
                                else:
                                    success = False
                                    reason = "命令参数有误"
                            else:
                                success = False
                                reason = "命令类别有误"
                        else:
                            success = False
                            reason = "命令参数缺失"

                        if success:
                            new_config["default"] = False
                else:
                    success = False
                    reason = "设置当前被锁定"
            else:
                success = False
                reason = "格式有误"

            if success and new_config != glovar.configs[gid]:
                glovar.configs[gid] = new_config
                save("configs")

            text += (f"操作：{code('更改设置')}\n"
                     f"状态：{code(reason)}\n")
            thread(send_report_message, ((lambda x: 10 if x else 5)(success), client, gid, text))

        thread(delete_message, (client, gid, mid))

        return True
    except Exception as e:
        logger.warning(f"Config directly error: {e}", exc_info=True)

    return False


@Client.on_message(Filters.incoming & Filters.group & ~test_group
                   & Filters.command(["dafm"], glovar.prefix))
def dafm(client: Client, message: Message) -> bool:
    # Delete all from me
    try:
        gid = message.chat.id
        mid = message.message_id
        if init_group_id(gid):
            if glovar.configs[gid]["sde"] or is_class_c(None, message):
                uid = message.from_user.id
                confirm_text = get_command_type(message)
                if confirm_text and re.search("^yes$|^y$", confirm_text, re.I):
                    if uid not in glovar.deleted_ids[gid]:
                        # Forward the request command message as evidence
                        result = forward_evidence(client, message, "自动删除", "群组自定义", "sde")
                        if result:
                            glovar.deleted_ids[gid].add(uid)
                            ask_for_help(client, "delete", gid, uid)
                            send_debug(client, message.chat, "自动删除", uid, mid, result)

        thread(delete_message, (client, gid, mid))

        return True
    except Exception as e:
        logger.warning(f"DAFM error: {e}", exc_info=True)

    return False


@Client.on_message(Filters.incoming & Filters.group & ~test_group
                   & Filters.command(["purge"], glovar.prefix))
def purge(client: Client, message: Message) -> bool:
    # Purge messages
    try:
        gid = message.chat.id
        mid = message.message_id
        # Check permission
        if is_class_c(None, message):
            # Check validation
            r_message = message.reply_to_message
            if r_message and gid not in glovar.purged_ids:
                glovar.purged_ids.add(gid)
                aid = message.from_user.id
                text = (f"管理员：{code(aid)}\n"
                        f"执行操作：{code('清除消息')}\n")
                r_mid = r_message.message_id
                if r_mid - mid <= 1000:
                    thread(delete_messages, (client, gid, range(mid, r_mid)))
                    text += f"状态：{code('已执行')}\n"
                    reason = get_command_type(message)
                    if reason:
                        text += f"原因：{code(reason)}\n"
                else:
                    text += (f"状态：{code('未执行')}\n"
                             f"原因：{code('消息条数过多')}\n")

        thread(delete_message, (client, gid, mid))

        return True
    except Exception as e:
        logger.warning(f"Purge error: {e}", exc_info=True)

    return False


@Client.on_message(Filters.incoming & Filters.group & test_group
                   & Filters.command(["version"], glovar.prefix))
def version(client: Client, message: Message) -> bool:
    # Check the program's version
    try:
        cid = message.chat.id
        aid = message.from_user.id
        mid = message.message_id
        text = (f"管理员：{user_mention(aid)}\n\n"
                f"版本：{bold(glovar.version)}\n")
        thread(send_message, (client, cid, text, mid))

        return True
    except Exception as e:
        logger.warning(f"Version error: {e}", exc_info=True)

    return False