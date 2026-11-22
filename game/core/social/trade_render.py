from ...data.progression.trade_config import TRADE_KIND_CARD, TRADE_KIND_RELIC
from ...entities import ALL_CARDS, get_relic_name
from ..inventory.bag_service import get_item_display_name
from ..text.events import JoinedText, LocaleText
from .trade_items import Pair, entry_name


def t(key: str, **params) -> LocaleText:
    return LocaleText(key=key, params=params)


def join(parts: list, separator: str = "\n") -> JoinedText:
    return JoinedText(parts=[part for part in parts if part is not None], separator=separator)


def entry_label(entry: dict) -> LocaleText:
    kind = entry.get("kind")
    if kind == TRADE_KIND_CARD:
        return t("i18n_trade.entry_card", name=entry_name(entry))
    if kind == TRADE_KIND_RELIC:
        return t("i18n_trade.entry_relic", name=entry_name(entry))
    return t("i18n_trade.entry_item", name=entry_name(entry))


def entries_text(entries: list) -> JoinedText:
    return join([entry_label(entry) for entry in entries], "、")


def asset_names(pair: Pair, uid: str) -> tuple[list, list, list]:
    cards = []
    for state in pair.deck(uid):
        card = ALL_CARDS.get(state)
        cards.append(card.name if card else state.id)
    relics = [get_relic_name(relic_id) for relic_id in pair.relics(uid)]
    items = [get_item_display_name(item_id) for item_id in pair.bag(uid)]
    return cards, relics, items


def asset_line(kind: str, names: list) -> LocaleText:
    if not names:
        return t(f"i18n_trade.assets_{kind}_empty")
    counts = {}
    order = []
    for name in names:
        if name not in counts:
            counts[name] = 0
            order.append(name)
        counts[name] += 1
    parts = []
    for name in order:
        count = counts[name]
        if count > 1:
            parts.append(t("i18n_trade.asset_item_count", name=name, count=count))
        else:
            parts.append(t("i18n_trade.asset_item", name=name))
    return t(f"i18n_trade.assets_{kind}", count=len(names), items=join(parts, "、"))


def assets_node(pair: Pair, uid: str, target_uid: str, target_name: str) -> JoinedText:
    own_cards, own_relics, own_items = asset_names(pair, uid)
    other_cards, other_relics, other_items = asset_names(pair, target_uid)
    return join([
        t("i18n_trade.assets_title", name=target_name),
        t("i18n_trade.separator"),
        t("i18n_trade.assets_self_header"),
        asset_line("cards", own_cards),
        asset_line("relics", own_relics),
        asset_line("items", own_items),
        t("i18n_trade.separator"),
        t("i18n_trade.assets_other_header", name=target_name),
        asset_line("cards", other_cards),
        asset_line("relics", other_relics),
        asset_line("items", other_items),
        t("i18n_trade.separator"),
        t("i18n_trade.assets_hint", name=target_name),
        t("i18n_trade.separator"),
    ])


def offer_detail(offer: dict) -> LocaleText:
    give = list(offer.get("give") or [])
    want = list(offer.get("want") or [])
    if want:
        return t(
            "i18n_trade.list_detail_exchange",
            give=entries_text(give),
            want=entries_text(want),
        )
    return t("i18n_trade.list_detail_gift", items=entries_text(give))


def list_node(incoming: list, outgoing: list) -> JoinedText:
    parts = [t("i18n_trade.list_header", incoming=len(incoming), outgoing=len(outgoing))]
    for offer in incoming:
        parts.append(
            t(
                "i18n_trade.list_incoming",
                name=offer.get("from_name", ""),
                detail=offer_detail(offer),
                id=offer.get("id", ""),
            )
        )
    for offer in outgoing:
        parts.append(
            t(
                "i18n_trade.list_outgoing",
                name=offer.get("to_name", ""),
                detail=offer_detail(offer),
                id=offer.get("id", ""),
            )
        )
    parts.append(t("i18n_trade.list_hint"))
    return join(parts)


def popup_node(offer: dict, extra_count: int = 0) -> JoinedText:
    give = list(offer.get("give") or [])
    want = list(offer.get("want") or [])
    parts = [t("i18n_trade.popup_header", name=offer.get("from_name", ""))]
    if want:
        parts.append(t("i18n_trade.popup_exchange_give", items=entries_text(give)))
        parts.append(t("i18n_trade.popup_exchange_want", items=entries_text(want)))
    else:
        parts.append(t("i18n_trade.popup_gift", items=entries_text(give)))
    if extra_count > 0:
        parts.append(t("i18n_trade.popup_more", count=extra_count))
    parts.append(t("i18n_trade.popup_options"))
    return join(parts)
