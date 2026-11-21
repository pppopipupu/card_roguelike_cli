import random
from typing import Optional
from ...data.balance_config import COOP_MAX_PLAYERS
from ...data.locale_data import get_locale_raw
from ...data.ultimate_prism_data import (
    PRISM_TALK_PREFIXES,
    ULTIMATE_PRISM_ACHIEVEMENT_ID,
    ULTIMATE_PRISM_CARD_ID,
    ULTIMATE_PRISM_MERC_ID,
)
from ...entities import ALL_CARDS
from ...entities.cards.base import get_card_lore
from ...models.state import Card, GameRun, UserStats, ensure_card_state
from ..cli.base.pinyin_match import find_entry_by_query
from ..party.mercenary import build_mercenary_player, is_mercenary
from ..text.events import locale_text
from ..text.pipeline import render_text_node
from .market_service import is_ultimate_prism_departed

CARD_TALK_TOWN_FLAG = "card_talk_dialog"
CARD_TALK_RUN_KEY = "card_talk_dialogs"


def _t(key: str, **params) -> str:
    return render_text_node(locale_text(key, params=params))


def can_talk_to_card(card: Optional[Card]) -> bool:
    if card is None:
        return False
    if getattr(card, "rarity", "") == "artifact":
        return True
    if hasattr(card, "has_tag") and (card.has_tag("sentient") or card.has_tag("talkable")):
        return True
    return False


def has_prism_mercenary_unlocked(stats: Optional[UserStats]) -> bool:
    if stats is None:
        return False
    if ULTIMATE_PRISM_ACHIEVEMENT_ID in (getattr(stats, "unlocked_achievements", None) or []):
        return True
    ach_stats = getattr(stats, "achievement_stats", None) or {}
    return int(ach_stats.get("ultimate_prism_played", 0) or 0) >= 1


def strip_card_talk_prefix(raw_query: str) -> tuple[str, bool]:
    text = (raw_query or "").strip()
    if not text:
        return "", False
    parts = text.split(None, 1)
    head = parts[0].lower()
    if head in PRISM_TALK_PREFIXES:
        return (parts[1].strip() if len(parts) > 1 else ""), True
    return text, False


def _collect_owned_card_ids(run: Optional[GameRun], stats: Optional[UserStats]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    if run is not None and run.player is not None:
        p = run.player
        for pile in (p.hand, p.deck, p.draw_pile, p.discard_pile, p.exhaust_pile):
            for c in pile:
                cid = ensure_card_state(c).id
                if cid and cid not in seen:
                    seen.add(cid)
                    ordered.append(cid)
    if stats is not None:
        for cid in list(getattr(stats, "locked_cards", None) or []) + list(getattr(stats, "unlocked_new_cards", None) or []):
            base = ensure_card_state(cid).id
            if base and base not in seen:
                seen.add(base)
                ordered.append(base)
        for c in getattr(stats, "open_world_deck", None) or []:
            cid = ensure_card_state(c).id
            if cid and cid not in seen:
                seen.add(cid)
                ordered.append(cid)
    return ordered


def _resolve_card_from_ids(query: str, cids: list[str], allow_fuzzy: bool = True) -> Optional[Card]:
    q = (query or "").strip()
    if not q or not cids:
        return None
    ql = q.lower()
    entries: list[tuple[str, str]] = []
    for cid in cids:
        card = ALL_CARDS.get(cid)
        if card is None:
            continue
        if ql == cid.lower() or ql == card.name.lower():
            return card
        entries.append((cid, card.name))
        entries.append((cid, cid))
    if allow_fuzzy:
        matched_cid = find_entry_by_query(entries, q)
        if matched_cid:
            return ALL_CARDS.get(matched_cid)
    return None


def resolve_talkable_card_query(
    query: str,
    run: Optional[GameRun],
    stats: Optional[UserStats],
    explicit: bool = False,
) -> Optional[Card]:
    q = (query or "").strip()
    if not q:
        return None
    if q.isdigit() and run is not None and run.player is not None:
        idx = int(q)
        if run.node_type == "battle" and 1 <= idx <= len(run.player.hand):
            return ALL_CARDS.get(ensure_card_state(run.player.hand[idx - 1]))
        if explicit and 1 <= idx <= len(run.player.deck):
            return ALL_CARDS.get(ensure_card_state(run.player.deck[idx - 1]))
        if not explicit:
            return None
    owned = _collect_owned_card_ids(run, stats)
    found = _resolve_card_from_ids(q, owned, allow_fuzzy=True)
    if found is not None:
        return found
    all_base_ids = [cid for cid in ALL_CARDS.keys() if not cid.endswith("+")]
    return _resolve_card_from_ids(q, all_base_ids, allow_fuzzy=explicit)


def _get_dialog_entry(run: Optional[GameRun], stats: Optional[UserStats], user_id: str) -> Optional[dict]:
    if run is not None:
        dialogs = run.node_data.get(CARD_TALK_RUN_KEY)
        if isinstance(dialogs, dict):
            entry = dialogs.get(user_id)
            if isinstance(entry, dict):
                return entry
    if stats is not None:
        entry = (stats.town_flags or {}).get(CARD_TALK_TOWN_FLAG)
        if isinstance(entry, dict):
            return entry
    return None


def _set_dialog_entry(save_manager, run: Optional[GameRun], stats: Optional[UserStats], user_id: str, entry: Optional[dict]) -> None:
    if run is not None:
        dialogs = run.node_data.setdefault(CARD_TALK_RUN_KEY, {})
        if entry is None:
            dialogs.pop(user_id, None)
            if not dialogs:
                run.node_data.pop(CARD_TALK_RUN_KEY, None)
        else:
            dialogs[user_id] = entry
        save_manager.save_save(user_id, run)
        return
    if stats is not None:
        if entry is None:
            stats.town_flags.pop(CARD_TALK_TOWN_FLAG, None)
        else:
            stats.town_flags[CARD_TALK_TOWN_FLAG] = entry
        save_manager.save_stats(user_id, stats)


def is_in_card_talk_dialog(run: Optional[GameRun], stats: Optional[UserStats], user_id: str) -> bool:
    return _get_dialog_entry(run, stats, user_id) is not None


def close_card_talk_dialog(save_manager, run: Optional[GameRun], stats: Optional[UserStats], user_id: str) -> str:
    entry = _get_dialog_entry(run, stats, user_id)
    card_name = str(entry.get("card_name", "")) if isinstance(entry, dict) else ""
    _set_dialog_entry(save_manager, run, stats, user_id, None)
    return _t("i18n_prism.card_talk.exit_msg", name=card_name or ULTIMATE_PRISM_CARD_ID)


def render_card_talk_dialog(run: Optional[GameRun], stats: Optional[UserStats], user_id: str) -> str:
    entry = _get_dialog_entry(run, stats, user_id)
    if not isinstance(entry, dict):
        return ""
    card_id = str(entry.get("card_id", ""))
    card = ALL_CARDS.get(card_id)
    name = card.name if card is not None else str(entry.get("card_name", card_id))
    lines = []
    if entry.get("last_msg"):
        lines.append(str(entry["last_msg"]))
        lines.append("")
    lines.append(_t("i18n_prism.card_talk.dialog_header", name=name))
    if card_id == ULTIMATE_PRISM_CARD_ID:
        lines.append(_t("i18n_prism.card_talk.prism_greeting"))
    else:
        lines.append(_t("i18n_prism.card_talk.generic_greeting", name=name))
    lines.append("")
    lines.append(_t("i18n_prism.card_talk.opt_chat", name=name))
    lines.append(_t("i18n_prism.card_talk.opt_lore"))
    if card_id == ULTIMATE_PRISM_CARD_ID and has_prism_mercenary_unlocked(stats):
        lines.append(_t("i18n_prism.card_talk.opt_recruit_merc"))
    lines.append(_t("i18n_prism.card_talk.opt_leave"))
    lines.append(_t("i18n_prism.card_talk.prompt"))
    return "\n".join(lines)


def _recruit_prism_mercenary(save_manager, engine, run: Optional[GameRun], stats: UserStats, user_id: str) -> str:
    if not has_prism_mercenary_unlocked(stats):
        return _t("i18n_prism.card_talk.recruit_not_unlocked")
    if is_ultimate_prism_departed(stats):
        return _t("i18n_prism.card_talk.recruit_departed")
    if run is not None:
        for uid in run.party_order:
            p = run.players.get(uid)
            if is_mercenary(p) and getattr(p, "mercenary_id", "") == ULTIMATE_PRISM_MERC_ID and getattr(p, "mercenary_owner", "") == user_id:
                return _t("i18n_prism.card_talk.recruit_already_in_party")
        if len(run.party_order) >= COOP_MAX_PLAYERS:
            return _t("i18n_prism.card_talk.recruit_party_full")
        merc_uid = f"merc:{ULTIMATE_PRISM_MERC_ID}:{user_id}"
        suffix = 1
        while merc_uid in run.players:
            suffix += 1
            merc_uid = f"merc:{ULTIMATE_PRISM_MERC_ID}:{user_id}:{suffix}"
        merc = build_mercenary_player(ULTIMATE_PRISM_MERC_ID, user_id)
        run.players[merc_uid] = merc
        run.party_order.append(merc_uid)
        full_order = getattr(run, "_full_party_order", None)
        if isinstance(full_order, list) and merc_uid not in full_order:
            full_order.append(merc_uid)
        fm = getattr(run, "floor_map", None)
        if fm is not None and isinstance(getattr(fm, "player_session_map", None), dict):
            sid = fm.player_session_map.get(user_id)
            if sid and sid in fm.active_sessions:
                fm.player_session_map[merc_uid] = sid
                sess = fm.active_sessions[sid]
                if merc_uid not in sess.participants:
                    sess.participants.append(merc_uid)
                if merc_uid not in sess.roster:
                    sess.roster.append(merc_uid)
        slot = run.party_order.index(merc_uid) + 1
        if run.node_type == "battle":
            battle_engine = getattr(engine, "battle_engine", engine)
            if hasattr(battle_engine, "join_battle"):
                battle_engine.join_battle(run, merc_uid)
        save_manager.save_save(user_id, run)
        return _t("i18n_prism.card_talk.recruit_success_run", slot=slot)
    hired = list(getattr(stats, "hired_mercenaries", None) or [])
    if ULTIMATE_PRISM_MERC_ID in hired:
        return _t("i18n_prism.card_talk.recruit_already_hired")
    hired.append(ULTIMATE_PRISM_MERC_ID)
    stats.hired_mercenaries = hired
    save_manager.save_stats(user_id, stats)
    return _t("i18n_prism.card_talk.recruit_success_town")


def try_card_talk(
    save_manager,
    engine,
    user_id: str,
    raw_query: str,
    run: Optional[GameRun] = None,
    stats: Optional[UserStats] = None,
    explicit: bool = False,
) -> Optional[str]:
    query, has_prefix = strip_card_talk_prefix(raw_query)
    is_explicit = explicit or has_prefix
    if not query:
        return _t("i18n_prism.card_talk.missing_arg") if is_explicit else None
    if stats is None:
        stats = save_manager.load_stats(user_id)
    card = resolve_talkable_card_query(query, run, stats, explicit=is_explicit)
    if card is None:
        return _t("i18n_prism.card_talk.card_not_found", target=query) if is_explicit else None
    if not can_talk_to_card(card):
        return _t("i18n_prism.card_talk.no_response", name=card.name)
    entry = {
        "card_id": card.id,
        "card_name": card.name,
        "last_msg": "",
    }
    _set_dialog_entry(save_manager, run, stats, user_id, entry)
    return render_card_talk_dialog(run, stats, user_id)


def handle_card_talk_input(
    save_manager,
    engine,
    run: Optional[GameRun],
    stats: Optional[UserStats],
    user_id: str,
    raw_text: str,
) -> str:
    if stats is None:
        stats = save_manager.load_stats(user_id)
    assert stats is not None
    entry = _get_dialog_entry(run, stats, user_id)
    if not isinstance(entry, dict):
        return ""
    text = str(raw_text or "").strip().lower()
    if text in ("0", "离开", "leave", "exit", "quit", "取消", "cancel"):
        return close_card_talk_dialog(save_manager, run, stats, user_id)
    try:
        idx = int(text)
    except ValueError:
        return _t("i18n_prism.card_talk.invalid_choice")
    card_id = str(entry.get("card_id", ""))
    card = ALL_CARDS.get(card_id)
    name = card.name if card is not None else str(entry.get("card_name", card_id))
    if idx == 1:
        if card_id == ULTIMATE_PRISM_CARD_ID:
            chats = get_locale_raw("i18n_prism.card_talk.prism_chats", [])
            msg = random.choice(chats) if isinstance(chats, list) and chats else _t("i18n_prism.card_talk.prism_greeting")
        else:
            chats = get_locale_raw("i18n_prism.card_talk.generic_chats", [])
            raw_line = random.choice(chats) if isinstance(chats, list) and chats else ""
            msg = raw_line.format(name=name) if raw_line else _t("i18n_prism.card_talk.generic_greeting", name=name)
        entry["last_msg"] = msg
        _set_dialog_entry(save_manager, run, stats, user_id, entry)
        return render_card_talk_dialog(run, stats, user_id)
    if idx == 2:
        lore = get_card_lore(card if card is not None else card_id)
        if lore:
            entry["last_msg"] = _t("i18n_prism.card_talk.lore_reply", name=name, lore=lore)
        else:
            entry["last_msg"] = _t("i18n_prism.card_talk.lore_empty", name=name)
        _set_dialog_entry(save_manager, run, stats, user_id, entry)
        return render_card_talk_dialog(run, stats, user_id)
    if idx == 3 and card_id == ULTIMATE_PRISM_CARD_ID:
        entry["last_msg"] = _recruit_prism_mercenary(save_manager, engine, run, stats, user_id)
        _set_dialog_entry(save_manager, run, stats, user_id, entry)
        return render_card_talk_dialog(run, stats, user_id)
    return _t("i18n_prism.card_talk.invalid_choice")
