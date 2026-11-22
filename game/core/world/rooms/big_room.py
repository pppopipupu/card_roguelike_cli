import random
from ....data.world.big_room_config import (
    BIG_ROOM_MAX_DIM,
    BIG_ROOM_MIN_DIM,
    BIG_ROOM_TEMPLATES,
    compute_offsets_bbox,
    is_valid_big_room_offsets,
)
from ....data.world.grid_map_config import ROOM_ICONS
from ....data.text.locale_data import get_locale_text
from ....models.state import BigRoomState, RoomState
from ..grid_map_generator import coord_to_xy


def get_big_room(fm, room_or_coord) -> BigRoomState | None:
    if fm is None or room_or_coord is None:
        return None
    if isinstance(room_or_coord, str):
        room = fm.rooms.get(room_or_coord)
    else:
        room = room_or_coord
    if room is None:
        return None
    gid = getattr(room, "big_room_id", "") or ""
    if not gid:
        return None
    return (getattr(fm, "big_rooms", None) or {}).get(gid)


def get_big_room_template(big_room: BigRoomState | None) -> dict:
    if big_room is None:
        return {}
    return BIG_ROOM_TEMPLATES.get(big_room.template_id, {})


def get_big_room_name(fm, room: RoomState | None) -> str:
    br = get_big_room(fm, room)
    if br is None:
        return ""
    tpl = get_big_room_template(br)
    name_key = tpl.get("name_key", "")
    if name_key:
        return get_locale_text(name_key)
    return get_locale_text("i18n_grid_map.room_name.big_room")


def get_big_room_icon(fm, room: RoomState | None, cleared_override: bool | None = None) -> str:
    br = get_big_room(fm, room)
    if br is None:
        return ROOM_ICONS["big_room"]
    tpl = get_big_room_template(br)
    is_cleared = br.cleared if cleared_override is None else cleared_override
    if is_cleared and not br.keep_icon_on_clear:
        return ROOM_ICONS["cleared"]
    return str(tpl.get("icon") or ROOM_ICONS["big_room"])


def is_big_room_direct_adjacent(fm, room: RoomState | None) -> bool:
    br = get_big_room(fm, room)
    if br is None:
        return False
    tpl = get_big_room_template(br)
    return bool(tpl.get("direct_reveal_adjacent", False))


def get_effective_npcs(fm, room: RoomState | None) -> list[str]:
    if room is None:
        return []
    br = get_big_room(fm, room)
    if br is not None and br.share_npcs:
        return list(br.npcs)
    return list(getattr(room, "npcs", None) or [])


def get_effective_defeated_npcs(fm, room: RoomState | None) -> list[str]:
    if room is None:
        return []
    br = get_big_room(fm, room)
    if br is not None and br.share_npcs:
        return list(br.defeated_npcs)
    return list(getattr(room, "defeated_npcs", None) or [])


def get_effective_alive_npcs(fm, room: RoomState | None) -> list[str]:
    defeated = set(get_effective_defeated_npcs(fm, room))
    return [nid for nid in get_effective_npcs(fm, room) if nid not in defeated]


def get_effective_items(fm, room: RoomState | None) -> list[str]:
    if room is None:
        return []
    br = get_big_room(fm, room)
    if br is not None and br.share_items:
        return list(br.items)
    return list(getattr(room, "items", None) or [])


def get_effective_props(fm, room: RoomState | None) -> list[str]:
    if room is None:
        return []
    br = get_big_room(fm, room)
    if br is not None and br.share_props:
        return list(br.props)
    return list(getattr(room, "props", None) or [])


def get_effective_interacted_props(fm, room: RoomState | None) -> list[str]:
    if room is None:
        return []
    br = get_big_room(fm, room)
    if br is not None and br.share_props:
        return list(br.interacted_props)
    return list(getattr(room, "interacted_props", None) or [])


def add_effective_item(fm, room: RoomState | None, item_id: str) -> None:
    if room is None or not item_id:
        return
    br = get_big_room(fm, room)
    if br is not None and br.share_items:
        br.items.append(item_id)
    else:
        room.items.append(item_id)


def remove_effective_item(fm, room: RoomState | None, item_id: str) -> bool:
    if room is None or not item_id:
        return False
    br = get_big_room(fm, room)
    target = br.items if (br is not None and br.share_items) else room.items
    if item_id in target:
        target.remove(item_id)
        return True
    return False


def mark_effective_prop_interacted(fm, room: RoomState | None, prop_id: str) -> None:
    if room is None or not prop_id:
        return
    br = get_big_room(fm, room)
    target = br.interacted_props if (br is not None and br.share_props) else room.interacted_props
    if prop_id not in target:
        target.append(prop_id)


def mark_effective_npc_defeated(fm, room: RoomState | None, npc_id: str) -> None:
    if room is None or not npc_id:
        return
    br = get_big_room(fm, room)
    if br is not None and br.share_npcs:
        if npc_id not in br.defeated_npcs:
            br.defeated_npcs.append(npc_id)
    else:
        if npc_id not in room.defeated_npcs:
            room.defeated_npcs.append(npc_id)


def sync_big_room_clear_state(fm, room: RoomState | None) -> None:
    if fm is None or room is None:
        return
    br = get_big_room(fm, room)
    if br is None:
        return
    from .hostile_npc import get_alive_hostile_npcs
    if br.share_npcs:
        alive_hostiles = get_alive_hostile_npcs(fm, room)
        if not alive_hostiles:
            any_cleared = any(fm.rooms[c].cleared for c in br.cells if c in fm.rooms)
            if br.cleared or any_cleared:
                br.cleared = True
                for c in br.cells:
                    if c in fm.rooms:
                        fm.rooms[c].cleared = True
        else:
            br.cleared = False
    else:
        br.cleared = all(
            (c in fm.rooms and fm.rooms[c].cleared)
            for c in br.cells
        )


def reveal_big_room_if_needed(fm, coord: str, force_whole: bool = False) -> list[str]:
    if fm is None or coord not in fm.rooms:
        return []
    room = fm.rooms[coord]
    revealed_now: list[str] = []
    br = get_big_room(fm, room)
    if br is not None and (br.reveal_mode == "whole" or force_whole):
        for c in br.cells:
            cell_room = fm.rooms.get(c)
            if cell_room is not None and not cell_room.explored:
                cell_room.explored = True
            if c not in fm.revealed_coords:
                fm.revealed_coords.append(c)
                revealed_now.append(c)
        return revealed_now
    if not room.explored:
        room.explored = True
    if coord not in fm.revealed_coords:
        fm.revealed_coords.append(coord)
        revealed_now.append(coord)
    return revealed_now


def create_big_room_instance(
    fm,
    group_id: str,
    template_id: str,
    cells: list[str],
    rng: random.Random | None = None,
) -> BigRoomState:
    if fm is None:
        raise ValueError("FloorMapState is required")
    tpl = BIG_ROOM_TEMPLATES[template_id]
    offsets = []
    for c in cells:
        xy = coord_to_xy(c)
        if xy[0] < 0 or xy[1] < 0:
            raise ValueError(f"Invalid coordinate: {c}")
        offsets.append(xy)
    if not is_valid_big_room_offsets(offsets):
        raise ValueError("Big room cells must be connected and within 1..10 bbox")
    bbox_w, bbox_h = compute_offsets_bbox(offsets)
    if not (BIG_ROOM_MIN_DIM <= bbox_w <= BIG_ROOM_MAX_DIM and BIG_ROOM_MIN_DIM <= bbox_h <= BIG_ROOM_MAX_DIM):
        raise ValueError("Big room bbox out of bounds")
    r = rng or random.Random()
    share_npcs = bool(tpl.get("share_npcs", True))
    share_items = bool(tpl.get("share_items", False))
    share_props = bool(tpl.get("share_props", False))
    br = BigRoomState(
        group_id=group_id,
        template_id=template_id,
        cells=list(cells),
        width=bbox_w,
        height=bbox_h,
        reveal_mode=str(tpl.get("reveal_mode", "whole")),
        share_npcs=share_npcs,
        share_items=share_items,
        share_props=share_props,
        keep_icon_on_clear=bool(tpl.get("keep_icon_on_clear", True)),
        npcs=list(tpl.get("shared_npcs", [])) if share_npcs else [],
        items=list(tpl.get("shared_items", [])) if share_items else [],
        props=list(tpl.get("shared_props", [])) if share_props else [],
        cleared=False,
    )
    fm.big_rooms[group_id] = br
    env_id = str(tpl.get("env_id", "big_armory_hall"))
    for c in cells:
        room = fm.rooms.get(c)
        if room is None:
            room = RoomState(coord=c, room_type="big_room")
            fm.rooms[c] = room
        room.room_type = "big_room"
        room.big_room_id = group_id
        room.env_id = env_id
        room.cleared = False
        room.npcs = []
        room.defeated_npcs = []
        room.items = []
        room.props = []
        room.interacted_props = []

    cell_list = list(cells)
    if not share_npcs and tpl.get("cell_hostile_pool"):
        h_pool = list(tpl["cell_hostile_pool"])
        cmin, cmax = tpl.get("cell_hostile_count", (1, 1))
        h_count = min(len(cell_list), r.randint(int(cmin), int(cmax)))
        picked = r.sample(cell_list, h_count)
        for hc in picked:
            fm.rooms[hc].npcs.append(r.choice(h_pool))

    guaranteed_prop = tpl.get("guaranteed_cell_prop", "")
    if guaranteed_prop and not share_props:
        safe_cells = [c for c in cell_list if not fm.rooms[c].npcs]
        target_cell = r.choice(safe_cells or cell_list)
        if guaranteed_prop not in fm.rooms[target_cell].props:
            fm.rooms[target_cell].props.append(guaranteed_prop)

    item_pool = list(tpl.get("item_pool") or [])
    prop_pool = list(tpl.get("prop_pool") or [])
    item_chance = float(tpl.get("item_chance_per_cell", 0.0))
    prop_chance = float(tpl.get("prop_chance_per_cell", 0.0))
    for idx, c in enumerate(cell_list):
        room = fm.rooms[c]
        if not share_items and item_pool:
            if r.random() < item_chance or (idx == 0 and item_chance > 0):
                room.items.append(item_pool[idx % len(item_pool)] if idx < len(item_pool) else r.choice(item_pool))
        if not share_props and prop_pool:
            if r.random() < prop_chance:
                p_pick = prop_pool[idx % len(prop_pool)] if idx < len(prop_pool) else r.choice(prop_pool)
                if p_pick not in room.props:
                    room.props.append(p_pick)
    return br
