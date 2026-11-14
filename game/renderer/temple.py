from ..data.locale_data import get_locale_text
from ..data.temple_config import (
    TEMPLE_HP_KEY,
    TEMPLE_MAX_HP_KEY,
    TEMPLE_ROOMS,
    TEMPLE_VISITED_KEY,
    ZONE_NAME_KEYS,
    ZONE_ORDER,
)


def _zone_map(stats) -> str:
    visited = stats.town_flags.get(TEMPLE_VISITED_KEY, [])
    lines = [get_locale_text("i18n_temple.ui.map_title")]
    for zone in ZONE_ORDER:
        names = []
        for room_id, cfg in TEMPLE_ROOMS.items():
            if cfg["zone"] != zone:
                continue
            if room_id in visited:
                names.append(get_locale_text(f"i18n_temple.room.{room_id}.name"))
            else:
                names.append(get_locale_text("i18n_temple.ui.room_unknown"))
        lines.append(get_locale_text(
            "i18n_temple.ui.zone_row",
            zone=get_locale_text(ZONE_NAME_KEYS[zone]),
            rooms=" · ".join(names),
        ))
    return "\n".join(lines)


def render_temple(stats, room_id: str, options, scene_text: str = "", notice: str = "") -> str:
    div = get_locale_text("i18n_temple.ui.divider")
    hp = int(stats.town_flags.get(TEMPLE_HP_KEY, 0) or 0)
    max_hp = int(stats.town_flags.get(TEMPLE_MAX_HP_KEY, hp) or hp)
    lines = [div, get_locale_text("i18n_temple.ui.title"), div, _zone_map(stats), div]
    if scene_text:
        lines.append(scene_text)
        lines.append("")
    lines.append(get_locale_text(f"i18n_temple.room.{room_id}.desc"))
    lines.append("")
    lines.append(get_locale_text("i18n_temple.ui.current", name=get_locale_text(f"i18n_temple.room.{room_id}.name")))
    lines.append(get_locale_text("i18n_temple.ui.hp", hp=hp, max_hp=max_hp))
    lines.append(div)
    lines.append(get_locale_text("i18n_temple.ui.options_header"))
    for num, label in options:
        lines.append(get_locale_text("i18n_temple.ui.option_row", num=num, label=label))
    if notice:
        lines.append(notice)
    lines.append(div)
    lines.append(get_locale_text("i18n_temple.ui.footer"))
    lines.append(div)
    return "\n".join(lines)
