from typing import Generator

from ...base import CommandHandler


class FriendCommand(CommandHandler, names=["friend", "好友", "fr"], allowed_states=["menu", "town", "explore", "battle", "dialog", "cafe"]):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        service = router.social_service
        if len(parts) < 2:
            yield (
                "👥 好友与组队指令：\n"
                " friend list 查看好友\n"
                " friend search <关键词> 搜索玩家\n"
                " friend add <ID或昵称> 发送好友申请\n"
                " friend requests 查看好友申请\n"
                " friend accept <ID或昵称> 接受申请\n"
                " friend reject <ID或昵称> 拒绝申请\n"
                " friend remove <ID或昵称> 删除好友\n"
                " friend id 查看自己的玩家 ID\n"
                " friend name <昵称> 修改昵称\n"
                " friend bind <通讯账号> 绑定通讯账号\n"
                " friend invite <好友> 邀请好友加入队伍"
            )
            return
        sub = parts[1].strip().lower()
        arg = " ".join(parts[2:]).strip() if len(parts) > 2 else ""
        if sub in ("list", "ls", "列表", "好友列表"):
            yield service.friend_list(user_id)
        elif sub in ("search", "find", "搜索", "查找"):
            yield service.friend_search(user_id, arg)
        elif sub in ("add", "添加", "加", "申请"):
            if not arg:
                yield "❌ 请提供玩家 ID、昵称或通讯账号，例如：friend add 小明"
                return
            yield service.friend_add(user_id, arg)
        elif sub in ("requests", "req", "申请列表", "待处理"):
            yield service.friend_requests(user_id)
        elif sub in ("accept", "接受", "同意"):
            if not arg:
                yield "❌ 请提供要接受的好友昵称或 ID。"
                return
            yield service.friend_accept(user_id, arg)
        elif sub in ("reject", "拒绝", "decline"):
            if not arg:
                yield "❌ 请提供要拒绝的好友昵称或 ID。"
                return
            yield service.friend_reject(user_id, arg)
        elif sub in ("remove", "del", "delete", "删除", "移除"):
            if not arg:
                yield "❌ 请提供要删除的好友昵称或 ID。"
                return
            yield service.friend_remove(user_id, arg)
        elif sub in ("id", "me", "我的id", "我的ID"):
            yield service.friend_id(user_id)
        elif sub in ("name", "昵称", "改名"):
            yield service.friend_name(user_id, arg)
        elif sub in ("bind", "绑定"):
            yield service.friend_bind(user_id, arg)
        elif sub in ("invite", "邀请"):
            if not arg:
                yield "❌ 请提供要邀请的好友昵称或 ID。"
                return
            yield service.team_invite(user_id, arg)
        elif sub in ("team", "队伍", "status"):
            yield service.team_status(user_id)
        else:
            yield "❌ 未知好友子指令。输入 friend 查看用法。"
