from ...data.text.locale_data import get_locale_text
from ...renderer import GameRenderer
from .registry import (
    AdminCommandHandler,
    AdminContext,
    register_admin_command,
    render_admin_help,
)
from .resolvers import parse_bool, resolve_target_user

BOSS_FIXED_NAMES = ("腐化之心", "Icerainboww")
BOSS_RANDOM_ALIASES = ("random", "随机", "轮换")


@register_admin_command(
    aliases=("help", "h", "?", "帮助"),
    category="config",
    help_key="i18n_admin.help_cmd_help",
    detail_key="i18n_admin.detail_help",
)
class HelpAdminCommand(AdminCommandHandler):
    async def execute(self, ctx: AdminContext) -> str:
        topic = ctx.args[0] if ctx.args else ""
        return render_admin_help(topic)


@register_admin_command(
    aliases=("boss", "最终boss"),
    category="config",
    help_key="i18n_admin.help_cmd_boss",
    detail_key="i18n_admin.detail_boss",
)
class BossAdminCommand(AdminCommandHandler):
    async def execute(self, ctx: AdminContext) -> str:
        args = ctx.args
        if not args:
            cfg = ctx.save_manager.load_admin_config()
            boss = cfg.get("final_boss", "random")
            boss_zh = (
                get_locale_text("i18n_cli_core.random_rotation")
                if boss == "random"
                else boss
            )
            return get_locale_text("i18n_cli_core.admin_boss_current", boss=boss_zh)
        if len(args) >= 2 and args[0].lower() == "set":
            target_boss = args[1]
            if target_boss.lower() in BOSS_RANDOM_ALIASES:
                ctx.save_manager.save_admin_config({"final_boss": "random"})
                return get_locale_text("i18n_cli_core.admin_boss_set_random")
            if target_boss in BOSS_FIXED_NAMES:
                ctx.save_manager.save_admin_config({"final_boss": target_boss})
                return get_locale_text(
                    "i18n_cli_core.admin_boss_set_fixed", boss=target_boss
                )
            return get_locale_text("i18n_cli_core.err_admin_invalid_boss")
        return get_locale_text("i18n_cli_core.err_admin_boss_usage")


@register_admin_command(
    aliases=("icerainboww", "ice"),
    category="config",
    help_key="i18n_admin.help_cmd_icerainboww",
    detail_key="i18n_admin.detail_icerainboww",
)
class IcerainbowwAdminCommand(AdminCommandHandler):
    async def execute(self, ctx: AdminContext) -> str:
        args = ctx.args
        if not args:
            cfg = ctx.save_manager.load_admin_config()
            status = cfg.get("icerainboww_enabled", True)
            status_zh = (
                get_locale_text("i18n_cli_core.status_enabled")
                if status
                else get_locale_text("i18n_cli_core.status_disabled")
            )
            return get_locale_text(
                "i18n_cli_core.admin_icerainboww_current", status=status_zh
            )
        parsed = parse_bool(args[0])
        if parsed is None:
            return get_locale_text("i18n_cli_core.err_admin_icerainboww_param")
        cfg = ctx.save_manager.load_admin_config()
        cfg["icerainboww_enabled"] = parsed
        ctx.save_manager.save_admin_config(cfg)
        if parsed:
            return get_locale_text("i18n_cli_core.admin_icerainboww_enabled")
        return get_locale_text("i18n_cli_core.admin_icerainboww_disabled")


@register_admin_command(
    aliases=("jump", "j", "跳层"),
    category="world",
    help_key="i18n_admin.help_cmd_jump",
    detail_key="i18n_admin.detail_jump",
)
class JumpAdminCommand(AdminCommandHandler):
    async def execute(self, ctx: AdminContext) -> str:
        args = ctx.args
        if len(args) == 1:
            target_uid = ctx.target_user_id
            stage_str = args[0]
        elif len(args) >= 2:
            resolved = resolve_target_user(ctx.save_manager, args[0])
            target_uid = resolved or args[0]
            stage_str = args[1]
        else:
            return get_locale_text("i18n_cli_core.err_admin_jump_usage")
        try:
            target_stage = int(stage_str)
        except ValueError:
            return get_locale_text("i18n_cli_core.err_admin_jump_int")
        if not (1 <= target_stage <= 32):
            return get_locale_text("i18n_cli_core.err_admin_jump_range")
        async with ctx.lock(target_uid):
            run = ctx.save_manager.load_save(target_uid)
            if not run:
                return get_locale_text("i18n_cli_core.err_admin_no_save")
            msg = ctx.engine.jump_to_stage(run, target_stage)
            return get_locale_text(
                "i18n_cli_core.admin_action_result",
                msg=msg,
                rendered=GameRenderer.render_game(run),
            )
