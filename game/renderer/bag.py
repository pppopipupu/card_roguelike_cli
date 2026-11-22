from typing import Optional
from ..models.state import UserStats, GameRun
from ..entities import get_relic_desc, get_relic_name
from ..data.text.locale_data import get_locale_text
from ..data.world.room_interact_data import BAG_DEFAULT_MAX_WEIGHT
from ..core.inventory.bag_service import (
    calc_bag_items_weight,
    format_weight,
    get_bag_max_weight,
    get_bag_weight,
    get_item_desc,
    get_item_display_name,
    get_item_rarity_label,
    get_item_weight,
    is_item_carryover,
)
from ..core.world.open_world.loadout_service import is_open_world_run


def _render_open_world_bag(stats: UserStats, run: Optional[GameRun] = None, notice: str = "") -> str:
    if run is not None and run.player is not None and is_open_world_run(run):
        bag_items = list(getattr(run.player, "bag_items", None) or [])
        relics = list(getattr(run.player, "relics", None) or [])
        mx = get_bag_max_weight(run.player)
    else:
        bag_items = list(getattr(stats, "open_world_bag", None) or [])
        relics = list(getattr(stats, "open_world_relics", None) or [])
        mx = BAG_DEFAULT_MAX_WEIGHT
    used = calc_bag_items_weight(bag_items)
    lines = [
        get_locale_text("renderer_menu.separator_long"),
        get_locale_text("i18n_open_world.bag.title"),
        get_locale_text("renderer_menu.separator_long"),
    ]
    if notice:
        lines.append(notice)
        lines.append("")
    lines.append(get_locale_text("renderer_menu.bag_gp", gp=stats.gp))
    lines.append(get_locale_text("i18n_room_interact.bag.rogue_weight_line", used=format_weight(used), max=mx))
    lines.append("")
    lines.append(get_locale_text("i18n_room_interact.bag.rogue_items_section"))
    if bag_items:
        item_counts: dict[str, int] = {}
        for item_id in bag_items:
            item_counts[item_id] = item_counts.get(item_id, 0) + 1
        for item_id, count in item_counts.items():
            rarity_label = get_item_rarity_label(item_id)
            if count > 1:
                lines.append(get_locale_text("renderer_menu.bag_item_stacked_line", name=get_item_display_name(item_id), rarity=rarity_label, count=count))
            else:
                lines.append(get_locale_text("renderer_menu.bag_item_line", name=get_item_display_name(item_id), rarity=rarity_label))
            lines.append(get_locale_text("renderer_menu.bag_item_desc_line", desc=get_item_desc(item_id)))
    else:
        lines.append(get_locale_text("i18n_room_interact.bag.rogue_items_empty"))
    lines.append("")
    lines.append(get_locale_text("i18n_open_world.bag.relics_header", count=len(relics)))
    if relics:
        for rid in relics:
            lines.append(get_locale_text("i18n_open_world.bag.relic_entry", name=get_relic_name(rid), desc=get_relic_desc(rid)))
    else:
        lines.append(get_locale_text("i18n_open_world.bag.relics_empty"))
    lines.append(get_locale_text("renderer_menu.separator_long"))
    lines.append(get_locale_text("i18n_open_world.bag.tip"))
    lines.append(get_locale_text("renderer_menu.separator_long"))
    return "\n".join(lines)


def render_bag(stats: UserStats, run: Optional[GameRun] = None, mode: Optional[str] = None) -> str:
    open_world = is_open_world_run(run)
    if mode == "t":
        return _render_open_world_bag(
            stats,
            run=run if open_world else None,
            notice=get_locale_text("i18n_open_world.bag.town_moved_to_chest"),
        )
    if mode == "o" or (mode is None and (open_world or run is None or run.player is None)):
        return _render_open_world_bag(stats, run=run if open_world else None)
    if mode == "r" and open_world:
        return _render_open_world_bag(stats, run=run)

    lines = [
        get_locale_text("renderer_menu.separator_long"),
        get_locale_text("i18n_room_interact.bag.rogue_bag_title"),
        get_locale_text("renderer_menu.separator_long"),
    ]
    if run is None or run.player is None:
        lines.append(get_locale_text("i18n_room_interact.bag.rogue_bag_no_run"))
        lines.append(get_locale_text("renderer_menu.separator_long"))
        return "\n".join(lines)
    p = run.player
    used = get_bag_weight(p)
    mx = get_bag_max_weight(p)
    lines.append(get_locale_text("i18n_room_interact.bag.rogue_weight_line", used=format_weight(used), max=mx))
    lines.append("")
    lines.append(get_locale_text("i18n_room_interact.bag.rogue_items_section"))
    bag_items = list(getattr(p, "bag_items", None) or [])
    if bag_items:
        for item_id in bag_items:
            carry_tag = get_locale_text("i18n_room_interact.bag.carry_yes") if is_item_carryover(item_id) else get_locale_text("i18n_room_interact.bag.carry_no")
            lines.append(get_locale_text(
                "i18n_room_interact.bag.rogue_item_line",
                name=get_item_display_name(item_id),
                rarity=get_item_rarity_label(item_id),
                weight=format_weight(get_item_weight(item_id)),
                carry_tag=carry_tag,
                desc=get_item_desc(item_id),
            ))
    else:
        lines.append(get_locale_text("i18n_room_interact.bag.rogue_items_empty"))
    lines.append(get_locale_text("renderer_menu.separator_long"))
    lines.append(get_locale_text("i18n_room_interact.bag.rogue_bag_tip"))
    lines.append(get_locale_text("renderer_menu.separator_long"))
    return "\n".join(lines)
