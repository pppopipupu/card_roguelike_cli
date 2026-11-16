from ....data.locale_data import get_locale_text
from ....data.town_card_shop_data import TOWN_CARD_MERCHANT_NPC_ID, TOWN_CARD_SHOP_CATALOG
from ....entities import ALL_CARDS
from ....models.state import UserStats, ensure_card_state
from ...text.events import LocaleText
from ...text.pipeline import render_text_node
from ..open_world.loadout_service import OpenWorldLoadoutService


def _t(key: str, **params) -> str:
    return render_text_node(LocaleText(key=key, params=params))


def _cost_text(card) -> str:
    parts = []
    cost_a = getattr(card, "cost_a", 0)
    cost_ba = getattr(card, "cost_ba", 0)
    if cost_a:
        parts.append(f"{cost_a}A")
    if cost_ba:
        parts.append(f"{cost_ba}BA")
    return "/".join(parts) if parts else "0A"


def _color_text(color: str) -> str:
    if color == "wizard":
        return _t("i18n_pvp.card_merchant.color_wizard")
    if color == "warrior":
        return _t("i18n_pvp.card_merchant.color_warrior")
    return _t("i18n_pvp.card_merchant.color_neutral")


def build_town_card_shop_menu(stats: UserStats, zh_cn: dict) -> dict:
    npc_name = zh_cn.get(TOWN_CARD_MERCHANT_NPC_ID, {}).get("name", TOWN_CARD_MERCHANT_NPC_ID)
    deck = OpenWorldLoadoutService.ensure_open_world_deck(stats)
    header_lines = [
        _t("i18n_pvp.card_merchant.title"),
        _t("i18n_pvp.card_merchant.summary", gp=stats.gp, deck_count=len(deck)),
        _t("i18n_pvp.card_merchant.tip"),
    ]
    options = []
    for idx, entry in enumerate(TOWN_CARD_SHOP_CATALOG, start=1):
        cid = entry["id"]
        price = int(entry["price"])
        card = ALL_CARDS.get(cid)
        if card is None:
            continue
        row = _t(
            "i18n_pvp.card_merchant.item_row",
            idx=idx,
            name=card.name,
            color=_color_text(getattr(card, "color", "neutral")),
            cost=_cost_text(card),
            price=price,
            desc=card.desc,
        )
        options.append({
            "number": idx,
            "action": "buy_open_world_card",
            "target": entry,
            "text": row,
        })
    options.append({
        "number": 0,
        "action": "leave",
        "target": None,
        "text": f"[0] {_t('i18n_pvp.card_merchant.opt_leave')}",
    })
    return {
        "npc_name": npc_name,
        "welcome": "\n".join(header_lines),
        "options": options,
        "fallback_action": None,
    }


def process_town_card_shop_choice(town_engine, stats: UserStats, choice_lower: str, user_id: str, zh_cn: dict) -> str:
    npc_name = zh_cn.get(TOWN_CARD_MERCHANT_NPC_ID, {}).get("name", TOWN_CARD_MERCHANT_NPC_ID)
    if choice_lower in ("0", "leave", "exit", "quit"):
        stats.town_flags.pop("current_dialog", None)
        town_engine.save_manager.save_stats(user_id, stats)
        return get_locale_text("global.dialog_exit", name=npc_name) + "\n\n" + town_engine.render_current_room(user_id, stats)

    if not choice_lower.isdigit():
        return _t("i18n_pvp.card_merchant.invalid_option")
    idx = int(choice_lower)
    if idx < 1 or idx > len(TOWN_CARD_SHOP_CATALOG):
        return _t("i18n_pvp.card_merchant.invalid_option")

    entry = TOWN_CARD_SHOP_CATALOG[idx - 1]
    cid = entry["id"]
    price = int(entry["price"])
    card = ALL_CARDS.get(cid)
    card_name = card.name if card else cid
    if stats.gp < price:
        return _t("i18n_pvp.card_merchant.insufficient_gp", name=card_name, price=price, gp=stats.gp)

    OpenWorldLoadoutService.ensure_open_world_deck(stats)
    stats.gp -= price
    stats.open_world_deck.append(ensure_card_state(cid))
    town_engine.save_manager.save_stats(user_id, stats)
    msg = _t(
        "i18n_pvp.card_merchant.buy_success",
        price=price,
        name=card_name,
        deck_count=len(stats.open_world_deck),
    )
    return msg + "\n\n" + town_engine._render_dialog_window(stats, TOWN_CARD_MERCHANT_NPC_ID, zh_cn)
