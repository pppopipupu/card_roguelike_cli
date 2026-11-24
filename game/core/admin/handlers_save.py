from typing import Any, Optional

from ...data.progression.achievement_data import ACHIEVEMENT_ORDER, ACHIEVEMENTS_CONFIG
from ...data.text.locale_data import get_locale_text
from ...json_codec import dumps
from ..progress.achievement_service import AchievementService
from .registry import AdminCommandHandler, AdminContext, register_admin_command
from .resolvers import parse_flag_value, resolve_achievement

FLAG_SCOPES = ("town", "floor", "node", "map")


def _format_flag_val(val: Any) -> str:
    if isinstance(val, (dict, list)):
        try:
            raw = dumps(val)
            return raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)
        except Exception:
            return str(val)
    return str(val)


@register_admin_command(
    aliases=("ach", "achievement", "成就"),
    category="save",
    help_key="i18n_admin.help_cmd_ach",
    detail_key="i18n_admin.detail_ach",
)
class AchievementAdminCommand(AdminCommandHandler):
    async def execute(self, ctx: AdminContext) -> str:
        args = list(ctx.args)
        if not args or args[0].lower() in ("list", "ls", "查看"):
            filter_mode = args[1].lower() if len(args) >= 2 else "unlocked"
            async with ctx.lock():
                stats = ctx.save_manager.load_stats(ctx.target_user_id)
                unlocked = set(stats.unlocked_achievements or [])
                rows = []
                for aid in ACHIEVEMENT_ORDER:
                    is_done = aid in unlocked
                    if filter_mode == "unlocked" and not is_done:
                        continue
                    if filter_mode == "locked" and is_done:
                        continue
                    cfg = ACHIEVEMENTS_CONFIG[aid]
                    mark = "[V]" if is_done else "[ ]"
                    rows.append(f"{mark} {cfg['name']} ({aid})")
                return get_locale_text(
                    "i18n_admin.ach_list",
                    done=len(unlocked),
                    total=len(ACHIEVEMENT_ORDER),
                    items="\n".join(rows) if rows else "-",
                )

        sub = args[0].lower()
        if sub in ("check", "reconcile", "重算"):
            async with ctx.lock():
                svc = AchievementService(ctx.save_manager)
                stats = ctx.save_manager.load_stats(ctx.target_user_id)
                newly = svc.reconcile(ctx.target_user_id, stats=stats, save=True)
                names = [entry["name"] for entry in newly]
                return get_locale_text(
                    "i18n_admin.ach_reconciled",
                    count=len(names),
                    items=", ".join(names) if names else "-",
                )

        if sub in ("stat", "stats", "统计"):
            if len(args) < 2:
                async with ctx.lock():
                    stats = ctx.save_manager.load_stats(ctx.target_user_id)
                    data = stats.achievement_stats or {}
                    lines = [f"{k}={_format_flag_val(v)}" for k, v in sorted(data.items())]
                    return get_locale_text(
                        "i18n_admin.ach_stats_list",
                        items="\n".join(lines) if lines else "-",
                    )
            if args[1].lower() in ("del", "remove", "rm") and len(args) >= 3:
                flag_key = args[2]
                async with ctx.lock():
                    stats = ctx.save_manager.load_stats(ctx.target_user_id)
                    if not isinstance(stats.achievement_stats, dict) or flag_key not in stats.achievement_stats:
                        return get_locale_text("i18n_admin.err_flag_not_found", scope="achievement_stats", flag_key=flag_key)
                    stats.achievement_stats.pop(flag_key, None)
                    ctx.save_manager.save_stats(ctx.target_user_id, stats)
                    return get_locale_text("i18n_admin.flag_deleted", scope="achievement_stats", flag_key=flag_key)
            if len(args) < 3:
                return get_locale_text("i18n_admin.detail_ach")
            flag_key = args[1]
            val = parse_flag_value(" ".join(args[2:]))
            async with ctx.lock():
                stats = ctx.save_manager.load_stats(ctx.target_user_id)
                if not isinstance(stats.achievement_stats, dict):
                    stats.achievement_stats = {}
                stats.achievement_stats[flag_key] = val
                ctx.save_manager.save_stats(ctx.target_user_id, stats)
                return get_locale_text(
                    "i18n_admin.flag_set",
                    scope="achievement_stats",
                    flag_key=flag_key,
                    value=_format_flag_val(val),
                )

        no_gp = False
        cleaned = []
        for tok in args[1:]:
            if tok.lower() in ("--no-gp", "-n"):
                no_gp = True
            else:
                cleaned.append(tok)

        if sub in ("unlock", "add", "grant", "解锁"):
            if not cleaned:
                return get_locale_text("i18n_admin.detail_ach")
            query = cleaned[0]
            async with ctx.lock():
                stats = ctx.save_manager.load_stats(ctx.target_user_id)
                if query.lower() == "all":
                    added = 0
                    gp_total = 0
                    for aid in ACHIEVEMENT_ORDER:
                        if aid not in stats.unlocked_achievements:
                            stats.unlocked_achievements.append(aid)
                            added += 1
                            if not no_gp:
                                gp_total += int(ACHIEVEMENTS_CONFIG[aid].get("gp_reward", 0) or 0)
                    if gp_total:
                        stats.gp = int(stats.gp or 0) + gp_total
                    ctx.save_manager.save_stats(ctx.target_user_id, stats)
                    return get_locale_text("i18n_admin.ach_unlocked_all", count=added, gp=gp_total)
                aid = resolve_achievement(query)
                if not aid:
                    return get_locale_text("i18n_admin.err_ach_not_found", ach=query)
                cfg = ACHIEVEMENTS_CONFIG[aid]
                if aid in stats.unlocked_achievements:
                    return get_locale_text("i18n_admin.ach_already_unlocked", name=cfg["name"], aid=aid)
                stats.unlocked_achievements.append(aid)
                gp_reward = 0 if no_gp else int(cfg.get("gp_reward", 0) or 0)
                if gp_reward:
                    stats.gp = int(stats.gp or 0) + gp_reward
                ctx.save_manager.save_stats(ctx.target_user_id, stats)
                return get_locale_text("i18n_admin.ach_unlocked", name=cfg["name"], aid=aid, gp=gp_reward)

        if sub in ("revoke", "del", "remove", "rm", "lock", "撤销"):
            if not cleaned:
                return get_locale_text("i18n_admin.detail_ach")
            query = cleaned[0]
            async with ctx.lock():
                stats = ctx.save_manager.load_stats(ctx.target_user_id)
                if query.lower() == "all":
                    count = len(stats.unlocked_achievements)
                    stats.unlocked_achievements.clear()
                    ctx.save_manager.save_stats(ctx.target_user_id, stats)
                    return get_locale_text("i18n_admin.ach_revoked_all", count=count)
                aid = resolve_achievement(query) or query
                if aid not in stats.unlocked_achievements:
                    return get_locale_text("i18n_admin.err_ach_not_unlocked", ach=query)
                stats.unlocked_achievements.remove(aid)
                ctx.save_manager.save_stats(ctx.target_user_id, stats)
                name = ACHIEVEMENTS_CONFIG.get(aid, {}).get("name", aid)
                return get_locale_text("i18n_admin.ach_revoked", name=name, aid=aid)

        return get_locale_text("i18n_admin.detail_ach")


@register_admin_command(
    aliases=("flag", "fl", "标记"),
    category="save",
    help_key="i18n_admin.help_cmd_flag",
    detail_key="i18n_admin.detail_flag",
)
class FlagAdminCommand(AdminCommandHandler):
    def _get_scope_dict(self, scope: str, stats, run) -> TupleOptionalDict:
        if scope == "town":
            if not isinstance(stats.town_flags, dict):
                stats.town_flags = {}
            return stats.town_flags, "stats"
        if run is None:
            return None, "no_save"
        if scope == "floor":
            fm = getattr(run, "floor_map", None)
            if fm is None:
                return None, "no_floor"
            if not isinstance(fm.floor_flags, dict):
                fm.floor_flags = {}
            return fm.floor_flags, "run"
        if scope == "node":
            if not isinstance(run.node_data, dict):
                run.node_data = {}
            return run.node_data, "run"
        if scope == "map":
            if not isinstance(run.map_data, dict):
                run.map_data = {}
            return run.map_data, "run"
        return None, "invalid"

    async def execute(self, ctx: AdminContext) -> str:
        args = ctx.args
        if not args or args[0].lower() in ("list", "ls", "查看"):
            scope_arg = args[1].lower() if len(args) >= 2 else "all"
            async with ctx.lock():
                stats = ctx.save_manager.load_stats(ctx.target_user_id)
                run = ctx.save_manager.load_save(ctx.target_user_id)
                scopes = FLAG_SCOPES if scope_arg == "all" else (scope_arg,)
                sections = []
                for sc in scopes:
                    if sc not in FLAG_SCOPES:
                        return get_locale_text("i18n_admin.err_flag_scope", scope=sc)
                    target_dict, status = self._get_scope_dict(sc, stats, run)
                    if target_dict is None:
                        sections.append(f"[{sc}] -")
                        continue
                    pairs = [f"  {k} = {_format_flag_val(v)}" for k, v in sorted(target_dict.items())]
                    sections.append(f"[{sc}]" + ("\n" + "\n".join(pairs) if pairs else " -"))
                return "\n".join(sections)

        sub = args[0].lower()
        if sub in FLAG_SCOPES:
            if len(args) == 1:
                return await self._list_single(ctx, sub)
            if len(args) == 2:
                return await self._get_flag(ctx, sub, args[1])
            return await self._set_flag(ctx, sub, args[1], " ".join(args[2:]))

        if sub == "get":
            if len(args) < 3:
                return get_locale_text("i18n_admin.detail_flag")
            return await self._get_flag(ctx, args[1].lower(), args[2])

        if sub == "set":
            if len(args) < 4:
                return get_locale_text("i18n_admin.detail_flag")
            return await self._set_flag(ctx, args[1].lower(), args[2], " ".join(args[3:]))

        if sub in ("del", "remove", "rm", "删除"):
            if len(args) < 3:
                return get_locale_text("i18n_admin.detail_flag")
            return await self._del_flag(ctx, args[1].lower(), args[2])

        if sub in ("clear", "清空"):
            if len(args) < 2:
                return get_locale_text("i18n_admin.detail_flag")
            return await self._clear_flags(ctx, args[1].lower())

        return get_locale_text("i18n_admin.detail_flag")

    async def _list_single(self, ctx: AdminContext, scope: str) -> str:
        async with ctx.lock():
            stats = ctx.save_manager.load_stats(ctx.target_user_id)
            run = ctx.save_manager.load_save(ctx.target_user_id)
            target_dict, status = self._get_scope_dict(scope, stats, run)
            if target_dict is None:
                return self._scope_error(scope, status)
            pairs = [f"  {k} = {_format_flag_val(v)}" for k, v in sorted(target_dict.items())]
            return f"[{scope}]" + ("\n" + "\n".join(pairs) if pairs else " -")

    async def _get_flag(self, ctx: AdminContext, scope: str, flag_key: str) -> str:
        async with ctx.lock():
            stats = ctx.save_manager.load_stats(ctx.target_user_id)
            run = ctx.save_manager.load_save(ctx.target_user_id)
            target_dict, status = self._get_scope_dict(scope, stats, run)
            if target_dict is None:
                return self._scope_error(scope, status)
            if flag_key not in target_dict:
                return get_locale_text("i18n_admin.err_flag_not_found", scope=scope, flag_key=flag_key)
            return get_locale_text(
                "i18n_admin.flag_get",
                scope=scope,
                flag_key=flag_key,
                value=_format_flag_val(target_dict[flag_key]),
            )

    async def _set_flag(self, ctx: AdminContext, scope: str, flag_key: str, raw_val: str) -> str:
        val = parse_flag_value(raw_val)
        async with ctx.lock():
            stats = ctx.save_manager.load_stats(ctx.target_user_id)
            run = ctx.save_manager.load_save(ctx.target_user_id)
            target_dict, status = self._get_scope_dict(scope, stats, run)
            if target_dict is None:
                return self._scope_error(scope, status)
            target_dict[flag_key] = val
            if status == "stats":
                ctx.save_manager.save_stats(ctx.target_user_id, stats)
            else:
                ctx.save_manager.save_save(ctx.target_user_id, run)
            return get_locale_text(
                "i18n_admin.flag_set",
                scope=scope,
                flag_key=flag_key,
                value=_format_flag_val(val),
            )

    async def _del_flag(self, ctx: AdminContext, scope: str, flag_key: str) -> str:
        async with ctx.lock():
            stats = ctx.save_manager.load_stats(ctx.target_user_id)
            run = ctx.save_manager.load_save(ctx.target_user_id)
            target_dict, status = self._get_scope_dict(scope, stats, run)
            if target_dict is None:
                return self._scope_error(scope, status)
            if flag_key not in target_dict:
                return get_locale_text("i18n_admin.err_flag_not_found", scope=scope, flag_key=flag_key)
            target_dict.pop(flag_key, None)
            if status == "stats":
                ctx.save_manager.save_stats(ctx.target_user_id, stats)
            else:
                ctx.save_manager.save_save(ctx.target_user_id, run)
            return get_locale_text("i18n_admin.flag_deleted", scope=scope, flag_key=flag_key)

    async def _clear_flags(self, ctx: AdminContext, scope: str) -> str:
        async with ctx.lock():
            stats = ctx.save_manager.load_stats(ctx.target_user_id)
            run = ctx.save_manager.load_save(ctx.target_user_id)
            target_dict, status = self._get_scope_dict(scope, stats, run)
            if target_dict is None:
                return self._scope_error(scope, status)
            count = len(target_dict)
            target_dict.clear()
            if status == "stats":
                ctx.save_manager.save_stats(ctx.target_user_id, stats)
            else:
                ctx.save_manager.save_save(ctx.target_user_id, run)
            return get_locale_text("i18n_admin.flag_cleared", scope=scope, count=count)

    def _scope_error(self, scope: str, status: str) -> str:
        if status == "no_save":
            return get_locale_text("i18n_cli_core.err_admin_no_save")
        if status == "no_floor":
            return get_locale_text("i18n_admin.err_no_floor_map")
        return get_locale_text("i18n_admin.err_flag_scope", scope=scope)


TupleOptionalDict = tuple[Optional[dict[str, Any]], str]
