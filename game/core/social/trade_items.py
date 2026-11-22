from dataclasses import asdict
from typing import Callable, Optional

from ...data.entities.relic_data import RELIC_CONFIG
from ...data.world.room_interact_data import BAG_DEFAULT_MAX_WEIGHT
from ...data.progression.trade_config import (
    TRADE_KINDS,
    TRADE_KIND_CARD,
    TRADE_KIND_ITEM,
    TRADE_KIND_PREFIXES,
    TRADE_KIND_RELIC,
    TRADE_MIN_DECK_CARDS,
    TRADE_SPEC_SEPARATORS,
)
from ...entities import ALL_CARDS, get_relic_name
from ...models.state import CardState, GameRun, PlayerState, UserStats, ensure_card_state
from ..inventory.bag_service import (
    calc_bag_items_weight,
    get_bag_max_weight,
    get_item_display_name,
    resolve_item_query,
)
from ..inventory.relic_service import (
    get_relic_counter,
    grant_relic,
    init_relic_counter_map,
    revoke_relic,
    set_relic_counter,
)
from ..world.open_world.loadout_service import OpenWorldLoadoutService

CARD_FULL_FIELDS = (
    "id",
    "upgraded",
    "gems",
    "enchantments",
    "return_left",
    "replay",
    "fragile",
    "no_copy",
    "power_penalty",
    "exhaust_used",
    "fleeting_used",
)
CARD_BASE_FIELDS = ("id", "upgraded", "gems", "enchantments")


class Spot:
    __slots__ = ("kind", "run", "stats")

    def __init__(self, kind: str, run: Optional[GameRun] = None, stats: Optional[UserStats] = None):
        self.kind = kind
        self.run = run
        self.stats = stats


class Pair:
    def __init__(self, save_manager, kind: str, run: Optional[GameRun] = None, stats: Optional[dict] = None):
        self.save_manager = save_manager
        self.kind = kind
        self.run = run
        self.stats = stats or {}

    def _player(self, uid: str) -> PlayerState:
        assert self.run is not None
        return self.run.players[uid]

    def deck(self, uid: str) -> list:
        if self.kind == "coop":
            return self._player(uid).deck
        stats = self.stats[uid]
        if not stats.open_world_deck:
            OpenWorldLoadoutService.ensure_open_world_deck(stats)
        return stats.open_world_deck

    def set_deck(self, uid: str, cards: list) -> None:
        if self.kind == "coop":
            self._player(uid).deck = cards
        else:
            self.stats[uid].open_world_deck = cards

    def relics(self, uid: str) -> list:
        if self.kind == "coop":
            return self._player(uid).relics
        return self.stats[uid].open_world_relics

    def relic_counter(self, uid: str, relic_id: str) -> int:
        if self.kind == "coop":
            return get_relic_counter(self._player(uid), relic_id)
        counters = self.stats[uid].open_world_relic_counters
        if relic_id in counters:
            return int(counters[relic_id])
        return int(RELIC_CONFIG.get(relic_id, {}).get("counter_init", 0))

    def add_relic(self, uid: str, relic_id: str, counter: int) -> None:
        if self.kind == "coop":
            player = self._player(uid)
            grant_relic(player, relic_id)
            set_relic_counter(player, relic_id, counter)
            return
        stats = self.stats[uid]
        if relic_id not in stats.open_world_relics:
            stats.open_world_relics.append(relic_id)
        counters = stats.open_world_relic_counters
        init_relic_counter_map(counters, relic_id)
        counters[relic_id] = int(counter)

    def remove_relic(self, uid: str, relic_id: str) -> None:
        if self.kind == "coop":
            revoke_relic(self._player(uid), relic_id)
            return
        stats = self.stats[uid]
        if relic_id in stats.open_world_relics:
            stats.open_world_relics.remove(relic_id)
        stats.open_world_relic_counters.pop(relic_id, None)

    def bag(self, uid: str) -> list:
        if self.kind == "coop":
            return self._player(uid).bag_items
        return self.stats[uid].open_world_bag

    def set_bag(self, uid: str, items: list) -> None:
        if self.kind == "coop":
            self._player(uid).bag_items = items
        else:
            self.stats[uid].open_world_bag = items

    def max_bag_weight(self, uid: str) -> float:
        if self.kind == "coop":
            return float(get_bag_max_weight(self._player(uid)))
        return float(BAG_DEFAULT_MAX_WEIGHT)

    def save(self, actor_uid: str) -> None:
        if self.kind == "coop":
            self.save_manager.save_save(actor_uid, self.run)
            return
        for uid, stats in self.stats.items():
            self.save_manager.save_stats(uid, stats)


def split_specs(text: str) -> list[str]:
    pieces = [str(text or "")]
    for separator in TRADE_SPEC_SEPARATORS:
        expanded = []
        for piece in pieces:
            expanded.extend(piece.split(separator))
        pieces = expanded
    return [piece.strip() for piece in pieces if piece.strip()]


def parse_spec(spec: str) -> tuple[str, str]:
    text = spec.strip()
    lowered = text.lower()
    for prefix, kind in TRADE_KIND_PREFIXES.items():
        for mark in (":", "：", " "):
            if lowered.startswith(prefix + mark):
                return kind, text[len(prefix) + 1:].strip()
    return "", text


def card_name(snapshot: dict) -> str:
    state = ensure_card_state(snapshot)
    card = ALL_CARDS.get(state)
    return card.name if card else state.id


def entry_name(entry: dict) -> str:
    kind = entry.get("kind")
    if kind == TRADE_KIND_CARD:
        return card_name(entry.get("card") or {})
    if kind == TRADE_KIND_RELIC:
        return get_relic_name(str(entry.get("relic_id", "")))
    return get_item_display_name(str(entry.get("item_id", "")))


def card_matches(state: CardState, snapshot: dict, fields: tuple) -> bool:
    for name in fields:
        if getattr(state, name, None) != snapshot.get(name):
            return False
    return True


def match_card_index(deck: list, snapshot: dict) -> Optional[int]:
    exact = [idx for idx, state in enumerate(deck) if card_matches(state, snapshot, CARD_FULL_FIELDS)]
    if exact:
        return exact[0]
    base = [idx for idx, state in enumerate(deck) if card_matches(state, snapshot, CARD_BASE_FIELDS)]
    if len(base) == 1:
        return base[0]
    return None


def find_card_entry(deck: list, query: str) -> Optional[dict]:
    from ..cli.base.pinyin_match import find_entry_by_query

    entries = []
    for idx, state in enumerate(deck):
        card = ALL_CARDS.get(state)
        if card is None:
            continue
        entries.append((str(idx), card.name))
        entries.append((str(idx), state.id))
    matched = find_entry_by_query(entries, query)
    if matched is None:
        return None
    return {"kind": TRADE_KIND_CARD, "card": asdict(ensure_card_state(deck[int(matched)]))}


def find_relic_entry(pair: Pair, owner_uid: str, query: str) -> Optional[dict]:
    from ..cli.base.pinyin_match import find_entry_by_query

    relics = pair.relics(owner_uid)
    if query in relics:
        relic_id = query
    else:
        entries = [(relic_id, get_relic_name(relic_id)) for relic_id in relics]
        entries.extend((relic_id, relic_id) for relic_id in relics)
        relic_id = find_entry_by_query(entries, query)
    if not relic_id:
        return None
    return {
        "kind": TRADE_KIND_RELIC,
        "relic_id": relic_id,
        "counter": pair.relic_counter(owner_uid, relic_id),
    }


def find_item_entry(pair: Pair, owner_uid: str, query: str) -> Optional[dict]:
    item_id = resolve_item_query(query, pair.bag(owner_uid))
    if not item_id:
        return None
    return {"kind": TRADE_KIND_ITEM, "item_id": item_id}


def find_entry(pair: Pair, owner_uid: str, kind: str, query: str) -> Optional[dict]:
    if kind == TRADE_KIND_CARD:
        return find_card_entry(pair.deck(owner_uid), query)
    if kind == TRADE_KIND_RELIC:
        return find_relic_entry(pair, owner_uid, query)
    return find_item_entry(pair, owner_uid, query)


def resolve_entry(pair: Pair, owner_uid: str, spec: str, owner_name: str, owner_is_actor: bool):
    kind, query = parse_spec(spec)
    if not query:
        return None, ("i18n_trade.err_need_spec", {})
    entry = None
    if kind:
        entry = find_entry(pair, owner_uid, kind, query)
    else:
        for candidate in TRADE_KINDS:
            entry = find_entry(pair, owner_uid, candidate, query)
            if entry is not None:
                break
    if entry is None:
        if owner_is_actor:
            return None, ("i18n_trade.err_unknown_own", {"name": query})
        return None, ("i18n_trade.err_unknown_other", {"owner": owner_name, "name": query})
    return entry, None


def take_entry(pair: Pair, work: dict, owner_uid: str, entry: dict):
    kind = entry.get("kind")
    if kind == TRADE_KIND_CARD:
        idx = match_card_index(work["deck"], entry.get("card") or {})
        if idx is None:
            return None
        return work["deck"].pop(idx)
    if kind == TRADE_KIND_RELIC:
        relic_id = str(entry.get("relic_id", ""))
        if relic_id not in work["relics"]:
            return None
        work["relics"].remove(relic_id)
        return (relic_id, pair.relic_counter(owner_uid, relic_id))
    item_id = str(entry.get("item_id", ""))
    if item_id not in work["bag"]:
        return None
    work["bag"].remove(item_id)
    return item_id


def build_plan(
    pair: Pair,
    from_uid: str,
    to_uid: str,
    give: list,
    want: list,
    name_of: Callable[[str], str],
):
    work = {}
    for uid in (from_uid, to_uid):
        work[uid] = {
            "deck": list(pair.deck(uid)),
            "relics": list(pair.relics(uid)),
            "bag": list(pair.bag(uid)),
        }
    removed_relics = {from_uid: [], to_uid: []}
    added_relics = {from_uid: [], to_uid: []}

    def transfer(owner_uid: str, receiver_uid: str, entries: list):
        for entry in entries:
            moved = take_entry(pair, work[owner_uid], owner_uid, entry)
            if moved is None:
                return (
                    "i18n_trade.err_missing",
                    {"owner": name_of(owner_uid), "name": entry_name(entry)},
                )
            kind = entry.get("kind")
            if kind == TRADE_KIND_CARD:
                work[receiver_uid]["deck"].append(moved)
            elif kind == TRADE_KIND_RELIC:
                relic_id, counter = moved
                if relic_id in work[receiver_uid]["relics"]:
                    return (
                        "i18n_trade.err_duplicate_relic",
                        {"name": name_of(receiver_uid), "relic": get_relic_name(relic_id)},
                    )
                work[receiver_uid]["relics"].append(relic_id)
                removed_relics[owner_uid].append(relic_id)
                added_relics[receiver_uid].append((relic_id, counter))
            else:
                work[receiver_uid]["bag"].append(moved)
        return None

    error = transfer(from_uid, to_uid, give)
    if error is not None:
        return None, error
    error = transfer(to_uid, from_uid, want)
    if error is not None:
        return None, error

    for uid in (from_uid, to_uid):
        if len(work[uid]["deck"]) < TRADE_MIN_DECK_CARDS:
            return None, (
                "i18n_trade.err_deck_min",
                {"name": name_of(uid), "min": TRADE_MIN_DECK_CARDS},
            )
        pre_used = calc_bag_items_weight(pair.bag(uid))
        post_used = calc_bag_items_weight(work[uid]["bag"])
        if post_used > pair.max_bag_weight(uid) and post_used > pre_used:
            return None, ("i18n_trade.err_bag_full", {"name": name_of(uid)})

    return {
        "work": work,
        "removed_relics": removed_relics,
        "added_relics": added_relics,
    }, None
