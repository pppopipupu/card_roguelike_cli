import random
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from ...data.cards.card_distribution_config import (
    BATTLE_DIFFICULTY_CHANNEL_MAP,
    CHANNEL_POLICIES,
    CLASS_TO_CARD_COLOR,
    DEFAULT_CARD_COLOR,
    DEFAULT_RARITY_WEIGHTS,
    KEY_SCHOLAR_REPLACE_CONFIG,
    LATE_FLOOR_THRESHOLD,
    LATE_STAGE_THRESHOLD,
    UPGRADE_SUFFIX,
)

CardModifierHook = Callable[[str, Any, Any, bool, Any], str]


@dataclass(frozen=True)
class CardFilterSpec:
    colors: tuple[str, ...] | None = None
    rarities: tuple[str, ...] | None = None
    card_types: tuple[str, ...] | None = None
    allow_coop: bool = False
    only_coop: bool = False
    allow_curse: bool = False
    allow_duel: bool = False
    allow_event: bool = False
    allow_token: bool = False
    require_available: bool = True
    exclude_upgraded: bool = True
    exclude_ids: frozenset[str] = frozenset()


class CardPoolResolver:
    @staticmethod
    def filter_cards(stats: Any, spec: CardFilterSpec) -> list[str]:
        from ...entities import ALL_CARDS
        from ...entities.cards.base import card_matches_color
        from ...entities.cards.market import is_card_available

        pool: list[str] = []
        for cid, card in ALL_CARDS.items():
            if spec.exclude_upgraded and cid.endswith(UPGRADE_SUFFIX):
                continue
            if cid in spec.exclude_ids:
                continue
            if not spec.allow_curse and cid.startswith("curse_"):
                continue
            if not spec.allow_duel and cid.startswith("duel_"):
                continue
            is_coop_card = bool(getattr(card, "coop_only", False))
            if spec.only_coop and not is_coop_card:
                continue
            if not spec.allow_coop and not spec.only_coop and is_coop_card:
                continue
            if spec.colors is not None and not any(card_matches_color(card, c) for c in spec.colors):
                continue
            if spec.rarities is not None and getattr(card, "rarity", "common") not in spec.rarities:
                continue
            if spec.card_types is not None and getattr(card, "type", "") not in spec.card_types:
                continue
            if not spec.allow_event and (getattr(card, "event_only", False) or getattr(card, "life_merchant_only", False)):
                continue
            if not spec.allow_token and getattr(card, "token", False):
                continue
            if spec.require_available and not is_card_available(cid, stats):
                continue
            pool.append(cid)
        return pool


class ChannelPolicyRegistry:
    _policies: dict[str, dict[str, Any]] = {k: dict(v) for k, v in CHANNEL_POLICIES.items()}

    @classmethod
    def register(cls, channel: str, policy: dict[str, Any]) -> None:
        cls._policies[channel] = dict(policy)

    @classmethod
    def get(cls, channel: str) -> dict[str, Any]:
        if channel not in cls._policies:
            raise KeyError(f"Unknown card distribution channel: {channel}")
        return cls._policies[channel]

    @staticmethod
    def resolve_floor_tier(run: Any = None, player: Any = None) -> str:
        fm = getattr(run, "floor_map", None) if run is not None else None
        if fm is not None:
            floor_idx = float(getattr(fm, "floor_index", 1) or 1)
            return "late" if floor_idx >= LATE_FLOOR_THRESHOLD else "early"
        target_player = player if player is not None else (getattr(run, "player", None) if run is not None else None)
        stage = int(getattr(target_player, "stage", 1) or 1) if target_player is not None else 1
        return "late" if stage >= LATE_STAGE_THRESHOLD else "early"

    @staticmethod
    def resolve_colors(
        policy: dict[str, Any],
        player: Any = None,
        *,
        override_colors: tuple[str, ...] | list[str] | None = None,
    ) -> tuple[str, ...] | None:
        if override_colors is not None:
            return tuple(override_colors)
        mode = policy.get("color_mode", "player_and_neutral")
        if mode == "player_and_neutral":
            return (CardDistributor.class_color(player), "neutral")
        if mode == "player_only":
            return (CardDistributor.class_color(player),)
        if mode == "fixed":
            raw = policy.get("colors")
            return None if raw is None else tuple(raw)
        if mode == "all":
            return None
        return None

    @classmethod
    def resolve_rarities(
        cls,
        policy: dict[str, Any],
        run: Any = None,
        player: Any = None,
        *,
        override_rarities: tuple[str, ...] | list[str] | None = None,
    ) -> tuple[str, ...] | None:
        if override_rarities is not None:
            return tuple(override_rarities)
        if "rarities" in policy:
            raw = policy["rarities"]
            return None if raw is None else tuple(raw)
        tier = cls.resolve_floor_tier(run, player)
        tier_key = "late_rarities" if tier == "late" else "early_rarities"
        raw = policy.get(tier_key)
        return None if raw is None else tuple(raw)


class CardModifierRegistry:
    _hooks: dict[str, CardModifierHook] = {}

    @classmethod
    def register(cls, name: str, hook: CardModifierHook) -> None:
        cls._hooks[name] = hook

    @classmethod
    def apply(
        cls,
        modifier_names: tuple[str, ...] | list[str],
        cards: list[str],
        run: Any,
        player: Any,
        include_coop: bool,
        rng: Any = None,
    ) -> list[str]:
        if not modifier_names or not cards:
            return cards
        result: list[str] = []
        for cid in cards:
            cur = cid
            for name in modifier_names:
                hook = cls._hooks.get(name)
                if hook is not None:
                    cur = hook(cur, run, player, include_coop, rng)
            result.append(cur)
        return result


def _fireball_replace_hook(cid: str, run: Any, player: Any, include_coop: bool, rng: Any) -> str:
    if run is None:
        return cid
    from ...models.state import check_and_replace_fireball

    return check_and_replace_fireball(run, cid)


def _key_scholar_replace_hook(cid: str, run: Any, player: Any, include_coop: bool, rng: Any) -> str:
    if include_coop or player is None:
        return cid
    if getattr(player, "subclass", "") != KEY_SCHOLAR_REPLACE_CONFIG["subclass"]:
        return cid
    from ...entities import ALL_CARDS

    card = ALL_CARDS.get(cid)
    if card is None:
        return cid
    if getattr(card, "color", "") != KEY_SCHOLAR_REPLACE_CONFIG["source_color"]:
        return cid
    if getattr(card, "rarity", "common") in KEY_SCHOLAR_REPLACE_CONFIG["excluded_rarities"]:
        return cid
    active_rng = rng if rng is not None else random
    if active_rng.random() < float(KEY_SCHOLAR_REPLACE_CONFIG["chance"]):
        return str(KEY_SCHOLAR_REPLACE_CONFIG["target_card"])
    return cid


CardModifierRegistry.register("fireball_replace", _fireball_replace_hook)
CardModifierRegistry.register("key_scholar_replace", _key_scholar_replace_hook)


class WeightedCardSampler:
    @staticmethod
    def card_weight(
        cid: str,
        *,
        rarity_weights: dict[str, float] | None = None,
        weight_fn: Callable[[str, Any], float] | None = None,
    ) -> float:
        from ...entities import ALL_CARDS

        card = ALL_CARDS.get(cid)
        if weight_fn is not None:
            return max(0.0, float(weight_fn(cid, card)))
        weights = rarity_weights if rarity_weights is not None else DEFAULT_RARITY_WEIGHTS
        rarity = getattr(card, "rarity", "common") if card is not None else "common"
        return max(0.0, float(weights.get(rarity, 1.0)))

    @classmethod
    def sample(
        cls,
        pool: list[str],
        count: int,
        *,
        rarity_weights: dict[str, float] | None = None,
        weighted: bool = True,
        allow_duplicates: bool = False,
        rng: Any = None,
        weight_fn: Callable[[str, Any], float] | None = None,
    ) -> list[str]:
        if count <= 0 or not pool:
            return []
        active_rng = rng if rng is not None else random
        candidates = list(pool) if allow_duplicates else list(dict.fromkeys(pool))
        target_count = count if allow_duplicates else min(count, len(candidates))
        if not weighted:
            if allow_duplicates:
                return [active_rng.choice(candidates) for _ in range(target_count)]
            return active_rng.sample(candidates, target_count)

        item_weights = [
            cls.card_weight(cid, rarity_weights=rarity_weights, weight_fn=weight_fn)
            for cid in candidates
        ]
        chosen: list[str] = []
        for _ in range(target_count):
            total_weight = sum(item_weights)
            if total_weight <= 0.0:
                idx = active_rng.randrange(len(candidates))
            else:
                threshold = active_rng.uniform(0.0, total_weight)
                acc = 0.0
                idx = len(candidates) - 1
                for i, w in enumerate(item_weights):
                    acc += w
                    if acc >= threshold:
                        idx = i
                        break
            chosen.append(candidates[idx])
            if not allow_duplicates:
                candidates.pop(idx)
                item_weights.pop(idx)
        return chosen


class CardDistributor:
    @staticmethod
    def class_color(player: Any) -> str:
        selected = getattr(player, "selected_class", "") if player is not None else ""
        return CLASS_TO_CARD_COLOR.get(selected, DEFAULT_CARD_COLOR)

    @staticmethod
    def resolve_battle_channel(difficulty: str | None) -> str:
        return BATTLE_DIFFICULTY_CHANNEL_MAP.get(str(difficulty or "normal"), "battle_normal")

    @staticmethod
    def get_pool(
        channel: str,
        run: Any = None,
        player: Any = None,
        stats: Any = None,
        *,
        include_coop: bool = False,
        colors: tuple[str, ...] | list[str] | None = None,
        rarities: tuple[str, ...] | list[str] | None = None,
        card_types: tuple[str, ...] | list[str] | None = None,
        require_available: bool | None = None,
    ) -> list[str]:
        policy = ChannelPolicyRegistry.get(channel)
        resolved_colors = ChannelPolicyRegistry.resolve_colors(policy, player, override_colors=colors)
        resolved_rarities = ChannelPolicyRegistry.resolve_rarities(policy, run, player, override_rarities=rarities)
        raw_types = card_types if card_types is not None else policy.get("card_types")
        resolved_types = None if raw_types is None else tuple(raw_types)
        req_avail = bool(policy.get("require_available", True)) if require_available is None else require_available
        allow_coop = bool(policy.get("allow_coop", False)) or (bool(policy.get("allow_coop_when_flag")) and include_coop)

        spec = CardFilterSpec(
            colors=resolved_colors,
            rarities=resolved_rarities,
            card_types=resolved_types,
            allow_coop=allow_coop,
            require_available=req_avail,
        )
        pool = CardPoolResolver.filter_cards(stats, spec)
        if include_coop and policy.get("append_coop_cards"):
            coop_spec = CardFilterSpec(
                rarities=resolved_rarities,
                card_types=resolved_types,
                allow_coop=True,
                only_coop=True,
                require_available=req_avail,
            )
            pool.extend(CardPoolResolver.filter_cards(stats, coop_spec))
        if not pool and policy.get("fallback_all_colors") and resolved_colors is not None:
            fallback_spec = CardFilterSpec(
                colors=None,
                rarities=resolved_rarities,
                card_types=resolved_types,
                allow_coop=allow_coop,
                require_available=req_avail,
            )
            pool = CardPoolResolver.filter_cards(stats, fallback_spec)
        return pool

    @staticmethod
    def roll_from_pool(
        pool: list[str],
        count: int,
        *,
        weighted: bool = True,
        rarity_weights: dict[str, float] | None = None,
        allow_duplicates: bool = False,
        run: Any = None,
        player: Any = None,
        include_coop: bool = False,
        modifiers: tuple[str, ...] | list[str] = (),
        rng: Any = None,
        weight_fn: Callable[[str, Any], float] | None = None,
    ) -> list[str]:
        picks = WeightedCardSampler.sample(
            pool,
            count,
            rarity_weights=rarity_weights,
            weighted=weighted,
            allow_duplicates=allow_duplicates,
            rng=rng,
            weight_fn=weight_fn,
        )
        if modifiers:
            picks = CardModifierRegistry.apply(modifiers, picks, run, player, include_coop, rng=rng)
        return picks

    @classmethod
    def roll(
        cls,
        channel: str,
        run: Any = None,
        player: Any = None,
        stats: Any = None,
        *,
        count: int | None = None,
        include_coop: bool = False,
        colors: tuple[str, ...] | list[str] | None = None,
        rarities: tuple[str, ...] | list[str] | None = None,
        card_types: tuple[str, ...] | list[str] | None = None,
        require_available: bool | None = None,
        apply_modifiers: bool = True,
        rng: Any = None,
        fallback: str | None = None,
    ) -> list[str]:
        policy = ChannelPolicyRegistry.get(channel)
        target_player = player if player is not None else (getattr(run, "player", None) if run is not None else None)
        pool = cls.get_pool(
            channel,
            run,
            target_player,
            stats,
            include_coop=include_coop,
            colors=colors,
            rarities=rarities,
            card_types=card_types,
            require_available=require_available,
        )
        target_count = int(count if count is not None else policy.get("count", 3))
        if not pool:
            fb = fallback if fallback is not None else policy.get("fallback")
            return [fb] if fb else []
        modifiers = tuple(policy.get("modifiers", ())) if apply_modifiers else ()
        return cls.roll_from_pool(
            pool,
            target_count,
            weighted=bool(policy.get("weighted", True)),
            rarity_weights=policy.get("rarity_weights"),
            allow_duplicates=bool(policy.get("allow_duplicates", False)),
            run=run,
            player=target_player,
            include_coop=include_coop,
            modifiers=modifiers,
            rng=rng,
        )

    @classmethod
    def roll_one(
        cls,
        channel: str,
        run: Any = None,
        player: Any = None,
        stats: Any = None,
        *,
        include_coop: bool = False,
        colors: tuple[str, ...] | list[str] | None = None,
        rarities: tuple[str, ...] | list[str] | None = None,
        card_types: tuple[str, ...] | list[str] | None = None,
        require_available: bool | None = None,
        apply_modifiers: bool = True,
        rng: Any = None,
        fallback: str | None = None,
    ) -> str | None:
        picks = cls.roll(
            channel,
            run,
            player,
            stats,
            count=1,
            include_coop=include_coop,
            colors=colors,
            rarities=rarities,
            card_types=card_types,
            require_available=require_available,
            apply_modifiers=apply_modifiers,
            rng=rng,
            fallback=fallback,
        )
        return picks[0] if picks else None
