from ...data.starting_deck_config import LOCK_SLOT_LIMIT
from ...data.ultimate_prism_data import (
    CHIREIDEN_QUEST_COMPLETED_FLAG,
    ULTIMATE_PRISM_CARD_ID,
    ULTIMATE_PRISM_CONFIG,
    ULTIMATE_PRISM_FLAG_DEPARTED,
    ULTIMATE_PRISM_FLAG_IDLE_BATTLES,
    ULTIMATE_PRISM_FLAG_UNLOCKED,
)
from ...models.state import UserStats
from ..text.events import locale_text
from ..text.pipeline import render_text_node


def _t(key: str, **params) -> str:
    return render_text_node(locale_text(key, params=params))


def has_completed_chireiden_quest(stats: UserStats | None) -> bool:
    if stats is None:
        return False
    flags = getattr(stats, "town_flags", None) or {}
    if flags.get(CHIREIDEN_QUEST_COMPLETED_FLAG):
        return True
    ach_stats = getattr(stats, "achievement_stats", None) or {}
    if int(ach_stats.get("chireiden_portal_kills", 0) or 0) >= 1:
        return True
    unlocked = getattr(stats, "unlocked_achievements", None) or []
    return "chireiden_penning_sealer" in unlocked


def is_ultimate_prism_unlocked(stats: UserStats | None) -> bool:
    if stats is None:
        return False
    flags = getattr(stats, "town_flags", None) or {}
    return bool(flags.get(ULTIMATE_PRISM_FLAG_UNLOCKED))


def is_ultimate_prism_departed(stats: UserStats | None) -> bool:
    if stats is None:
        return False
    flags = getattr(stats, "town_flags", None) or {}
    return bool(flags.get(ULTIMATE_PRISM_FLAG_DEPARTED))


def can_buy_ultimate_prism(stats: UserStats | None) -> bool:
    if stats is None:
        return False
    return has_completed_chireiden_quest(stats) and not is_ultimate_prism_unlocked(stats)


def can_relock_ultimate_prism(stats: UserStats | None) -> bool:
    if stats is None:
        return False
    return is_ultimate_prism_unlocked(stats) and is_ultimate_prism_departed(stats)


def buy_ultimate_prism(stats: UserStats) -> tuple[bool, str]:
    price = int(ULTIMATE_PRISM_CONFIG["unlock_price_gp"])
    if not has_completed_chireiden_quest(stats):
        return False, _t("i18n_prism.market.need_chireiden")
    if is_ultimate_prism_unlocked(stats):
        if is_ultimate_prism_departed(stats):
            return relock_ultimate_prism(stats)
        if ULTIMATE_PRISM_CARD_ID in (stats.locked_cards or []):
            return False, _t("i18n_prism.market.already_locked")
    if stats.locked_cards is None:
        stats.locked_cards = []
    if ULTIMATE_PRISM_CARD_ID not in stats.locked_cards and len(stats.locked_cards) >= LOCK_SLOT_LIMIT:
        return False, _t("i18n_town.card_lock_limit", limit=LOCK_SLOT_LIMIT)
    if stats.gp < price:
        return False, _t("global.gp_insufficient", req=price, owned=stats.gp)
    stats.gp -= price
    stats.town_flags[ULTIMATE_PRISM_FLAG_UNLOCKED] = True
    stats.town_flags[ULTIMATE_PRISM_FLAG_DEPARTED] = False
    stats.town_flags[ULTIMATE_PRISM_FLAG_IDLE_BATTLES] = 0
    if not hasattr(stats, "unlocked_new_cards") or stats.unlocked_new_cards is None:
        stats.unlocked_new_cards = []
    if ULTIMATE_PRISM_CARD_ID not in stats.unlocked_new_cards:
        stats.unlocked_new_cards.append(ULTIMATE_PRISM_CARD_ID)
    if ULTIMATE_PRISM_CARD_ID not in stats.locked_cards:
        stats.locked_cards.append(ULTIMATE_PRISM_CARD_ID)
    return True, _t("i18n_prism.market.buy_success", price=price)


def relock_ultimate_prism(stats: UserStats) -> tuple[bool, str]:
    price = int(ULTIMATE_PRISM_CONFIG["relock_price_gp"])
    if not is_ultimate_prism_unlocked(stats):
        return False, _t("i18n_prism.market.lock_need_buy", price=int(ULTIMATE_PRISM_CONFIG["unlock_price_gp"]))
    if stats.locked_cards is None:
        stats.locked_cards = []
    if ULTIMATE_PRISM_CARD_ID not in stats.locked_cards and len(stats.locked_cards) >= LOCK_SLOT_LIMIT:
        return False, _t("i18n_town.card_lock_limit", limit=LOCK_SLOT_LIMIT)
    if stats.gp < price:
        return False, _t("global.gp_insufficient", req=price, owned=stats.gp)
    stats.gp -= price
    stats.town_flags[ULTIMATE_PRISM_FLAG_DEPARTED] = False
    stats.town_flags[ULTIMATE_PRISM_FLAG_IDLE_BATTLES] = 0
    if ULTIMATE_PRISM_CARD_ID not in stats.locked_cards:
        stats.locked_cards.append(ULTIMATE_PRISM_CARD_ID)
    return True, _t("i18n_prism.market.relock_success", price=price)
