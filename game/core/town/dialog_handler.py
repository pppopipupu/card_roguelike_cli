import random
from typing import Any, Callable, Dict, List, Optional

from ...models.state import UserStats
from ...cards import ALL_CARDS
from ...entities.cards.market import get_market_price
from ...data.locale_data import get_locale_text
from ...data.starting_deck_config import LOCK_PRICE_GP, LOCK_SLOT_LIMIT


def _option(action: Optional[str], label: Any, condition: Optional[Callable[[UserStats], bool]] = None, target: Any = None, prefix: bool = True, selectable: bool = True) -> Dict[str, Any]:
    return {"action": action, "label": label, "condition": condition, "target": target, "prefix": prefix, "selectable": selectable}


def _global_label(key: str, default: str = "") -> tuple:
    return ("global", key, default)


def _npc_label(key: str, default: Any = None) -> tuple:
    return ("npc", key, default)


def _text_label(text: str) -> tuple:
    return ("text", text)


def _resolve_label(label: Any, stats: UserStats, npc_data: Dict[str, Any], zh_cn: Dict[str, Any], number: int) -> str:
    if callable(label):
        return label(stats, npc_data, zh_cn, number)
    kind = label[0]
    if kind == "text":
        return label[1]
    if kind == "npc":
        key = label[1]
        default = label[2] if len(label) > 2 else None
        if isinstance(default, tuple) and default and default[0] == "global":
            global_default = default[2] if len(default) > 2 else ""
            default = get_locale_text(f"global.{default[1]}", global_default)
        if default is None:
            return npc_data.get(key, "")
        return npc_data.get(key, default)
    if kind == "global":
        default = label[2] if len(label) > 2 else ""
        return get_locale_text(f"global.{label[1]}", default)
    return ""


def _materialize_options(specs: List[Dict[str, Any]], stats: UserStats, npc_data: Dict[str, Any], zh_cn: Dict[str, Any]) -> List[Dict[str, Any]]:
    options = []
    number = 0
    for spec in specs:
        condition = spec.get("condition")
        if condition is not None and not condition(stats):
            continue
        selectable = spec.get("selectable", True)
        if selectable:
            number += 1
            current = number
        else:
            current = None
        text = _resolve_label(spec.get("label"), stats, npc_data, zh_cn, current)
        if selectable and spec.get("prefix", True):
            text = f"{current}. {text}"
        target = spec.get("target")
        if callable(target):
            target = target(stats)
        options.append({"number": current, "text": text, "action": spec.get("action"), "target": target})
    return options


def _normal_specs(npc_id: str) -> List[Dict[str, Any]]:
    specs = []
    specs.append(_option(
        "idle",
        _npc_label("option_idle", _global_label("idle_talk_default", get_locale_text("global.idle_talk_default"))),
        condition=lambda s: npc_id not in ("Chest", "Fountain", "West_Gate") and not (npc_id == "Crypto_Whale" and s.town_flags.get("reported_whale")),
    ))

    if npc_id == "Guide_Elder":
        specs.append(_option("quest_accept", _npc_label("option_quest_accept"), condition=lambda s: s.town_flags.get("quest_town_tour_state", "unstarted") == "unstarted"))
        specs.append(_option("quest_status", _npc_label("option_quest_status"), condition=lambda s: s.town_flags.get("quest_town_tour_state", "unstarted") == "started" and len(s.town_flags.get("quest_town_tour_visited", [])) < 11))
        specs.append(_option("quest_complete", _npc_label("option_quest_complete"), condition=lambda s: s.town_flags.get("quest_town_tour_state", "unstarted") == "started" and len(s.town_flags.get("quest_town_tour_visited", [])) >= 11))
    elif npc_id == "Bartender_Jack":
        specs.append(_option("gift_glass", _npc_label("option_gift_glass"), condition=lambda s: "wine_glass" in s.town_inventory and not s.town_flags.get("jack_gift_given", 0)))
        specs.append(_option("buy_beer", _npc_label("option_buy_beer")))
        specs.append(_option("brew_quest_accept", _npc_label("option_brew_quest_accept"), condition=lambda s: s.town_flags.get("quest_brew_state", "unstarted") == "unstarted"))
        specs.append(_option("give_wishing_dew", _npc_label("option_give_wishing_dew"), condition=lambda s: s.town_flags.get("quest_brew_state", "unstarted") == "started" and "wishing_dew" in s.town_inventory))
        specs.append(_option("dialog_sign_agreement", _npc_label("option_dialog_sign_agreement"), condition=lambda s: s.town_flags.get("quest_brew_state", "unstarted") == "started" and "promotional_agreement" not in s.town_inventory and "void_herb" not in s.town_inventory and "wishing_dew" not in s.town_inventory))
    elif npc_id == "Blacksmith_Ironclad":
        specs.append(_option("gift_ore", _npc_label("option_gift_ore"), condition=lambda s: "strange_ore" in s.town_inventory and not s.town_flags.get("ironclad_gift_given", 0)))
        specs.append(_option("quest_hammer_accept", _npc_label("option_quest_hammer_accept"), condition=lambda s: s.town_flags.get("quest_hammer_state", "unstarted") == "unstarted"))
        specs.append(_option("quest_hammer_return_force", _npc_label("option_return_hammer_force"), condition=lambda s: s.town_flags.get("quest_hammer_state", "unstarted") == "started" and bool(s.town_flags.get("noob_coerced_hammer"))))
        specs.append(_option("quest_hammer_return_real", _npc_label("option_return_hammer_real"), condition=lambda s: s.town_flags.get("quest_hammer_state", "unstarted") == "started" and not s.town_flags.get("noob_coerced_hammer") and "smith_hammer" in s.town_inventory))
        specs.append(_option("quest_hammer_return_fake", _npc_label("option_return_hammer_fake"), condition=lambda s: s.town_flags.get("quest_hammer_state", "unstarted") == "started" and "fake_hammer" in s.town_inventory))
        specs.append(_option("quest_hammer_clue", _npc_label("option_quest_hammer_clue"), condition=lambda s: s.town_flags.get("quest_hammer_state", "unstarted") == "started"))
    elif npc_id == "Market_Merchant":
        specs.append(_option("buy_shelf", _npc_label("option_buy_shelf")))
        specs.append(_option("lock_card", _npc_label("option_lock_card")))
    elif npc_id == "Shopkeeper_Jack":
        specs.append(_option("buy_subclass", _npc_label("option_buy_subclass", get_locale_text("i18n_town.option_buy_subclass"))))
        specs.append(_option("sell_wishing_dew", _npc_label("option_sell_wishing_dew"), condition=lambda s: s.town_flags.get("quest_brew_state", "unstarted") == "started" and "wishing_dew" in s.town_inventory))
    elif npc_id == "Lost_Bard":
        specs.append(_option("ask_hammer", _npc_label("option_ask_hammer"), condition=lambda s: s.town_flags.get("quest_hammer_state", "unstarted") == "started" and not s.town_flags.get("taken_smith_hammer") and not s.town_flags.get("noob_coerced_hammer")))
        specs.append(_option("give_beer", _npc_label("option_give_beer"), condition=lambda s: s.town_flags.get("quest_hammer_state", "unstarted") == "started" and not s.town_flags.get("taken_smith_hammer") and not s.town_flags.get("noob_coerced_hammer") and "beer" in s.town_inventory))
    elif npc_id == "Crypto_Whale":
        specs.append(_option("buy_fake_hammer", _npc_label("option_buy_fake_hammer"), condition=lambda s: not s.town_flags.get("reported_whale") and s.town_flags.get("quest_hammer_state", "unstarted") == "started" and "smith_hammer" not in s.town_inventory and "fake_hammer" not in s.town_inventory and not s.town_flags.get("noob_coerced_hammer")))
        specs.append(_option("buy_void_herb", _npc_label("option_buy_void_herb"), condition=lambda s: not s.town_flags.get("reported_whale") and s.town_flags.get("quest_brew_state", "unstarted") == "started" and "void_herb" not in s.town_inventory and "wishing_dew" not in s.town_inventory))
        specs.append(_option("trade_void_herb", _npc_label("option_trade_void_herb"), condition=lambda s: not s.town_flags.get("reported_whale") and s.town_flags.get("quest_brew_state", "unstarted") == "started" and "void_herb" not in s.town_inventory and "wishing_dew" not in s.town_inventory and "promotional_agreement" in s.town_inventory))
    elif npc_id == "Town_Guard":
        specs.append(_option("report_whale", _npc_label("option_report_whale"), condition=lambda s: s.town_flags.get("quest_brew_state", "unstarted") == "started" and "void_herb" not in s.town_inventory and "wishing_dew" not in s.town_inventory and not s.town_flags.get("reported_whale")))
    elif npc_id == "Chest":
        specs.append(_option("open_box", _npc_label("option_open"), condition=lambda s: "rusty_key" in s.town_inventory and not s.town_flags.get("box_opened", 0)))
    elif npc_id == "Fountain":
        specs.append(_option("wish", _npc_label("option_wish"), condition=lambda s: "lucky_coin" in s.town_inventory))
        specs.append(_option("wash_herb", _npc_label("option_wash_herb"), condition=lambda s: s.town_flags.get("quest_brew_state", "unstarted") == "started" and "void_herb" in s.town_inventory))
    elif npc_id == "West_Gate":
        specs.append(_option("knock", _npc_label("option_knock")))
    elif npc_id in ("Dummy", "NoobSlayer99", "xXx_SniperElite_xXx", "pppopipupu"):
        specs.append(_option("challenge", _npc_label("option_challenge")))

    specs.append(_option("leave", _npc_label("option_leave", _global_label("leave_default", get_locale_text("global.leave_default")))))
    return specs


def _riddle_specs(step: Any) -> List[Dict[str, Any]]:
    answers = []
    if step == 1:
        answers = [
            get_locale_text("i18n_town.riddle_soda"),
            get_locale_text("i18n_town.riddle_salary"),
            get_locale_text("i18n_town.riddle_well"),
            get_locale_text("i18n_town.riddle_tears"),
        ]
    elif step == 2:
        answers = [
            get_locale_text("i18n_town.riddle_smith"),
            get_locale_text("i18n_town.riddle_snowman"),
            get_locale_text("i18n_town.riddle_guard"),
            get_locale_text("i18n_town.riddle_poet"),
        ]
    specs = [_option("riddle_answer", _text_label(text), target=index + 1) for index, text in enumerate(answers)]
    specs.append(_option("back_riddle", _global_label("back_to_previous", get_locale_text("global.back_to_previous"))))
    return specs


def _agreement_specs(stats: UserStats) -> List[Dict[str, Any]]:
    specs = []
    if "lost_notebook" in stats.town_inventory:
        specs.append(_option("agreement_notebook", _npc_label("option_sign_by_notebook")))
    specs.append(_option("agreement_riddle", _npc_label("option_sign_by_riddle")))
    specs.append(_option("back_agreement", _global_label("back_to_previous", get_locale_text("global.back_to_previous"))))
    return specs


def _market_buy_label(cid: str) -> Callable:
    def label(stats: UserStats, npc_data: Dict[str, Any], zh_cn: Dict[str, Any], number: int) -> str:
        c_name = ALL_CARDS[cid].name if cid in ALL_CARDS else cid
        card_obj = ALL_CARDS.get(cid)
        rarity_str = get_locale_text("renderer_town.rarity_common")
        if card_obj:
            rarity = getattr(card_obj, "rarity", "common")
            if rarity == "common":
                rarity_str = get_locale_text("renderer_town.rarity_common")
            elif rarity == "rare":
                rarity_str = get_locale_text("renderer_town.rarity_rare")
            else:
                rarity_str = get_locale_text("renderer_town.rarity_epic")
        price = get_market_price(cid, card_obj)
        return get_locale_text("global.market_buy_option", idx=number, name=c_name, rarity=rarity_str, price=price)
    return label


def _market_buy_specs(town_engine, stats: UserStats) -> List[Dict[str, Any]]:
    shelf = town_engine._get_market_shelf(stats)
    specs = []
    for index, cid in enumerate(shelf):
        if not cid:
            specs.append(_option("market_buy", _global_label("market_sold_out", get_locale_text("global.market_sold_out")), target=index))
        else:
            specs.append(_option("market_buy", _market_buy_label(cid), target=index, prefix=False))
    specs.append(_option("back_market_buy", _global_label("back_to_previous", get_locale_text("global.back_to_previous"))))
    return specs


def _shop_items(stats: UserStats) -> List[Dict[str, Any]]:
    from ...models.manager import SaveManager
    boss_cfg = SaveManager().load_admin_config()
    icerainboww_enabled = boss_cfg.get("icerainboww_enabled", True)
    from ...data.shop_data import SHOP_ITEMS
    unlocked = getattr(stats, "unlocked_subclasses", [])
    has_gatekey = getattr(stats, "unlocked_gatekey", False)
    items = [
        {"name": "时序法师", "price": SHOP_ITEMS["时序法师"]["price"], "is_unlocked": "时序法师" in unlocked, "buyable": True},
        {"name": "塑能法师", "price": SHOP_ITEMS["塑能法师"]["price"], "is_unlocked": "塑能法师" in unlocked, "buyable": True},
        {"name": "秘钥学者", "price": SHOP_ITEMS["秘钥学者"]["price"], "is_unlocked": "秘钥学者" in unlocked, "buyable": True},
        {"name": "门之钥匙", "price": SHOP_ITEMS["门之钥匙"]["price"], "is_unlocked": has_gatekey, "buyable": True},
        {"name": "神秘物品", "price": SHOP_ITEMS["神秘物品"]["price"], "is_unlocked": "神秘物品" in unlocked, "buyable": True},
    ]
    if icerainboww_enabled:
        killed_icerainboww = getattr(stats, "killed_icerainboww", False)
        items.append({"name": "Icerainboww" if killed_icerainboww else get_locale_text("i18n_town.shop_hidden_name"), "price": None, "is_unlocked": killed_icerainboww, "buyable": False})
    killed_yog = getattr(stats, "yog_sothoth_kill_count", 0) > 0
    items.append({"name": get_locale_text("i18n_town.shop_yog_name") if killed_yog else get_locale_text("i18n_town.shop_hidden_name"), "price": None, "is_unlocked": killed_yog, "buyable": False})
    return items


def _shop_label(item: Dict[str, Any]) -> Callable:
    def label(stats: UserStats, npc_data: Dict[str, Any], zh_cn: Dict[str, Any], number: int) -> str:
        name = item["name"]
        if item["buyable"]:
            if item["is_unlocked"]:
                return get_locale_text("i18n_town.shop_buy_unlocked", number=number, name=name, status=get_locale_text("global.unlocked_status"))
            return get_locale_text("i18n_town.shop_buy_price", number=number, name=name, price=item["price"])
        status_str = get_locale_text("global.unlocked_status") if item["is_unlocked"] else get_locale_text("i18n_town.shop_locked")
        return get_locale_text("i18n_town.shop_status", number=number, name=name, status=status_str)
    return label


def _shop_specs(stats: UserStats) -> List[Dict[str, Any]]:
    specs = []
    for item in _shop_items(stats):
        specs.append(_option("shop_buy", _shop_label(item), target=item, prefix=False))
    specs.append(_option("back_shop", _global_label("back_to_previous", get_locale_text("global.back_to_previous"))))
    return specs


def build_dialog_menu(town_engine, stats: UserStats, npc_id: str, zh_cn: Dict[str, Any]) -> Dict[str, Any]:
    entities = zh_cn.get("interactive_entities", {})
    npc_data = entities.get(npc_id, {})
    npc_name = npc_data.get("name", npc_id)
    player_name = getattr(stats, "player_name", get_locale_text("i18n_town.player_default_name"))
    welcome = npc_data.get("welcome", "").replace("{player_name}", player_name)
    fallback_action = None

    riddle_step = stats.town_flags.get("jack_riddle_step")
    agreement_menu = stats.town_flags.get("jack_agreement_menu")
    market_sub = stats.town_flags.get("market_sub_menu")
    shop_sub = stats.town_flags.get("shop_sub_menu")

    if npc_id == "Bartender_Jack" and riddle_step:
        welcome = get_locale_text("global.jack_riddle_intro")
        if riddle_step == 1:
            welcome += "\n\n" + get_locale_text("global.jack_riddle_1")
        elif riddle_step == 2:
            welcome += "\n\n" + get_locale_text("global.jack_riddle_2")
        specs = _riddle_specs(riddle_step)
    elif npc_id == "Bartender_Jack" and agreement_menu:
        welcome = npc_data.get("welcome", "")
        specs = _agreement_specs(stats)
    elif npc_id == "Market_Merchant" and market_sub == "buy":
        specs = _market_buy_specs(town_engine, stats)
    elif npc_id == "Market_Merchant" and market_sub == "lock":
        specs = [
            _option(None, _global_label("lock_instructions", get_locale_text("global.lock_instructions")), selectable=False),
            _option("back_market_lock", _global_label("back_to_previous_1", get_locale_text("global.back_to_previous_1")), prefix=False),
        ]
        fallback_action = "lock_card_name"
    elif npc_id == "Shopkeeper_Jack" and shop_sub == "buy_subclass":
        specs = _shop_specs(stats)
    else:
        if npc_id == "Crypto_Whale" and stats.town_flags.get("reported_whale"):
            welcome = get_locale_text("global.whale_reported_refuse")
        specs = _normal_specs(npc_id)

    return {
        "npc_name": npc_name,
        "welcome": welcome,
        "options": _materialize_options(specs, stats, npc_data, zh_cn),
        "fallback_action": fallback_action,
    }


def process_dialog_choice(town_engine, stats: UserStats, npc_id: str, choice_lower: str, choice: str, user_id: str, zh_cn: Dict[str, Any]) -> str:
    menu = build_dialog_menu(town_engine, stats, npc_id, zh_cn)
    for option in menu["options"]:
        if option["number"] is not None and choice_lower == str(option["number"]):
            return process_dialog_action(town_engine, stats, npc_id, option["action"], choice_lower, user_id, zh_cn, option["target"])
    fallback_action = menu.get("fallback_action")
    if fallback_action:
        return process_dialog_action(town_engine, stats, npc_id, fallback_action, choice_lower, user_id, zh_cn, choice)
    return get_locale_text("global.invalid_option")


def process_dialog_action(town_engine, stats: UserStats, npc_id: str, action: str, choice_lower: str, user_id: str, zh_cn: Dict[str, Any], target: Any = None) -> str:
    entities = zh_cn.get("interactive_entities", {})
    npc_data = entities.get(npc_id, {})

    def rerender() -> str:
        return town_engine._render_dialog_window(stats, npc_id, zh_cn)

    def save() -> None:
        town_engine.save_manager.save_stats(user_id, stats)

    if action == "leave":
        stats.town_flags.pop("current_dialog", None)
        stats.town_flags.pop("market_sub_menu", None)
        stats.town_flags.pop("shop_sub_menu", None)
        stats.town_flags.pop("jack_agreement_menu", None)
        stats.town_flags.pop("jack_riddle_step", None)
        save()
        return get_locale_text("global.dialog_exit", name=npc_data.get("name", npc_id)) + "\n\n" + town_engine.render_current_room(user_id, stats)

    if action == "back_riddle":
        stats.town_flags.pop("jack_riddle_step", None)
        save()
        return rerender()

    if action == "back_agreement":
        stats.town_flags.pop("jack_agreement_menu", None)
        save()
        return rerender()

    if action == "back_market_buy" or action == "back_market_lock":
        stats.town_flags.pop("market_sub_menu", None)
        save()
        return rerender()

    if action == "back_shop":
        stats.town_flags.pop("shop_sub_menu", None)
        save()
        return rerender()

    if action == "riddle_answer":
        step = stats.town_flags.get("jack_riddle_step")
        if step == 1:
            if target == 2:
                stats.town_flags["jack_riddle_step"] = 2
                save()
                return rerender()
            if target in (1, 3, 4):
                stats.town_flags.pop("jack_riddle_step", None)
                save()
                return get_locale_text("global.jack_riddle_wrong") + "\n\n" + rerender()
        elif step == 2:
            if target == 2:
                stats.town_flags.pop("jack_riddle_step", None)
                stats.town_inventory.append("promotional_agreement")
                save()
                return get_locale_text("global.jack_riddle_success") + "\n\n" + rerender()
            if target in (1, 3, 4):
                stats.town_flags.pop("jack_riddle_step", None)
                save()
                return get_locale_text("global.jack_riddle_wrong") + "\n\n" + rerender()
        return get_locale_text("global.invalid_option")

    if action == "agreement_notebook":
        stats.town_flags.pop("jack_agreement_menu", None)
        stats.town_inventory.remove("lost_notebook")
        stats.town_inventory.append("promotional_agreement")
        save()
        return get_locale_text("global.jack_notebook_success") + "\n\n" + rerender()

    if action == "agreement_riddle":
        stats.town_flags.pop("jack_agreement_menu", None)
        stats.town_flags["jack_riddle_step"] = 1
        save()
        return rerender()

    if action == "market_buy":
        shelf = town_engine._get_market_shelf(stats)
        if not isinstance(target, int) or not 0 <= target < len(shelf):
            return get_locale_text("global.invalid_option")
        cid = shelf[target]
        if not cid:
            return get_locale_text("global.card_buy_not_on_shelf", name="")
        card_obj = ALL_CARDS.get(cid)
        price = get_market_price(cid, card_obj)
        if stats.gp < price:
            return get_locale_text("global.gp_insufficient", req=price, owned=stats.gp)
        c_name = ALL_CARDS[cid].name if cid in ALL_CARDS else cid
        stats.gp -= price
        stats.purchased_pool.append(cid)
        if not hasattr(stats, "unlocked_new_cards"):
            stats.unlocked_new_cards = []
        if cid not in stats.unlocked_new_cards:
            stats.unlocked_new_cards.append(cid)
        shelf[target] = ""
        stats.town_flags["market_shelf"] = shelf
        save()
        res_msg = get_locale_text("global.card_buy_success", price=price, name=c_name)
        return res_msg + "\n\n" + rerender()

    if action == "lock_card_name":
        choice = target
        target_cid = None
        from ...entities.cards.base import _get_card_config
        card_config = _get_card_config()
        for cid, cfg in card_config.items():
            if cfg.get("name") == choice:
                target_cid = cid
                break
        if not target_cid:
            return get_locale_text("global.card_lock_failed_not_found", name=choice)
        c_obj = ALL_CARDS[target_cid]
        if getattr(c_obj, "rarity", "common") in ("legendary", "mythic", "artifact", "curse"):
            return get_locale_text("global.card_lock_failed_legendary")
        if target_cid in getattr(stats, "locked_cards", []):
            return get_locale_text("i18n_town.card_lock_already", choice=choice)
        if len(getattr(stats, "locked_cards", [])) >= LOCK_SLOT_LIMIT:
            return get_locale_text("i18n_town.card_lock_limit", limit=LOCK_SLOT_LIMIT)
        if stats.gp < LOCK_PRICE_GP:
            return get_locale_text("global.gp_insufficient", req=LOCK_PRICE_GP, owned=stats.gp)
        stats.gp -= LOCK_PRICE_GP
        if not hasattr(stats, "locked_cards") or stats.locked_cards is None:
            stats.locked_cards = []
        stats.locked_cards.append(target_cid)
        stats.town_flags.pop("market_sub_menu", None)
        save()
        res_msg = get_locale_text("global.card_lock_success", name=choice, price=LOCK_PRICE_GP)
        return res_msg + "\n\n" + rerender()

    if action == "shop_buy":
        if not isinstance(target, dict):
            return get_locale_text("global.invalid_option")
        name = target["name"]
        price = target["price"]
        is_unlocked = target["is_unlocked"]
        buyable = target["buyable"]
        if not buyable:
            return get_locale_text("i18n_town.shop_not_buyable", name=name)
        if name == "门之钥匙":
            if getattr(stats, "unlocked_gatekey", False):
                return get_locale_text("global.already_unlocked_error", name=name)
        else:
            if name in getattr(stats, "unlocked_subclasses", []):
                return get_locale_text("global.already_unlocked_error", name=name)
        if stats.gp < price:
            return get_locale_text("global.gp_insufficient", req=price, owned=stats.gp)
        stats.gp -= price
        if name == "门之钥匙":
            stats.unlocked_gatekey = True
        else:
            stats.unlocked_subclasses.append(name)
        save()
        success_msg = get_locale_text("global.shop_buy_success", name=name, price=price)
        return success_msg + "\n\n" + rerender()

    if action == "idle":
        quotes = npc_data.get("idle_talk", [])
        q = random.choice(quotes) if quotes else "..."
        return q + "\n\n" + rerender()

    if action == "quest_accept":
        stats.town_flags["quest_town_tour_state"] = "started"
        stats.town_flags["quest_town_tour_visited"] = ["square"]
        save()
        return npc_data.get("quest_accepted", "") + "\n\n" + rerender()

    if action == "quest_status":
        visited = stats.town_flags.get("quest_town_tour_visited", [])
        return npc_data.get("quest_doing", "").format(progress=len(visited)) + "\n\n" + rerender()

    if action == "quest_complete":
        stats.town_flags["quest_town_tour_state"] = "completed"
        stats.gp += 2000
        save()
        return npc_data.get("quest_completed_msg", "") + "\n\n" + rerender()

    if action == "gift_glass":
        stats.town_inventory.remove("wine_glass")
        stats.town_flags["jack_gift_given"] = 1
        stats.gp += 150
        save()
        return npc_data.get("gift_success", "") + "\n\n" + rerender()

    if action == "gift_ore":
        stats.town_inventory.remove("strange_ore")
        stats.town_flags["ironclad_gift_given"] = 1
        stats.gp += 200
        save()
        return npc_data.get("gift_success", "") + "\n\n" + rerender()

    if action == "buy_shelf":
        stats.town_flags["market_sub_menu"] = "buy"
        save()
        return rerender()

    if action == "lock_card":
        stats.town_flags["market_sub_menu"] = "lock"
        save()
        return rerender()

    if action == "buy_subclass":
        stats.town_flags["shop_sub_menu"] = "buy_subclass"
        save()
        return rerender()

    if action == "open_box":
        stats.town_inventory.remove("rusty_key")
        stats.town_flags["box_opened"] = 1
        stats.gp += 300
        if not hasattr(stats, "locked_cards") or stats.locked_cards is None:
            stats.locked_cards = []
        if "discover" not in stats.locked_cards and len(stats.locked_cards) < LOCK_SLOT_LIMIT:
            stats.locked_cards.append("discover")
        save()
        return npc_data.get("open_success", "") + "\n\n" + rerender()

    if action == "wish":
        stats.town_inventory.remove("lucky_coin")
        effects = ["gp", "card", "hp"]
        c_effect = random.choice(effects)
        if c_effect == "gp":
            stats.gp += 200
            res = npc_data.get("wish_success_gp", "")
        elif c_effect == "card":
            if not hasattr(stats, "locked_cards") or stats.locked_cards is None:
                stats.locked_cards = []
            if "discover" not in stats.locked_cards and len(stats.locked_cards) < LOCK_SLOT_LIMIT:
                stats.locked_cards.append("discover")
            res = npc_data.get("wish_success_card", "")
        else:
            stats.town_health_bonus += 5
            res = npc_data.get("wish_success_hp", "")
        save()
        return res + "\n\n" + rerender()

    if action == "knock":
        count = stats.town_flags.get("knock_count", 0) + 1
        stats.town_flags["knock_count"] = count
        save()
        if count == 3:
            if not stats.town_flags.get("west_gate_bonus_claimed", 0):
                stats.town_flags["west_gate_bonus_claimed"] = 1
                stats.gp += 100
                save()
            return npc_data.get("knock_bonus_3", "") + "\n\n" + rerender()
        if count == 10:
            stats.town_flags.pop("current_dialog", None)
            save()
            return town_engine.challenge_npc(user_id, "Gate_Guardian")
        return npc_data.get("knock_normal", "").format(count=count) + "\n\n" + rerender()

    if action == "challenge":
        stats.town_flags.pop("current_dialog", None)
        save()
        return town_engine.challenge_npc(user_id, npc_id)

    if action == "buy_beer":
        if stats.gp < 50:
            return get_locale_text("global.beer_buy_insufficient")
        stats.gp -= 50
        stats.town_inventory.append("beer")
        save()
        return get_locale_text("global.beer_buy_success") + "\n\n" + rerender()

    if action == "brew_quest_accept":
        stats.town_flags["quest_brew_state"] = "started"
        save()
        return get_locale_text("global.quest_brew_started") + "\n\n" + rerender()

    if action == "give_wishing_dew":
        stats.town_flags["quest_brew_state"] = "completed"
        stats.town_inventory.remove("wishing_dew")
        stats.gp += 1500
        stats.town_health_bonus = getattr(stats, "town_health_bonus", 0) + 5
        save()
        return get_locale_text("global.quest_brew_real_success") + "\n\n" + rerender()

    if action == "dialog_sign_agreement":
        stats.town_flags["jack_agreement_menu"] = True
        save()
        return rerender()

    if action == "quest_hammer_accept":
        stats.town_flags["quest_hammer_state"] = "started"
        save()
        return get_locale_text("global.quest_hammer_started") + "\n\n" + rerender()

    if action == "quest_hammer_clue":
        return get_locale_text("global.quest_hammer_clue_msg") + "\n\n" + rerender()

    if action == "quest_hammer_return_real":
        stats.town_flags["quest_hammer_state"] = "completed"
        stats.town_inventory.remove("smith_hammer")
        stats.gp += 1500
        stats.town_health_bonus = getattr(stats, "town_health_bonus", 0) + 5
        save()
        return get_locale_text("global.quest_hammer_real_success") + "\n\n" + rerender()

    if action == "quest_hammer_return_fake":
        stats.town_flags["quest_hammer_state"] = "completed"
        stats.town_inventory.remove("fake_hammer")
        stats.gp += 200
        save()
        return get_locale_text("global.quest_hammer_fake_success") + "\n\n" + rerender()

    if action == "quest_hammer_return_force":
        stats.town_flags["quest_hammer_state"] = "completed"
        stats.gp += 1200
        save()
        return get_locale_text("global.quest_hammer_force_success") + "\n\n" + rerender()

    if action == "ask_hammer":
        return get_locale_text("global.lost_bard_tell_clue") + "\n\n" + rerender()

    if action == "give_beer":
        stats.town_inventory.remove("beer")
        stats.town_inventory.append("smith_hammer")
        save()
        return get_locale_text("global.lost_bard_give_beer_success") + "\n\n" + rerender()

    if action == "buy_fake_hammer":
        if stats.gp < 500:
            return get_locale_text("global.gp_insufficient", req=500, owned=stats.gp)
        stats.gp -= 500
        stats.town_inventory.append("fake_hammer")
        save()
        return get_locale_text("global.buy_fake_hammer_success") + "\n\n" + rerender()

    if action == "buy_void_herb":
        if stats.gp < 800:
            return get_locale_text("global.gp_insufficient", req=800, owned=stats.gp)
        stats.gp -= 800
        stats.town_inventory.append("void_herb")
        save()
        return get_locale_text("global.buy_void_herb_success") + "\n\n" + rerender()

    if action == "trade_void_herb":
        stats.town_inventory.remove("promotional_agreement")
        stats.town_inventory.append("void_herb")
        save()
        return get_locale_text("global.trade_void_herb_success") + "\n\n" + rerender()

    if action == "report_whale":
        stats.town_flags["reported_whale"] = True
        stats.town_inventory.append("void_herb")
        save()
        return get_locale_text("global.report_whale_success") + "\n\n" + rerender()

    if action == "wash_herb":
        stats.town_inventory.remove("void_herb")
        stats.town_inventory.append("wishing_dew")
        save()
        return get_locale_text("global.wash_herb_success") + "\n\n" + rerender()

    if action == "sell_wishing_dew":
        stats.town_flags["quest_brew_state"] = "completed"
        stats.town_inventory.remove("wishing_dew")
        stats.gp += 2000
        save()
        return get_locale_text("global.sell_dew_success") + "\n\n" + rerender()

    return get_locale_text("global.invalid_option")
