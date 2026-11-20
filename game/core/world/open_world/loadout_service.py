from collections import Counter
from typing import Optional, TypeGuard

from ....data.grid_map_config import SP_CONFIG
from ....data.open_world_config import (
    OPEN_WORLD_COMBAT_FLAG,
    OPEN_WORLD_DEFAULT_BASE_HP,
    OPEN_WORLD_NINJA_BASE_HP,
    OPEN_WORLD_STARTING_GOLD,
    OPEN_WORLD_WARRIOR_BASE_HP,
)
from ....data.room_interact_data import BAG_DEFAULT_MAX_WEIGHT
from ....models.state import CardState, GameRun, PlayerState, UserStats, ensure_card_state
from ...inventory.bag_service import get_item_display_name, resolve_item_query, use_bag_item
from ...inventory.deck_service import DeckService
from ...inventory.relic_service import init_relic_counter
from ...text.events import LocaleText
from ...text.pipeline import render_text_node


def is_open_world_run(run: Optional[GameRun]) -> TypeGuard[GameRun]:
    if run is None:
        return False
    if run.node_data.get(OPEN_WORLD_COMBAT_FLAG) or run.node_data.get("yog_quest"):
        return True
    floor_map = getattr(run, "floor_map", None)
    return bool(floor_map and floor_map.floor_flags.get("yog_quest"))


def _card_signature(card: CardState) -> tuple:
    return (card.id, bool(card.upgraded), tuple(card.gems or []))


class OpenWorldLoadoutService:
    @staticmethod
    def ensure_open_world_deck(stats: UserStats) -> list[CardState]:
        if not getattr(stats, "open_world_deck", None):
            stats.open_world_deck = DeckService.assemble_starting_deck(
                stats,
                include_random_rolls=False,
                consume_pending=False,
            )
        return DeckService.clone_cards(stats.open_world_deck)

    @staticmethod
    def base_max_hp(stats: UserStats) -> int:
        selected_class = getattr(stats, "selected_class", "法师")
        if selected_class == "战士":
            base = OPEN_WORLD_WARRIOR_BASE_HP
        elif selected_class == "蕾忍":
            base = OPEN_WORLD_NINJA_BASE_HP
        else:
            base = OPEN_WORLD_DEFAULT_BASE_HP
        return base + int(getattr(stats, "town_health_bonus", 0) or 0)

    @staticmethod
    def get_vitals(stats: UserStats) -> tuple[int, int, int, int, int]:
        default_max_hp = OpenWorldLoadoutService.base_max_hp(stats)
        max_sp = int(SP_CONFIG["default_max_sp"])
        raw_max_hp = int(getattr(stats, "open_world_max_hp", 0) or 0)
        max_hp = raw_max_hp if raw_max_hp > 0 else default_max_hp
        raw_hp = int(getattr(stats, "open_world_hp", 0) or 0)
        hp = min(max_hp, raw_hp) if raw_hp > 0 else max_hp
        raw_sp = int(getattr(stats, "open_world_sp", -1))
        sp = min(max_sp, max(0, raw_sp)) if raw_sp >= 0 else max_sp
        raw_gold = int(getattr(stats, "open_world_gold", -1))
        gold = raw_gold if raw_gold >= 0 else OPEN_WORLD_STARTING_GOLD
        return hp, max_hp, sp, max_sp, gold

    @staticmethod
    def ensure_vitals(stats: UserStats) -> tuple[int, int, int, int, int]:
        hp, max_hp, sp, max_sp, gold = OpenWorldLoadoutService.get_vitals(stats)
        stats.open_world_hp = hp
        stats.open_world_max_hp = max_hp
        stats.open_world_sp = sp
        stats.open_world_gold = gold
        return hp, max_hp, sp, max_sp, gold

    @staticmethod
    def apply_loadout_to_player(stats: UserStats, player: PlayerState) -> PlayerState:
        player.deck = OpenWorldLoadoutService.ensure_open_world_deck(stats)
        player.relics = list(getattr(stats, "open_world_relics", []) or [])
        player.relic_counters = dict(getattr(stats, "open_world_relic_counters", {}) or {})
        player.bag_items = list(getattr(stats, "open_world_bag", []) or [])
        player.bag_max_weight = BAG_DEFAULT_MAX_WEIGHT
        for rid in player.relics:
            init_relic_counter(player, rid)
        return player

    @staticmethod
    def build_player_state(
        user_id: str,
        stats: UserStats,
        *,
        hp: Optional[int] = None,
        max_hp: Optional[int] = None,
        gold: Optional[int] = None,
        stage: int = 0,
    ) -> PlayerState:
        selected_class = getattr(stats, "selected_class", "法师")
        selected_subclass = getattr(stats, "selected_subclass", "")
        cur_hp, cur_max_hp, cur_sp, max_sp, cur_gold = OpenWorldLoadoutService.ensure_vitals(stats)
        resolved_max_hp = max_hp if max_hp is not None else cur_max_hp
        resolved_hp = hp if hp is not None else min(cur_hp, resolved_max_hp)
        resolved_gold = gold if gold is not None else cur_gold
        player = PlayerState(
            hp=resolved_hp,
            max_hp=resolved_max_hp,
            shield=0,
            gold=resolved_gold,
            stage=stage,
            name=getattr(stats, "player_name", user_id),
            deck=[],
            relics=[],
            abilities=[],
            subclass=selected_subclass,
            selected_class=selected_class,
            sp=cur_sp,
            max_sp=max_sp,
            bag_max_weight=BAG_DEFAULT_MAX_WEIGHT,
        )
        return OpenWorldLoadoutService.apply_loadout_to_player(stats, player)

    @staticmethod
    def sync_player_to_stats(stats: UserStats, player: PlayerState) -> None:
        stats.open_world_deck = DeckService.clone_cards(player.deck)
        stats.open_world_relics = list(getattr(player, "relics", []) or [])
        stats.open_world_relic_counters = dict(getattr(player, "relic_counters", {}) or {})
        stats.open_world_bag = list(getattr(player, "bag_items", []) or [])
        max_hp = max(1, int(getattr(player, "max_hp", 0) or OpenWorldLoadoutService.base_max_hp(stats)))
        stats.open_world_max_hp = max_hp
        if getattr(player, "hp", 0) > 0:
            stats.open_world_hp = min(max_hp, int(player.hp))
        stats.open_world_sp = max(0, int(getattr(player, "sp", SP_CONFIG["default_max_sp"])))
        stats.open_world_gold = max(0, int(getattr(player, "gold", 0)))

    @staticmethod
    def sync_run_to_stats(save_manager, run: Optional[GameRun], exclude_uid: Optional[str] = None) -> None:
        if not is_open_world_run(run):
            return
        if run.node_data.get("pvp_match_id"):
            return
        if run.node_data.get("open_world_death_handled"):
            return
        players = getattr(run, "players", None) or {}
        if players:
            targets = [
                (uid, player)
                for uid, player in players.items()
                if not getattr(player, "is_mercenary", False)
            ]
        elif run.player is not None:
            targets = [(run.user_id, run.player)]
        else:
            return
        for uid, player in targets:
            if exclude_uid and uid == exclude_uid:
                continue
            if getattr(player, "hp", 0) <= 0:
                continue
            stats = save_manager.load_stats(uid)
            OpenWorldLoadoutService.sync_player_to_stats(stats, player)
            save_manager.save_stats(uid, stats)

    @staticmethod
    def snapshot_loadout(
        stats: UserStats,
        player: Optional[PlayerState] = None,
    ) -> dict:
        if player is not None:
            deck = list(player.deck or [])
            if not deck:
                deck = OpenWorldLoadoutService.ensure_open_world_deck(stats)
            relics = list(getattr(player, "relics", []) or [])
            counters = dict(getattr(player, "relic_counters", {}) or {})
            bag_items = list(getattr(player, "bag_items", []) or [])
            max_hp = int(getattr(player, "max_hp", 0) or OpenWorldLoadoutService.base_max_hp(stats))
        else:
            deck = OpenWorldLoadoutService.ensure_open_world_deck(stats)
            relics = list(getattr(stats, "open_world_relics", []) or [])
            counters = dict(getattr(stats, "open_world_relic_counters", {}) or {})
            bag_items = list(getattr(stats, "open_world_bag", []) or [])
            _, max_hp, _, _, _ = OpenWorldLoadoutService.get_vitals(stats)
        return {
            "deck": DeckService.serialize_cards(deck),
            "relics": relics,
            "relic_counters": counters,
            "bag_items": bag_items,
            "max_hp": max_hp,
        }

    @staticmethod
    def strip_on_death(stats: UserStats) -> None:
        stats.open_world_deck = []
        stats.open_world_relics = []
        stats.open_world_relic_counters = {}
        stats.open_world_bag = []
        _, max_hp, _, max_sp, _ = OpenWorldLoadoutService.get_vitals(stats)
        stats.open_world_max_hp = max_hp
        stats.open_world_hp = max_hp
        stats.open_world_sp = max_sp
        stats.open_world_gold = OPEN_WORLD_STARTING_GOLD

    @staticmethod
    def use_bag_item_from_stats(battle_engine, user_id: str, stats: UserStats, query: str) -> Optional[str]:
        bag_items = list(getattr(stats, "open_world_bag", []) or [])
        if not resolve_item_query(query, bag_items):
            return None
        p_tmp = OpenWorldLoadoutService.build_player_state(user_id, stats)
        tmp_run = GameRun(user_id=user_id, node_type="town", player=p_tmp)
        msg = use_bag_item(battle_engine, tmp_run, query)
        OpenWorldLoadoutService.sync_player_to_stats(stats, p_tmp)
        return msg

    @staticmethod
    def drop_bag_item_from_stats(stats: UserStats, query: str) -> str:
        clean = (query or "").strip()
        if not clean:
            return render_text_node(LocaleText(key="i18n_open_world.bag.drop_need_arg"))
        bag_items = list(getattr(stats, "open_world_bag", []) or [])
        if not bag_items:
            return render_text_node(LocaleText(key="i18n_open_world.bag.drop_empty"))
        item_id = resolve_item_query(clean, bag_items)
        if not item_id:
            return render_text_node(LocaleText(key="i18n_open_world.bag.drop_not_found", params={"query": clean}))
        stats.open_world_bag.remove(item_id)
        return render_text_node(
            LocaleText(key="i18n_open_world.bag.drop_success", params={"name": get_item_display_name(item_id)})
        )

    @staticmethod
    def reclaim_ghost_loadout(
        stats: UserStats,
        ghost: dict,
        player: Optional[PlayerState] = None,
    ) -> tuple[int, int]:
        old_deck = [ensure_card_state(c) for c in (ghost.get("deck") or [])]
        old_relics = [str(r) for r in (ghost.get("relics") or []) if r]
        old_counters = dict(ghost.get("relic_counters") or {})

        starter = DeckService.assemble_starting_deck(
            stats,
            include_random_rolls=False,
            consume_pending=False,
        )
        starter_counts = Counter(_card_signature(card) for card in starter)
        current_deck = list(getattr(stats, "open_world_deck", []) or [])
        extra_cards: list[CardState] = []
        for card in current_deck:
            sig = _card_signature(card)
            if starter_counts.get(sig, 0) > 0:
                starter_counts[sig] -= 1
            else:
                extra_cards.append(DeckService.clone_state(card))

        if old_deck:
            stats.open_world_deck = DeckService.clone_cards(old_deck) + extra_cards

        current_relics = list(getattr(stats, "open_world_relics", []) or [])
        current_counters = dict(getattr(stats, "open_world_relic_counters", {}) or {})
        for rid in old_relics:
            if rid not in current_relics:
                current_relics.append(rid)
        for rid, val in old_counters.items():
            current_counters.setdefault(str(rid), int(val))
        stats.open_world_relics = current_relics
        stats.open_world_relic_counters = current_counters

        if player is not None:
            player.deck = DeckService.clone_cards(stats.open_world_deck)
            player.relics = list(stats.open_world_relics)
            player.relic_counters = dict(stats.open_world_relic_counters)
            for rid in player.relics:
                init_relic_counter(player, rid)

        return (len(old_deck), len(old_relics))
