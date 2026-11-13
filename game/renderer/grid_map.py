from ..core.grid_map_generator import coord_to_xy, neighbors_4, xy_to_coord
from ..core.sp_system import format_exhaustion_effects
from ..data.grid_map_config import (
    DIRECT_REVEAL_ADJACENT_TYPES,
    FLOOR_CONFIGS,
    PERMANENT_ICON_TYPES,
    QUEST_RELIC_CONFIG,
    ROOM_ICONS,
)
from ..data.locale_data import get_locale_text
from ..entities import get_relic_name
from ..models.state import GameRun
from .formatters import format_relic_bar


def _visible_cell_icon(fm, coord: str, viewer_coord: str, other_coords: set[str], adj_set: set[str]) -> str:
    room = fm.rooms.get(coord)
    if room is None:
        return ROOM_ICONS["fog"]
    revealed = coord in fm.revealed_coords or room.explored
    if coord == viewer_coord:
        return ROOM_ICONS["player"]
    if coord in other_coords:
        return ROOM_ICONS["teammate"]
    if revealed:
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
    other_coords = {
        c for u, c in (fm.player_coords or {}).items()
        if u != uid and u in run.players and not getattr(run.players[u], "is_mercenary", False)
    }
    adj_set = _adjacent_to_revealed(fm)
    relics_str = format_relic_bar(p.relics)
    quest_str = ""
    if getattr(p, "quest_relics", None):
        qnames = []
        for qr in p.quest_relics:
            qcfg = QUEST_RELIC_CONFIG.get(qr, {})
            qname = get_locale_text(qcfg["name_key"]) if qcfg.get("name_key") else qr
            qnames.append(f"【{qname}】")
        quest_str = get_locale_text("i18n_grid_map.quest_relics_line", items=" ".join(qnames))

    ex_lvl = int(getattr(p, "exhaustion", 0) or 0)
    ex_desc = format_exhaustion_effects(ex_lvl)
    lines = [
        get_locale_text("i18n_grid_map.header_title", floor=fm.floor_index, floor_name=floor_name, coord=viewer_coord),
        get_locale_text(
            "i18n_grid_map.header_status",
            name=p.name,
            hp=p.hp,
            max_hp=p.max_hp,
            gold=p.gold,
            sp=getattr(p, "sp", 10),
            max_sp=getattr(p, "max_sp", 10),
            exhaustion=ex_lvl,
        ) + relics_str,
        get_locale_text("i18n_grid_map.exhaustion_line", level=ex_lvl, desc=ex_desc),
    ]
    if quest_str:
        lines.append(quest_str)
    if run.player_count() > 1:
        lines.append(render_party_status(run))
    lines.append("")

    col_headers = "   " + " ".join(chr(ord("A") + x) for x in range(fm.width))
    lines.append(col_headers)
    seen_icons = set()
    for y in range(fm.height):
        row_cells = []
        for x in range(fm.width):
            c = xy_to_coord(x, y)
            icon = _visible_cell_icon(fm, c, viewer_coord, other_coords, adj_set)
            seen_icons.add(icon)
            row_cells.append(icon)
        lines.append(f"{y + 1:>2} " + "".join(row_cells))
    lines.append("")

    legend_order = [
        ("player", "i18n_grid_map.legend.player"),
        ("teammate", "i18n_grid_map.legend.teammate"),
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
    for k, lkey in legend_order:
        icon = ROOM_ICONS[k]
        if icon in seen_icons:
            legend_parts.append(f"{icon}{get_locale_text(lkey)}")
    if legend_parts:
        lines.append(get_locale_text("i18n_grid_map.legend_title") + " ".join(legend_parts))

    tp_entries = []
    for c, r in fm.rooms.items():
        if (r.explored or c in fm.revealed_coords) and r.room_type in PERMANENT_ICON_TYPES:
            tp_entries.append(f"{ROOM_ICONS[r.room_type]}{get_locale_text(f'i18n_grid_map.room_name.{r.room_type}')}({c})")
    if tp_entries:
        lines.append(get_locale_text("i18n_grid_map.revealed_facilities") + " ".join(tp_entries))

    cur_room = fm.rooms.get(viewer_coord)
    if cur_room and (cur_room.room_type in ("landmark", "downstairs") or (viewer_coord == fm.ritual_coord and not fm.secret_unlocked)):
        lines.append(get_locale_text("i18n_grid_map.talk_hint"))

    if not p.fold_guide:
        lines.append(get_locale_text("i18n_grid_map.controls_hint"))
    lines.append(get_locale_text("i18n_grid_map.separator"))
    return "\n".join(lines)


def render_battle_prompt(run: GameRun) -> str:
    options = run.node_data.get("options", [])
    coord = run.node_data.get("coord", "")
    lines = [
        get_locale_text("i18n_grid_map.separator"),
        get_locale_text("i18n_grid_map.battle_prompt.title", coord=coord),
        get_locale_text("i18n_grid_map.battle_prompt.desc"),
        "",
    ]
    for idx, opt in enumerate(options, 1):
        lines.append(f"  [{idx}] {opt.get('text', '')}")
    lines.append("")
    lines.append(get_locale_text("i18n_grid_map.choose_hint"))
    lines.append(get_locale_text("i18n_grid_map.separator"))
    return "\n".join(lines)


def render_landmark(run: GameRun) -> str:
    title = run.node_data.get("title", "")
    desc = run.node_data.get("desc", "")
    options = run.node_data.get("options", [])
    lines = [
        get_locale_text("i18n_grid_map.separator"),
        title,
        desc,
        "",
    ]
    for idx, opt in enumerate(options, 1):
        lines.append(f"  [{idx}] {opt.get('text', '')}")
    lines.append("")
    lines.append(get_locale_text("i18n_grid_map.choose_hint"))
    lines.append(get_locale_text("i18n_grid_map.separator"))
    return "\n".join(lines)


def render_downstairs(run: GameRun) -> str:
    title = run.node_data.get("title", "")
    desc = run.node_data.get("desc", "")
    options = run.node_data.get("options", [])
    lines = [
        get_locale_text("i18n_grid_map.separator"),
        title,
        desc,
        "",
    ]
    for idx, opt in enumerate(options, 1):
        lines.append(f"  [{idx}] {opt.get('text', '')}")
    lines.append("")
    lines.append(get_locale_text("i18n_grid_map.choose_hint"))
    lines.append(get_locale_text("i18n_grid_map.separator"))
    return "\n".join(lines)
