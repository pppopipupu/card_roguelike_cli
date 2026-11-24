from typing import Optional

from ...data.text.locale_data import get_locale_text
from ...data.world.grid_map_config import FLOOR_CONFIGS, ROOM_ICONS
from ...renderer import GameRenderer
from ..party.session import SessionContextScoper
from ..world.bleak_falls import generate_bleak_falls_floor
from ..world.chireiden import generate_chireiden_floor
from ..world.grid_map_generator import generate_floor_map
from ..world.tutorial import generate_tutorial_floor
from ..world.yog_quest.floor import generate_yog_quest_floor
from .registry import AdminCommandHandler, AdminContext, register_admin_command
from .resolvers import parse_bool, resolve_item, resolve_npc, resolve_prop

VALID_ROOM_TYPES = frozenset(ROOM_ICONS.keys()) - {"fog", "unknown", "cleared", "player"}


def _parse_floor_key(raw: str) -> Optional[int | float]:
    text = str(raw or "").strip()
    if not text:
        return None
    for key in FLOOR_CONFIGS:
        if str(key) == text:
            return key
    try:
        fval = float(text)
    except ValueError:
        return None
    for key in FLOOR_CONFIGS:
        if float(key) == fval:
            return key
    return None


def _build_floor_by_index(run, floor_idx: int | float, save_manager):
    if floor_idx == 0:
        return generate_tutorial_floor(run)
    if floor_idx in (1.5, 1.67777):
        return generate_bleak_falls_floor(run, float(floor_idx))
    if floor_idx == 3.5:
        return generate_chireiden_floor(run, 3.5)
    if floor_idx in (5, 6):
        return generate_yog_quest_floor(run, int(floor_idx))
    return generate_floor_map(run, int(floor_idx), save_manager=save_manager)


def _resolve_coord(fm, uid: str, raw: str) -> Optional[str]:
    tok = str(raw or "").strip()
    if not tok or tok.lower() in ("here", "cur", "current", "."):
        return fm.player_coords.get(uid)
    up = tok.upper()
    if up in fm.rooms:
        return up
    low = tok.lower()
    if low == "boss" and fm.boss_coord:
        return fm.boss_coord
    if low in ("secret", "secret_boss") and fm.secret_boss_coord:
        return fm.secret_boss_coord
    if low == "ritual" and fm.ritual_coord:
        return fm.ritual_coord
    for coord, room in fm.rooms.items():
        if room.room_type == low:
            return coord
    return None


@register_admin_command(
    aliases=("map", "mp", "地图"),
    category="world",
    help_key="i18n_admin.help_cmd_map",
    detail_key="i18n_admin.detail_map",
)
class MapAdminCommand(AdminCommandHandler):
    async def execute(self, ctx: AdminContext) -> str:
        args = ctx.args
        if not args or args[0].lower() in ("info", "status", "查看"):
            return await self._map_info(ctx)
        sub = args[0].lower()
        if sub in ("reveal", "all", "开图", "全图"):
            return await self._map_reveal(ctx)
        if sub in ("tp", "teleport", "传送"):
            return await self._map_tp(ctx, args[1:])
        if sub in ("floor", "fl", "切层"):
            return await self._map_floor(ctx, args[1:])
        if sub in ("room", "rm", "房间"):
            return await self._map_room(ctx, args[1:])
        if sub in ("secret", "密室"):
            return await self._map_secret(ctx, args[1:])
        if sub in ("regen", "reset", "重生成"):
            return await self._map_regen(ctx)
        if sub in ("exit", "leave", "unstuck", "脱离"):
            return await self._map_exit(ctx)
        return get_locale_text("i18n_admin.detail_map")

    async def _map_info(self, ctx: AdminContext) -> str:
        async with ctx.lock():
            run = ctx.save_manager.load_save(ctx.target_user_id)
            if not run:
                return get_locale_text("i18n_cli_core.err_admin_no_save")
            fm = getattr(run, "floor_map", None)
            if fm is None:
                return get_locale_text("i18n_admin.err_no_floor_map")
            coord = fm.player_coords.get(ctx.target_user_id, "-")
            room = fm.rooms.get(coord)
            room_desc = (
                f"{room.room_type} (explored={room.explored}, cleared={room.cleared}, "
                f"locked={room.locked}, npcs={room.npcs}, items={room.items}, props={room.props})"
                if room is not None
                else "-"
            )
            return get_locale_text(
                "i18n_admin.map_info",
                floor=fm.floor_index,
                w=fm.width,
                h=fm.height,
                coord=coord,
                node=run.node_type,
                boss=fm.boss_coord or "-",
                secret=fm.secret_boss_coord or "-",
                secret_open=fm.secret_unlocked,
                ritual=fm.ritual_coord or "-",
                revealed=len(fm.revealed_coords),
                total=len(fm.rooms),
                room=room_desc,
            )

    async def _map_reveal(self, ctx: AdminContext) -> str:
        async with ctx.lock():
            run = ctx.save_manager.load_save(ctx.target_user_id)
            if not run:
                return get_locale_text("i18n_cli_core.err_admin_no_save")
            fm = getattr(run, "floor_map", None)
            if fm is None:
                return get_locale_text("i18n_admin.err_no_floor_map")
            fm.revealed_coords = list(fm.rooms.keys())
            for room in fm.rooms.values():
                room.explored = True
            ctx.save_manager.save_save(ctx.target_user_id, run)
            msg = get_locale_text("i18n_admin.map_revealed", count=len(fm.rooms))
            return get_locale_text(
                "i18n_cli_core.admin_action_result",
                msg=msg,
                rendered=GameRenderer.render_game(run),
            )

    async def _map_tp(self, ctx: AdminContext, args: list[str]) -> str:
        if not args:
            return get_locale_text("i18n_admin.detail_map")
        target_tok = args[0]
        enter_room = len(args) >= 2 and args[1].lower() in ("enter", "go", "进入")
        async with ctx.lock():
            run = ctx.save_manager.load_save(ctx.target_user_id)
            if not run:
                return get_locale_text("i18n_cli_core.err_admin_no_save")
            fm = getattr(run, "floor_map", None)
            if fm is None:
                return get_locale_text("i18n_admin.err_no_floor_map")
            coord = _resolve_coord(fm, ctx.target_user_id, target_tok)
            if not coord or coord not in fm.rooms:
                return get_locale_text("i18n_admin.err_coord_not_found", coord=target_tok)
            fm.player_session_map.pop(ctx.target_user_id, None)
            fm.player_coords[ctx.target_user_id] = coord
            if coord not in fm.revealed_coords:
                fm.revealed_coords.append(coord)
            fm.rooms[coord].explored = True
            run.node_type = "grid_map"
            run.enemies.clear()
            run.node_data = {}
            if enter_room:
                res = ctx.engine.grid_map_service._enter_room(run, ctx.target_user_id, coord)
                ctx.save_manager.save_save(ctx.target_user_id, run)
                return res
            ctx.save_manager.save_save(ctx.target_user_id, run)
            msg = get_locale_text("i18n_admin.map_teleported", coord=coord, rtype=fm.rooms[coord].room_type)
            return get_locale_text(
                "i18n_cli_core.admin_action_result",
                msg=msg,
                rendered=GameRenderer.render_game(run),
            )

    async def _map_floor(self, ctx: AdminContext, args: list[str]) -> str:
        if not args:
            floors = ", ".join(str(k) for k in FLOOR_CONFIGS)
            return get_locale_text("i18n_admin.err_floor_invalid", floor="", floors=floors)
        floor_idx = _parse_floor_key(args[0])
        if floor_idx is None:
            floors = ", ".join(str(k) for k in FLOOR_CONFIGS)
            return get_locale_text("i18n_admin.err_floor_invalid", floor=args[0], floors=floors)
        async with ctx.lock():
            run = ctx.save_manager.load_save(ctx.target_user_id)
            if not run:
                return get_locale_text("i18n_cli_core.err_admin_no_save")
            fm = _build_floor_by_index(run, floor_idx, ctx.save_manager)
            run.floor_map = fm
            SessionContextScoper.ensure_full_party_order(run)
            stage_min = int(FLOOR_CONFIGS[floor_idx].get("stage_min", 1))
            for uid in run.all_human_uids():
                pl = run.players.get(uid)
                if pl is not None:
                    pl.stage = stage_min
            run.node_type = "grid_map"
            run.enemies.clear()
            run.node_data = {}
            ctx.save_manager.save_save(ctx.target_user_id, run)
            msg = get_locale_text("i18n_admin.map_floor_switched", floor=floor_idx, stage=stage_min)
            return get_locale_text(
                "i18n_cli_core.admin_action_result",
                msg=msg,
                rendered=GameRenderer.render_game(run),
            )

    async def _map_room(self, ctx: AdminContext, args: list[str]) -> str:
        if len(args) < 3:
            return get_locale_text("i18n_admin.detail_map")
        coord_tok = args[0]
        action = args[1].lower()
        rest = args[2:]
        async with ctx.lock():
            run = ctx.save_manager.load_save(ctx.target_user_id)
            if not run:
                return get_locale_text("i18n_cli_core.err_admin_no_save")
            fm = getattr(run, "floor_map", None)
            if fm is None:
                return get_locale_text("i18n_admin.err_no_floor_map")
            coord = _resolve_coord(fm, ctx.target_user_id, coord_tok)
            if not coord or coord not in fm.rooms:
                return get_locale_text("i18n_admin.err_coord_not_found", coord=coord_tok)
            room = fm.rooms[coord]

            if action == "type":
                rtype = rest[0].lower()
                if rtype not in VALID_ROOM_TYPES:
                    return get_locale_text("i18n_admin.err_room_type_invalid", rtype=rtype)
                room.room_type = rtype
                if rtype == "boss":
                    fm.boss_coord = coord
                elif rtype == "secret_boss":
                    fm.secret_boss_coord = coord
                msg = get_locale_text("i18n_admin.map_room_updated", coord=coord, field="room_type", value=rtype)
            elif action in ("clear", "cleared"):
                val = parse_bool(rest[0])
                if val is None:
                    return get_locale_text("i18n_admin.err_bool_required", value=rest[0])
                room.cleared = val
                msg = get_locale_text("i18n_admin.map_room_updated", coord=coord, field="cleared", value=val)
            elif action in ("explore", "explored"):
                val = parse_bool(rest[0])
                if val is None:
                    return get_locale_text("i18n_admin.err_bool_required", value=rest[0])
                room.explored = val
                if val and coord not in fm.revealed_coords:
                    fm.revealed_coords.append(coord)
                msg = get_locale_text("i18n_admin.map_room_updated", coord=coord, field="explored", value=val)
            elif action in ("lock", "locked"):
                val = parse_bool(rest[0])
                if val is None:
                    return get_locale_text("i18n_admin.err_bool_required", value=rest[0])
                room.locked = val
                msg = get_locale_text("i18n_admin.map_room_updated", coord=coord, field="locked", value=val)
            elif action in ("danger", "high_danger"):
                val = parse_bool(rest[0])
                if val is None:
                    return get_locale_text("i18n_admin.err_bool_required", value=rest[0])
                room.is_high_danger = val
                msg = get_locale_text("i18n_admin.map_room_updated", coord=coord, field="is_high_danger", value=val)
            elif action == "obstacle":
                try:
                    sp_val = max(0, int(rest[0]))
                except ValueError:
                    return get_locale_text("i18n_admin.err_int_required", value=rest[0])
                room.obstacle_sp = sp_val
                if sp_val > 0:
                    room.room_type = "obstacle"
                msg = get_locale_text("i18n_admin.map_room_updated", coord=coord, field="obstacle_sp", value=sp_val)
            elif action == "landmark":
                room.landmark_id = "" if rest[0].lower() in ("none", "clear") else rest[0]
                if room.landmark_id:
                    room.room_type = "landmark"
                msg = get_locale_text("i18n_admin.map_room_updated", coord=coord, field="landmark_id", value=room.landmark_id or "-")
            elif action in ("npc", "item", "prop") and len(rest) >= 2:
                op = rest[0].lower()
                query = rest[1]
                if action == "npc":
                    entry_id = resolve_npc(query) or query
                    target_list = room.npcs
                elif action == "prop":
                    entry_id = resolve_prop(query) or query
                    target_list = room.props
                else:
                    resolved_item = resolve_item(query)
                    entry_id = resolved_item[0] if resolved_item else query
                    target_list = room.items
                if op in ("add", "添加"):
                    target_list.append(entry_id)
                elif op in ("del", "remove", "rm", "移除"):
                    if entry_id in target_list:
                        target_list.remove(entry_id)
                else:
                    return get_locale_text("i18n_admin.detail_map")
                msg = get_locale_text("i18n_admin.map_room_updated", coord=coord, field=action, value=f"{op}:{entry_id}")
            else:
                return get_locale_text("i18n_admin.detail_map")

            ctx.save_manager.save_save(ctx.target_user_id, run)
            return get_locale_text(
                "i18n_cli_core.admin_action_result",
                msg=msg,
                rendered=GameRenderer.render_game(run),
            )

    async def _map_secret(self, ctx: AdminContext, args: list[str]) -> str:
        val = True if not args else parse_bool(args[0])
        if val is None:
            low = args[0].lower()
            if low == "unlock":
                val = True
            elif low == "lock":
                val = False
            else:
                return get_locale_text("i18n_admin.err_bool_required", value=args[0])
        async with ctx.lock():
            run = ctx.save_manager.load_save(ctx.target_user_id)
            if not run:
                return get_locale_text("i18n_cli_core.err_admin_no_save")
            fm = getattr(run, "floor_map", None)
            if fm is None:
                return get_locale_text("i18n_admin.err_no_floor_map")
            fm.secret_unlocked = val
            fm.secret_clue_found = val
            if val and fm.secret_boss_coord:
                if fm.secret_boss_coord not in fm.revealed_coords:
                    fm.revealed_coords.append(fm.secret_boss_coord)
                sroom = fm.rooms.get(fm.secret_boss_coord)
                if sroom is not None:
                    sroom.secret_unlocked = True
                    sroom.explored = True
            ctx.save_manager.save_save(ctx.target_user_id, run)
            msg = get_locale_text("i18n_admin.map_secret_updated", unlocked=val, coord=fm.secret_boss_coord or "-")
            return get_locale_text(
                "i18n_cli_core.admin_action_result",
                msg=msg,
                rendered=GameRenderer.render_game(run),
            )

    async def _map_regen(self, ctx: AdminContext) -> str:
        async with ctx.lock():
            run = ctx.save_manager.load_save(ctx.target_user_id)
            if not run:
                return get_locale_text("i18n_cli_core.err_admin_no_save")
            fm = getattr(run, "floor_map", None)
            floor_idx = fm.floor_index if fm is not None else 1
            run.floor_map = _build_floor_by_index(run, floor_idx, ctx.save_manager)
            SessionContextScoper.ensure_full_party_order(run)
            run.node_type = "grid_map"
            run.enemies.clear()
            run.node_data = {}
            ctx.save_manager.save_save(ctx.target_user_id, run)
            msg = get_locale_text("i18n_admin.map_regenerated", floor=floor_idx)
            return get_locale_text(
                "i18n_cli_core.admin_action_result",
                msg=msg,
                rendered=GameRenderer.render_game(run),
            )

    async def _map_exit(self, ctx: AdminContext) -> str:
        async with ctx.lock():
            run = ctx.save_manager.load_save(ctx.target_user_id)
            if not run:
                return get_locale_text("i18n_cli_core.err_admin_no_save")
            fm = getattr(run, "floor_map", None)
            if fm is not None:
                sid = fm.player_session_map.pop(ctx.target_user_id, None)
                if sid and sid in fm.active_sessions:
                    sess = fm.active_sessions[sid]
                    if ctx.target_user_id in sess.participants:
                        sess.participants.remove(ctx.target_user_id)
                    if not sess.participants:
                        fm.active_sessions.pop(sid, None)
            run.node_type = "grid_map"
            run.enemies.clear()
            run.node_data = {}
            ctx.save_manager.save_save(ctx.target_user_id, run)
            msg = get_locale_text("i18n_admin.map_exited")
            return get_locale_text(
                "i18n_cli_core.admin_action_result",
                msg=msg,
                rendered=GameRenderer.render_game(run),
            )
