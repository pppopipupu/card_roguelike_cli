from collections import Counter

from ....data.world.open_world_config import TOWN_CHEST_NPC_ID, TOWN_CHEST_TAB_KEY
from ....entities import get_relic_desc, get_relic_name
from ....models.state import UserStats
from ...inventory.bag_service import BAG_DEFAULT_MAX_WEIGHT, calc_bag_items_weight, can_add_bag_item, get_item_display_name, get_item_weight
from ...inventory.relic_service import init_relic_counter_map
from ...text.events import LocaleText
from ...text.pipeline import render_text_node


def _t(key: str, **params) -> str:
    return render_text_node(LocaleText(key=key, params=params))


def _grouped_items(items: list[str]) -> list[tuple[str, int]]:
    counts = Counter(items or [])
    result = [(item_id, count) for item_id, count in counts.items()]
    result.sort(key=lambda pair: (get_item_display_name(pair[0]), pair[0]))
    return result


def _chest_summary_lines(stats: UserStats) -> list[str]:
    chest_items = list(getattr(stats, "town_chest", []) or [])
    chest_relics = list(getattr(stats, "town_chest_relics", []) or [])
    lines = [
        _t("i18n_open_world.chest.title"),
        _t("i18n_open_world.chest.chest_items_header", count=len(chest_items)),
    ]
    if not chest_items and not chest_relics:
        lines.append(_t("i18n_open_world.chest.chest_empty"))
    else:
        for item_id, count in _grouped_items(chest_items):
            lines.append("   * " + _t("i18n_open_world.chest.display_item", name=get_item_display_name(item_id), count=count))
        if chest_relics:
            lines.append(_t("i18n_open_world.chest.chest_relics_header", count=len(chest_relics)))
            for rid in chest_relics:
                lines.append("   * " + _t("i18n_open_world.chest.display_relic", name=get_relic_name(rid)))
    bag_items = list(getattr(stats, "open_world_bag", []) or [])
    bag_relics = list(getattr(stats, "open_world_relics", []) or [])
    lines.append(
        _t(
            "i18n_open_world.chest.bag_items_header",
            weight=round(calc_bag_items_weight(bag_items), 1),
            max_weight=BAG_DEFAULT_MAX_WEIGHT,
            count=len(bag_items),
        )
    )
    if bag_relics:
        lines.append(_t("i18n_open_world.chest.bag_relics_header", count=len(bag_relics)))
    return lines


def _build_main_options(stats: UserStats) -> list[dict]:
    bag_items = list(getattr(stats, "open_world_bag", []) or [])
    chest_items = list(getattr(stats, "town_chest", []) or [])
    bag_relics = list(getattr(stats, "open_world_relics", []) or [])
    chest_relics = list(getattr(stats, "town_chest_relics", []) or [])
    options = []
    idx = 1
    if bag_items:
        options.append({"action": "tab_store_item", "text": f"[{idx}] {_t('i18n_open_world.chest.opt_store_item', count=len(bag_items))}"})
        idx += 1
    if chest_items:
        options.append({"action": "tab_take_item", "text": f"[{idx}] {_t('i18n_open_world.chest.opt_take_item', count=len(chest_items))}"})
        idx += 1
    if bag_items:
        options.append({"action": "store_all", "text": f"[{idx}] {_t('i18n_open_world.chest.opt_store_all')}"})
        idx += 1
    if bag_relics:
        options.append({"action": "tab_store_relic", "text": f"[{idx}] {_t('i18n_open_world.chest.opt_store_relic', count=len(bag_relics))}"})
        idx += 1
    if chest_relics:
        options.append({"action": "tab_take_relic", "text": f"[{idx}] {_t('i18n_open_world.chest.opt_take_relic', count=len(chest_relics))}"})
        idx += 1
    options.append({"action": "close", "text": f"[0] {_t('i18n_open_world.chest.opt_close')}"})
    return options


def build_chest_menu(stats: UserStats, zh_cn: dict) -> dict:
    tab = str(stats.town_flags.get(TOWN_CHEST_TAB_KEY, "main") or "main")
    npc_name = zh_cn.get("interactive_entities", {}).get(TOWN_CHEST_NPC_ID, {}).get("name", TOWN_CHEST_NPC_ID)
    summary = _chest_summary_lines(stats)
    options: list[dict] = []

    if tab in ("store_item", "take_item"):
        source = getattr(stats, "open_world_bag" if tab == "store_item" else "town_chest", []) or []
        grouped = _grouped_items(list(source))
        if not grouped:
            stats.town_flags[TOWN_CHEST_TAB_KEY] = "main"
            tab = "main"
        else:
            for idx, (item_id, count) in enumerate(grouped, start=1):
                row = _t(
                    "i18n_open_world.chest.item_row",
                    idx=idx,
                    name=get_item_display_name(item_id),
                    count=count,
                    weight=round(get_item_weight(item_id), 1),
                ).strip()
                options.append({"action": tab, "item_id": item_id, "text": row})
    elif tab in ("store_relic", "take_relic"):
        relics = list(getattr(stats, "open_world_relics" if tab == "store_relic" else "town_chest_relics", []) or [])
        if not relics:
            stats.town_flags[TOWN_CHEST_TAB_KEY] = "main"
            tab = "main"
        else:
            for idx, rid in enumerate(relics, start=1):
                row = _t(
                    "i18n_open_world.chest.relic_row",
                    idx=idx,
                    name=get_relic_name(rid),
                    desc=get_relic_desc(rid),
                ).strip()
                options.append({"action": tab, "relic_id": rid, "text": row})

    if tab == "main":
        options = _build_main_options(stats)
    else:
        options.append({"action": "back", "text": f"[0] {_t('i18n_open_world.chest.opt_back')}"})

    return {
        "npc_name": npc_name,
        "welcome": "\n".join(summary),
        "options": options,
    }


def process_chest_choice(town_engine, stats: UserStats, choice_lower: str, user_id: str, zh_cn: dict) -> str:
    menu = build_chest_menu(stats, zh_cn)
    options = menu["options"]
    selected = None
    if choice_lower in ("0", "leave", "exit", "quit", "离开", "退出", "关闭"):
        for opt in options:
            if opt["action"] in ("close", "back"):
                selected = opt
                break
    elif choice_lower.isdigit():
        num = int(choice_lower)
        non_zero = [opt for opt in options if opt["action"] not in ("close", "back")]
        if 1 <= num <= len(non_zero):
            selected = non_zero[num - 1]
    if selected is None:
        return _t("i18n_open_world.chest.msg_invalid_option") + "\n\n" + town_engine._render_dialog_window(stats, TOWN_CHEST_NPC_ID, zh_cn)

    action = selected["action"]
    if action == "close":
        stats.town_flags.pop("current_dialog", None)
        stats.town_flags.pop(TOWN_CHEST_TAB_KEY, None)
        town_engine.save_manager.save_stats(user_id, stats)
        return _t("i18n_open_world.chest.msg_closed") + "\n\n" + town_engine.render_current_room(user_id, stats)

    if action == "back":
        stats.town_flags[TOWN_CHEST_TAB_KEY] = "main"
        town_engine.save_manager.save_stats(user_id, stats)
        return town_engine._render_dialog_window(stats, TOWN_CHEST_NPC_ID, zh_cn)

    if action.startswith("tab_"):
        stats.town_flags[TOWN_CHEST_TAB_KEY] = action[4:]
        town_engine.save_manager.save_stats(user_id, stats)
        return town_engine._render_dialog_window(stats, TOWN_CHEST_NPC_ID, zh_cn)

    msg = ""
    if action == "store_all":
        bag_items = list(getattr(stats, "open_world_bag", []) or [])
        if not bag_items:
            msg = _t("i18n_open_world.chest.msg_store_empty")
        else:
            stats.town_chest.extend(bag_items)
            stats.open_world_bag = []
            msg = _t("i18n_open_world.chest.msg_stored_all", count=len(bag_items))
    elif action == "store_item":
        item_id = selected["item_id"]
        if item_id in stats.open_world_bag:
            stats.open_world_bag.remove(item_id)
            stats.town_chest.append(item_id)
            msg = _t("i18n_open_world.chest.msg_stored_item", name=get_item_display_name(item_id))
            if not stats.open_world_bag:
                stats.town_flags[TOWN_CHEST_TAB_KEY] = "main"
    elif action == "take_item":
        item_id = selected["item_id"]
        if item_id in stats.town_chest:
            if not can_add_bag_item(stats.open_world_bag, item_id, BAG_DEFAULT_MAX_WEIGHT):
                msg = _t("i18n_open_world.chest.msg_take_overweight", name=get_item_display_name(item_id), max_weight=BAG_DEFAULT_MAX_WEIGHT)
            else:
                stats.town_chest.remove(item_id)
                stats.open_world_bag.append(item_id)
                msg = _t("i18n_open_world.chest.msg_took_item", name=get_item_display_name(item_id))
                if not stats.town_chest:
                    stats.town_flags[TOWN_CHEST_TAB_KEY] = "main"
    elif action == "store_relic":
        rid = selected["relic_id"]
        if rid in stats.open_world_relics:
            stats.open_world_relics.remove(rid)
            stats.town_chest_relics.append(rid)
            if rid in stats.open_world_relic_counters:
                stats.town_chest_relic_counters[rid] = stats.open_world_relic_counters.pop(rid)
            msg = _t("i18n_open_world.chest.msg_stored_relic", name=get_relic_name(rid))
            if not stats.open_world_relics:
                stats.town_flags[TOWN_CHEST_TAB_KEY] = "main"
    elif action == "take_relic":
        rid = selected["relic_id"]
        if rid in stats.town_chest_relics:
            if rid in stats.open_world_relics:
                msg = _t("i18n_open_world.chest.msg_relic_already_owned", name=get_relic_name(rid))
            else:
                stats.town_chest_relics.remove(rid)
                stats.open_world_relics.append(rid)
                if rid in stats.town_chest_relic_counters:
                    stats.open_world_relic_counters[rid] = stats.town_chest_relic_counters.pop(rid)
                else:
                    init_relic_counter_map(stats.open_world_relic_counters, rid)
                msg = _t("i18n_open_world.chest.msg_took_relic", name=get_relic_name(rid))
                if not stats.town_chest_relics:
                    stats.town_flags[TOWN_CHEST_TAB_KEY] = "main"

    town_engine.save_manager.save_stats(user_id, stats)
    return msg + "\n\n" + town_engine._render_dialog_window(stats, TOWN_CHEST_NPC_ID, zh_cn)
