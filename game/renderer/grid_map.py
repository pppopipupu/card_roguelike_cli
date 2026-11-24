from ..core.world.grid_map_generator import coord_to_xy, neighbors_4, xy_to_coord
from ..core.world.presence import render_players_for
from ..core.world.rooms.big_room import (
    get_big_room,
    get_big_room_icon,
    get_big_room_name,
    get_effective_alive_npcs,
    get_effective_interacted_props,
    get_effective_items,
    get_effective_props,
    is_big_room_direct_adjacent,
)
from ..core.world.rooms.hostile_npc import ensure_room_hostile_npcs, ensure_treasure_chest_prop
from ..data.world.grid_map_config import (
    DIRECT_REVEAL_ADJACENT_TYPES,
    FLOOR_CONFIGS,
    PERMANENT_ICON_TYPES,
    QUEST_RELIC_CONFIG,
    ROOM_ICONS,
    get_display_floor,
)
from ..data.text.locale_data import get_locale_text
from ..core.world.bleak_falls import BLEAK_LANDMARK_TYPES
from ..data.world.map_quest_config import ROOM_BLEAK_ENTRANCE
from ..models.state import GameRun
from .formatters import format_npcs_and_players_line, format_persistent_buff_bar, format_relic_bar
from .world_grid import render_grid_header, render_grid_view
def _visible_cell_icon(fm, coord: str, viewer_coord: str, adj_set: set[str]) -> str:
    room = fm.rooms.get(coord)
    if room is None:
        return ROOM_ICONS["fog"]
    revealed = coord in fm.revealed_coords or room.explored
    if coord == viewer_coord:
        return ROOM_ICONS["player"]
    if revealed:
        if room.room_type == "big_room":
            return get_big_room_icon(fm, room)
        if room.room_type == "secret_boss":
            return ROOM_ICONS["secret_boss"] if fm.secret_unlocked else ROOM_ICONS["wall"]
        if room.room_type in ("wall", "obstacle", "downstairs"):
            return ROOM_ICONS[room.room_type]
        if room.room_type in PERMANENT_ICON_TYPES:
            return ROOM_ICONS[room.room_type]
        if room.cleared:
            return ROOM_ICONS["cleared"]
        return ROOM_ICONS.get(room.room_type, ROOM_ICONS["unknown"])
    if coord in adj_set:
        if room.room_type == "big_room":
            return get_big_room_icon(fm, room) if is_big_room_direct_adjacent(fm, room) else ROOM_ICONS["unknown"]
        if room.room_type == "secret_boss":
            return ROOM_ICONS["secret_boss"] if fm.secret_unlocked else ROOM_ICONS["wall"]
        if room.room_type in ("wall", "obstacle"):
            return ROOM_ICONS[room.room_type]
        if room.room_type in DIRECT_REVEAL_ADJACENT_TYPES:
            return ROOM_ICONS[room.room_type]
        return ROOM_ICONS["unknown"]
    return ROOM_ICONS["fog"]


def _adjacent_to_revealed(fm) -> set[str]:
    adj = set()
    revealed = set(fm.revealed_coords or [])
    for c, r in fm.rooms.items():
        if r.explored:
            revealed.add(c)
    for rc in revealed:
        rx, ry = coord_to_xy(rc)
        if rx < 0:
            continue
        for nx, ny in neighbors_4(rx, ry, fm.width, fm.height):
            nc = xy_to_coord(nx, ny)
            if nc not in revealed:
                adj.add(nc)
    return adj


def render_grid_map(run: GameRun) -> str:
    from .party import render_party_status
    fm = getattr(run, "floor_map", None)
    p = run.player
    if fm is None:
        return get_locale_text("i18n_grid_map.err_no_floor_map")
    cfg = FLOOR_CONFIGS.get(fm.floor_index, FLOOR_CONFIGS[1])
    floor_name = get_locale_text(cfg["name_key"])
    uid = run.user_id
    viewer_coord = fm.player_coords.get(uid) or xy_to_coord(0, fm.height // 2)
    world_here = render_players_for(uid, run=run)
    adj_set = _adjacent_to_revealed(fm)
    relics_str = format_relic_bar(p.relics, getattr(p, "relic_counters", None))
    quest_str = ""
    if getattr(p, "quest_relics", None):
        qnames = []
        for qr in p.quest_relics:
            qcfg = QUEST_RELIC_CONFIG.get(qr, {})
            qname = get_locale_text(qcfg["name_key"]) if qcfg.get("name_key") else qr
            qnames.append(f"【{qname}】")
        quest_str = get_locale_text("i18n_grid_map.quest_relics_line", items=" ".join(qnames))

    pbuff_str = format_persistent_buff_bar(p)
    display_floor = get_display_floor(fm.floor_index)
    lines = [
        render_grid_header(display_floor, floor_name, viewer_coord),
        get_locale_text(
            "i18n_grid_map.header_status",
            name=p.name,
            hp=p.hp,
            max_hp=p.max_hp,
            gold=p.gold,
            sp=getattr(p, "sp", 10),
            max_sp=getattr(p, "max_sp", 10),
        ) + relics_str + pbuff_str,
    ]
    if quest_str:
        lines.append(quest_str)
    if run.player_count() > 1:
        lines.append(render_party_status(run))
    lines.append("")

    grid_lines, seen_icons = render_grid_view(
        fm.width,
        fm.height,
        viewer_coord,
        lambda c: _visible_cell_icon(fm, c, viewer_coord, adj_set),
    )
    lines.extend(grid_lines)
    lines.append("")

    legend_order = [
        ("player", "i18n_grid_map.legend.player"),
        ("fog", "i18n_grid_map.legend.fog"),
        ("wall", "i18n_grid_map.legend.wall"),
        ("obstacle", "i18n_grid_map.legend.obstacle"),
        ("unknown", "i18n_grid_map.legend.unknown"),
        ("cleared", "i18n_grid_map.legend.cleared"),
        ("battle", "i18n_grid_map.legend.battle"),
        ("elite", "i18n_grid_map.legend.elite"),
        ("high_danger", "i18n_grid_map.legend.high_danger"),
        ("treasure", "i18n_grid_map.legend.treasure"),
        ("cafe", "i18n_grid_map.legend.cafe"),
        ("shop", "i18n_grid_map.legend.shop"),
        ("rest", "i18n_grid_map.legend.rest"),
        ("landmark", "i18n_grid_map.legend.landmark"),
        ("life_merchant", "i18n_grid_map.legend.life_merchant"),
        ("boss", "i18n_grid_map.legend.boss"),
        ("downstairs", "i18n_grid_map.legend.downstairs"),
        ("secret_boss", "i18n_grid_map.legend.secret_boss"),
    ]
    legend_parts = []
    used_legend_icons = set()
    for k, lkey in legend_order:
        icon = ROOM_ICONS[k]
        if icon in seen_icons:
            legend_parts.append(f"{icon}{get_locale_text(lkey)}")
            used_legend_icons.add(icon)
    for br in (getattr(fm, "big_rooms", None) or {}).values():
        if not br.cells:
            continue
        rep_room = fm.rooms.get(br.cells[0])
        if rep_room is None:
            continue
        b_icon = get_big_room_icon(fm, rep_room)
        if b_icon in seen_icons and b_icon not in used_legend_icons:
            b_name = get_big_room_name(fm, rep_room)
            legend_parts.append(f"{b_icon}{b_name}")
            used_legend_icons.add(b_icon)
    if legend_parts:
        lines.append(get_locale_text("i18n_grid_map.legend_title") + " ".join(legend_parts))

    tp_entries = []
    for c, r in fm.rooms.items():
        if (r.explored or c in fm.revealed_coords) and r.room_type in PERMANENT_ICON_TYPES:
            tp_entries.append(f"{ROOM_ICONS[r.room_type]}{get_locale_text(f'i18n_grid_map.room_name.{r.room_type}')}({c})")
    if tp_entries:
        lines.append(get_locale_text("i18n_grid_map.revealed_facilities") + " ".join(tp_entries))

    cur_room = fm.rooms.get(viewer_coord)
    if cur_room is not None:
        lines.extend(_render_room_details(fm, cur_room, viewer_coord, p, world_here, run=run))
        eff_props = get_effective_props(fm, cur_room)
        eff_done = set(get_effective_interacted_props(fm, cur_room))
        if cur_room.room_type == "downstairs":
            if fm.floor_flags.get("yog_quest"):
                lines.append(get_locale_text("i18n_yog_quest.gate.hint"))
            else:
                lines.append(get_locale_text("i18n_grid_map.tunnel_hint"))
        elif "treasure_chest" in eff_props and "treasure_chest" not in eff_done:
            lines.append(get_locale_text("i18n_grid_map.treasure_hint"))
        elif cur_room.room_type == ROOM_BLEAK_ENTRANCE:
            lines.append(get_locale_text("i18n_bleak_falls.entrance.talk_hint"))
        elif cur_room.room_type in BLEAK_LANDMARK_TYPES or cur_room.landmark_id in BLEAK_LANDMARK_TYPES:
            lines.append(get_locale_text("i18n_bleak_falls.landmark_talk_hint"))
        elif cur_room.room_type == "landmark" or (viewer_coord == fm.ritual_coord and not fm.secret_unlocked):
            lines.append(get_locale_text("i18n_grid_map.talk_hint"))

    if p.fold_guide:
        lines.append(get_locale_text("i18n_grid_map.guide_folded"))
    else:
        lines.append(get_locale_text("i18n_grid_map.controls_hint"))
        lines.append(get_locale_text("i18n_room_interact.room_ui.interact_hints"))
    lines.append(get_locale_text("i18n_grid_map.separator"))
    return "\n".join(lines)


def render_landmark(run: GameRun) -> str:
    title = run.node_data.get("title", "")
    desc = run.node_data.get("desc", "")
    options = run.node_data.get("options", [])
    npcs_line = format_npcs_and_players_line(None, render_players_for(run.user_id, run=run))
    lines = [
        get_locale_text("i18n_grid_map.separator"),
        title,
        desc,
    ]
    if npcs_line:
        lines.append(npcs_line)
    lines.append("")
    for idx, opt in enumerate(options, 1):
        lines.append(f"  [{idx}] {opt.get('text', '')}")
    lines.append("")
    lines.append(get_locale_text("i18n_grid_map.guide_folded") if run.player.fold_guide else get_locale_text("i18n_grid_map.choose_hint"))
    lines.append(get_locale_text("i18n_grid_map.separator"))
    return "\n".join(lines)


def _render_downstairs_waiting(run: GameRun, npcs_line: str) -> str:
    fm = getattr(run, "floor_map", None)
    ready_map = fm.floor_flags.get("downstairs_ready", {}) if fm is not None else {}
    if not isinstance(ready_map, dict):
        ready_map = {}
    sep = get_locale_text("i18n_social.common.list_separator")
    ready_names: list[str] = []
    pending_names: list[str] = []
    for pid in run.all_human_uids():
        pl = run.players.get(pid)
        if pl is None or pl.downed or pl.hp <= 0:
            continue
        if ready_map.get(pid) or pid == run.user_id:
            ready_names.append(pl.name)
        else:
            coord = fm.player_coords.get(pid, "?") if fm is not None else "?"
            pending_names.append(f"{pl.name}({coord})")
    lines = [
        get_locale_text("i18n_grid_map.separator"),
        get_locale_text("i18n_grid_map.downstairs.waiting_title"),
        get_locale_text("i18n_grid_map.downstairs.waiting_desc"),
    ]
    if npcs_line:
        lines.append(npcs_line)
    lines.append("")
    if ready_names:
        lines.append(get_locale_text("i18n_grid_map.downstairs.ready_list", items=sep.join(ready_names)))
    if pending_names:
        lines.append(get_locale_text("i18n_grid_map.downstairs.pending_list", items=sep.join(pending_names)))
    lines.append("")
    lines.append(get_locale_text("i18n_grid_map.downstairs.waiting_hint"))
    lines.append(get_locale_text("i18n_grid_map.separator"))
    return "\n".join(lines)


def render_downstairs(run: GameRun) -> str:
    npcs_line = format_npcs_and_players_line(None, render_players_for(run.user_id, run=run))
    if run.node_data.get("coop_done"):
        return _render_downstairs_waiting(run, npcs_line)
    title = run.node_data.get("title", "")
    desc = run.node_data.get("desc", "")
    options = run.node_data.get("options", [])
    lines = [
        get_locale_text("i18n_grid_map.separator"),
        title,
        desc,
    ]
    if npcs_line:
        lines.append(npcs_line)
    lines.append("")
    for idx, opt in enumerate(options, 1):
        lines.append(f"  [{idx}] {opt.get('text', '')}")
    lines.append("")
    lines.append(get_locale_text("i18n_grid_map.guide_folded") if run.player.fold_guide else get_locale_text("i18n_grid_map.choose_hint"))
    lines.append(get_locale_text("i18n_grid_map.separator"))
    return "\n".join(lines)


def _describe_neighbor(fm, x: int, y: int, viewer_big_room_id: str = "") -> str:
    from ..data.world.room_interact_data import OBSTACLE_STYLES
    if not (0 <= x < fm.width and 0 <= y < fm.height):
        return get_locale_text("i18n_room_interact.dir.void_edge")
    coord = xy_to_coord(x, y)
    room = fm.rooms.get(coord)
    if room is None or room.room_type == "wall":
        return get_locale_text("i18n_room_interact.dir.wall")
    if room.room_type == "secret_boss" and not fm.secret_unlocked:
        return get_locale_text("i18n_room_interact.dir.secret_locked")
    revealed = coord in fm.revealed_coords or room.explored
    if viewer_big_room_id and getattr(room, "big_room_id", "") == viewer_big_room_id:
        return get_locale_text("i18n_big_room.ui.neighbor_same_room", name=get_big_room_name(fm, room))
    if room.room_type == "obstacle":
        style = room.obstacle_style or "collapsed_boulders"
        scfg = OBSTACLE_STYLES.get(style, OBSTACLE_STYLES["collapsed_boulders"])
        return get_locale_text("i18n_room_interact.dir.obstacle", name=get_locale_text(scfg["name_key"]))
    if not revealed:
        if room.room_type == "big_room" and is_big_room_direct_adjacent(fm, room):
            label = get_big_room_name(fm, room)
            return get_locale_text("i18n_room_interact.dir.room_open", room_label=label)
        if room.room_type in DIRECT_REVEAL_ADJACENT_TYPES:
            label = get_locale_text(f"i18n_grid_map.room_name.{room.room_type}")
            return get_locale_text("i18n_room_interact.dir.room_open", room_label=label)
        return get_locale_text("i18n_room_interact.dir.unexplored")
    if room.room_type == "big_room":
        label = get_big_room_name(fm, room)
        br = get_big_room(fm, room)
        if br is not None and br.cleared and not br.keep_icon_on_clear:
            return get_locale_text("i18n_room_interact.dir.room_cleared", room_label=label)
        return get_locale_text("i18n_room_interact.dir.room_open", room_label=label)
    label = get_locale_text(f"i18n_grid_map.room_name.{room.room_type}")
    if room.cleared and room.room_type not in PERMANENT_ICON_TYPES:
        return get_locale_text("i18n_room_interact.dir.room_cleared", room_label=label)
    return get_locale_text("i18n_room_interact.dir.room_open", room_label=label)


def _format_room_npc_label(nid: str, fm, cur_room, run=None) -> str:
    from ..data.world.room_interact_data import ROOM_NPCS
    if nid.startswith("cafe_guest:"):
        from ..data.world.cafe_data import NPC_SHOW_NAMES
        guest_key = nid.split(":", 1)[1]
        show = str(NPC_SHOW_NAMES.get(guest_key, guest_key))
        shared = (getattr(cur_room, "shared_payload", None) or {}).get("cafe_state")
        status = ""
        if isinstance(shared, dict):
            talked_npcs = shared.get("talked_npcs") or []
            talked_by = shared.get("talked_by") or {}
            active_by_npc = shared.get("active_by_npc") or {}
            players = getattr(run, "players", {}) or {} if run is not None else {}
            multi = run is not None and run.player_count() > 1
            if guest_key in talked_npcs:
                actor_uid = talked_by.get(guest_key)
                if multi and actor_uid in players:
                    status = get_locale_text("i18n_map_cafe.cafe_status_talked_by", name=players[actor_uid].name)
                else:
                    status = get_locale_text("i18n_map_cafe.cafe_status_talked")
            elif multi and active_by_npc.get(guest_key) in players:
                busy_uid = active_by_npc.get(guest_key)
                if fm is not None:
                    bsid = fm.player_session_map.get(busy_uid)
                    if bsid and bsid in fm.active_sessions and fm.active_sessions[bsid].node_type == "room_dialog":
                        status = get_locale_text("i18n_map_cafe.cafe_status_busy", name=players[busy_uid].name)
        return f"【{show}{status}】"
    return f"【{get_locale_text(ROOM_NPCS[nid]['name_key'])}】" if nid in ROOM_NPCS else nid


def _render_room_details(fm, cur_room, viewer_coord: str, player, world_players: list[dict] | None = None, run=None) -> list[str]:
    from ..core.inventory.bag_service import format_weight, get_bag_max_weight, get_bag_weight, get_item_display_name
    from ..core.world.rooms.interact import format_room_env_with_props
    ensure_room_hostile_npcs(fm, cur_room)
    ensure_treasure_chest_prop(cur_room)
    shared = getattr(cur_room, "shared_payload", None) or {}
    name_key = shared.get("name_key")
    out = [get_locale_text(name_key)] if name_key else []
    br = get_big_room(fm, cur_room)
    if br is not None:
        bname = get_big_room_name(fm, cur_room)
        out.append(get_locale_text("i18n_big_room.ui.room_banner", name=bname, coord=viewer_coord, count=len(br.cells)))
        if br.share_npcs and br.share_items:
            out.append(get_locale_text("i18n_big_room.ui.shared_hint_all_shared"))
        elif br.share_npcs:
            out.append(get_locale_text("i18n_big_room.ui.shared_hint_npcs_shared"))
        else:
            out.append(get_locale_text("i18n_big_room.ui.shared_hint_local"))
    out.append(format_room_env_with_props(cur_room, include_cleared_suffix=True, fm=fm))

    cx, cy = coord_to_xy(viewer_coord)
    viewer_br_id = getattr(cur_room, "big_room_id", "") or ""
    dirs = [
        ("i18n_room_interact.dir.north", cx, cy - 1),
        ("i18n_room_interact.dir.south", cx, cy + 1),
        ("i18n_room_interact.dir.west", cx - 1, cy),
        ("i18n_room_interact.dir.east", cx + 1, cy),
    ]
    dir_parts = [
        get_locale_text("i18n_room_interact.dir.entry", dir=get_locale_text(dkey), desc=_describe_neighbor(fm, nx, ny, viewer_big_room_id=viewer_br_id))
        for dkey, nx, ny in dirs
    ]
    out.append(get_locale_text("i18n_room_interact.dir.line_header") + " | ".join(dir_parts))

    alive_npcs = get_effective_alive_npcs(fm, cur_room)
    npc_names = [
        _format_room_npc_label(nid, fm, cur_room, run=run)
        for nid in alive_npcs
    ]
    ghost_names: list[str] = []
    if fm is not None and fm.floor_flags.get("yog_quest"):
        from ..core.world.open_world.ghost_service import OpenWorldGhostService
        from ..data.world.open_world_config import WORLD_YOG_TEMPLE
        from ..data.world.world_social_config import WORLD_SNOWFIELD
        from ..data.world.yog_quest_config import YOG_FLOOR_TEMPLE
        from ..models.manager import SaveManager

        world = WORLD_YOG_TEMPLE if fm.floor_index == YOG_FLOOR_TEMPLE else WORLD_SNOWFIELD
        ghost_names = OpenWorldGhostService.display_names_at(SaveManager(), world, viewer_coord)
        for gname in ghost_names:
            npc_names.append(f"【{gname}】")
    npcs_line = format_npcs_and_players_line(npc_names, world_players)
    if npcs_line:
        out.append(npcs_line)
    if ghost_names:
        sep = get_locale_text("i18n_social.common.list_separator")
        out.append(
            get_locale_text(
                "i18n_open_world.ghost_scene_hint",
                ghosts=sep.join(f"【{gname}】" for gname in ghost_names),
            )
        )

    items = get_effective_items(fm, cur_room)
    if items:
        item_names = [f"【{get_item_display_name(it)}】" for it in items]
        out.append(get_locale_text("i18n_room_interact.room_ui.items_line", items="、".join(item_names)))

    out.append(get_locale_text(
        "i18n_room_interact.bag.rogue_weight_line",
        used=format_weight(get_bag_weight(player)),
        max=get_bag_max_weight(player),
    ))
    return out
