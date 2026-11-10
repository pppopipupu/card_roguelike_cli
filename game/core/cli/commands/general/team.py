from typing import Generator

from ...base import CommandHandler
from .....renderer import GameRenderer
from .....data.locale_data import get_locale_text


class TeamCommand(CommandHandler, names=["team", "队伍", "组队", "tm", "lobby"], allowed_states=["menu", "town", "explore", "battle", "dialog", "cafe"], help_key="team"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        service = router.social_service
        if len(parts) < 2:
            yield service.team_status(user_id)
            return
        sub = parts[1].strip().lower()
        arg = " ".join(parts[2:]).strip() if len(parts) > 2 else ""
        if sub in ("create", "new", "创建", "建队"):
            yield service.team_create(user_id)
        elif sub in ("invite", "邀请"):
            if not arg:
                yield get_locale_text("i18n_cli_general_a.team.invite_need_arg")
                return
            yield service.team_invite(user_id, arg)
        elif sub in ("join", "accept", "加入", "接受"):
            yield service.team_join(user_id, arg.upper() if arg else "")
        elif sub in ("leave", "quit", "离开", "退出"):
            yield service.team_leave(user_id)
        elif sub in ("ready", "准备", "r"):
            yield service.team_ready(user_id, True)
        elif sub in ("unready", "取消准备"):
            yield service.team_ready(user_id, False)
        elif sub in ("start", "开始", "go"):
            result = service.team_start(user_id)
            if isinstance(result, tuple):
                message, run = result
                yield message + "\n\n" + GameRenderer.render_game(run)
            else:
                yield result
        elif sub in ("kick", "踢", "踢出"):
            if not arg:
                yield get_locale_text("i18n_cli_general_a.team.kick_need_arg")
                return
            yield service.team_kick(user_id, arg)
        elif sub in ("disband", "dissolve", "解散"):
            yield service.team_disband(user_id)
        elif sub in ("status", "info", "状态", "队伍状态"):
            yield service.team_status(user_id)
        elif sub in ("invites", "invitations", "邀请列表"):
            yield service.team_invites(user_id)
        else:
            yield get_locale_text("i18n_cli_general_a.team.unknown_sub")
