from ..data.locale_data import get_locale_text
from ..data.outer_plane_config import (
    OUTER_PLANE_ROOMS,
    OUTER_PLANE_VISITED_KEY,
    OUTER_PLANE_WIP_ROOM,
    ZONE_NAME_KEYS,
    ZONE_ORDER,
)


def _zone_map(stats) -> str:
    visited = stats.town_flags.get(OUTER_PLANE_VISITED_KEY, [])
    lines = [get_locale_text("i18n_outer_plane.ui.map_title")]
    for zone in ZONE_ORDER:
        names = []
        for room_id, cfg in OUTER_PLANE_ROOMS.items():
            if cfg["zone"] != zone:
                continue
            if room_id in visited:
                names.append(get_locale_text(f"i18n_outer_plane.room.{room_id}.name"))
            else:
                names.append(get_locale_text("i18n_outer_plane.ui.room_unknown"))
        lines.append(get_locale_text(
            "i18n_outer_plane.ui.zone_row",
            zone=get_locale_text(ZONE_NAME_KEYS[zone]),
            rooms=" · ".join(names),
        ))
    return "\n".join(lines)


def render_outer_plane(stats, room_id, options, lucidity, max_lucidity, scene_text="", notice="") -> str:
    div = get_locale_text("i18n_outer_plane.ui.divider")
    if room_id == OUTER_PLANE_WIP_ROOM:
        sign = get_locale_text("i18n_outer_plane.ending.wip_sign")
        scene_text = sign + "\n\n" + scene_text if scene_text else sign
    lines = [div, get_locale_text("i18n_outer_plane.ui.title"), div, _zone_map(stats), div]
    if scene_text:
        lines.append(scene_text)
        lines.append("")
    lines.append(get_locale_text(f"i18n_outer_plane.room.{room_id}.desc"))
    lines.append("")
    lines.append(get_locale_text("i18n_outer_plane.ui.current", name=get_locale_text(f"i18n_outer_plane.room.{room_id}.name")))
    lines.append(get_locale_text("i18n_outer_plane.ui.lucidity", lucidity=lucidity, max=max_lucidity))
    lines.append(div)
    lines.append(get_locale_text("i18n_outer_plane.ui.options_header"))
    for num, label in options:
        lines.append(get_locale_text("i18n_outer_plane.ui.option_row", num=num, label=label))
    if notice:
        lines.append(notice)
    lines.append(div)
    lines.append(get_locale_text("i18n_outer_plane.ui.footer"))
    lines.append(div)
    return "\n".join(lines)
