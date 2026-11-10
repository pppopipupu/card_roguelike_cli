from typing import Generator

from ...base import CommandHandler
from .....data.locale_data import get_locale_text


class FriendCommand(CommandHandler, names=["friend", "好友", "fr"], allowed_states=["menu", "town", "explore", "battle", "dialog", "cafe"], help_key="friend"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        service = router.social_service
        if len(parts) < 2:
            yield get_locale_text("i18n_cli_general_a.friend.usage")
            return
        sub = parts[1].strip().lower()
        arg = " ".join(parts[2:]).strip() if len(parts) > 2 else ""
        if sub in ("list", "ls", "列表", "好友列表"):
            yield service.friend_list(user_id)
        elif sub in ("search", "find", "搜索", "查找"):
            yield service.friend_search(user_id, arg)
        elif sub in ("add", "添加", "加", "申请"):
            if not arg:
                yield get_locale_text("i18n_cli_general_a.friend.add_need_arg")
                return
            yield service.friend_add(user_id, arg)
        elif sub in ("requests", "req", "申请列表", "待处理"):
            yield service.friend_requests(user_id)
        elif sub in ("accept", "接受", "同意"):
            if not arg:
                yield get_locale_text("i18n_cli_general_a.friend.accept_need_arg")
                return
            yield service.friend_accept(user_id, arg)
        elif sub in ("reject", "拒绝", "decline"):
            if not arg:
                yield get_locale_text("i18n_cli_general_a.friend.reject_need_arg")
                return
            yield service.friend_reject(user_id, arg)
        elif sub in ("remove", "del", "delete", "删除", "移除"):
            if not arg:
                yield get_locale_text("i18n_cli_general_a.friend.remove_need_arg")
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
                yield get_locale_text("i18n_cli_general_a.friend.invite_need_arg")
                return
            yield service.team_invite(user_id, arg)
        elif sub in ("team", "队伍", "status"):
            yield service.team_status(user_id)
        else:
            yield get_locale_text("i18n_cli_general_a.friend.unknown_sub")
