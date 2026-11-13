from dataclasses import replace
from ...models.state import CardState, ensure_card_state
from ...data.reward_config import EPIC_CARD_RARITY, NORMAL_CARD_RARITIES

UPGRADE_SUFFIX = "+"


class DeckService:
    @staticmethod
    def new_state(card_id, upgraded=False, gems=None, **flags):
        base_id = card_id.id if isinstance(card_id, CardState) else card_id
        state = CardState(id=base_id, upgraded=upgraded, gems=list(gems or []))
        for name in CardState.__dataclass_fields__:
            if name in ("id", "upgraded", "gems"):
                continue
            if name in flags:
                setattr(state, name, flags[name])
        return state

    @staticmethod
    def clone_state(state):
        source = ensure_card_state(state)
        return replace(source, gems=list(source.gems or []))

    @staticmethod
    def upgrade_state(state):
        upgraded = DeckService.clone_state(state)
        upgraded.upgraded = True
        return upgraded

    @staticmethod
    def _prepare(card_id, upgraded):
        state = DeckService.clone_state(card_id)
        if upgraded:
            state.upgraded = True
        return state

    @staticmethod
    def _add(pile, card_id, upgraded):
        state = DeckService._prepare(card_id, upgraded)
        pile.append(state)
        return state

    @staticmethod
    def add_card_to_deck(player, card_id, upgraded=False):
        return DeckService._add(player.deck, card_id, upgraded)

    @staticmethod
    def add_card_to_hand(player, card_id, upgraded=False):
        return DeckService._add(player.hand, card_id, upgraded)

    @staticmethod
    def add_card_to_draw(player, card_id, upgraded=False):
        return DeckService._add(player.draw_pile, card_id, upgraded)

    @staticmethod
    def add_card_to_discard(player, card_id, upgraded=False):
        return DeckService._add(player.discard_pile, card_id, upgraded)

    @staticmethod
    def add_card_to_exhaust(player, card_id, upgraded=False):
        return DeckService._add(player.exhaust_pile, card_id, upgraded)

    @staticmethod
    def grouped_deck(deck):
        groups = {}
        for entry in deck:
            state = ensure_card_state(entry)
            key = (state.id, state.upgraded, tuple(state.gems), state.exhaust_used, state.fleeting_used)
            if key in groups:
                groups[key][1] += 1
            else:
                groups[key] = [state, 1]
        return [(groups[key][0], groups[key][1]) for key in sorted(groups)]

    @staticmethod
    def _class_color(player):
        return "warrior" if getattr(player, "selected_class", "法师") == "战士" else "wizard"

    @staticmethod
    def eligible_card_ids(stats, *, colors=None, rarities=None, card_types=None, allow_coop=False, allow_curse=False, allow_duel=False, allow_event=False, require_available=True, exclude_upgraded=True):
        from ...entities import ALL_CARDS
        from ...entities.cards.base import card_matches_color
        from ...entities.cards.market import is_card_available
        color_allow = None if colors is None else tuple(colors)
        rarity_allow = None if rarities is None else tuple(rarities)
        type_allow = None if card_types is None else tuple(card_types)
        pool = []
        for cid, card in ALL_CARDS.items():
            if exclude_upgraded and cid.endswith(UPGRADE_SUFFIX):
                continue
            if not allow_curse and cid.startswith("curse_"):
                continue
            if not allow_duel and cid.startswith("duel_"):
                continue
            if color_allow is not None and not any(card_matches_color(card, c) for c in color_allow):
                continue
            if rarity_allow is not None and getattr(card, "rarity", "common") not in rarity_allow:
                continue
            if type_allow is not None and getattr(card, "type", "") not in type_allow:
                continue
            if not allow_coop and getattr(card, "coop_only", False):
                continue
            if not allow_event and (getattr(card, "event_only", False) or getattr(card, "life_merchant_only", False)):
                continue
            if require_available and not is_card_available(cid, stats):
                continue
            pool.append(cid)
        return pool

    @staticmethod
    def get_reward_card_pool(run, player, stats, *, include_coop=False):
        from ...entities.cards.market import is_coop_only
        color = DeckService._class_color(player)
        pool = DeckService.eligible_card_ids(
            stats,
            colors=(color, "neutral"),
            rarities=NORMAL_CARD_RARITIES,
        )
        if include_coop:
            pool.extend(
                cid
                for cid in DeckService.eligible_card_ids(
                    stats,
                    rarities=NORMAL_CARD_RARITIES,
                    allow_coop=True,
                )
                if is_coop_only(cid)
            )
        return pool

    @staticmethod
    def get_shop_card_pool(run, player, stats, *, include_coop=False):
        color = DeckService._class_color(player)
        allow_coop = (run is not None and run.player_count() > 1) or include_coop
        return DeckService.eligible_card_ids(
            stats,
            colors=(color, "neutral"),
            rarities=NORMAL_CARD_RARITIES,
            allow_coop=allow_coop,
        )

    @staticmethod
    def get_epic_card_pool(run, player, stats):
        color = DeckService._class_color(player)
        return DeckService.eligible_card_ids(
            stats,
            colors=(color, "neutral"),
            rarities=(EPIC_CARD_RARITY,),
        )

    @staticmethod
    def get_class_spell_pool(player, stats, include_coop=False):
        color = DeckService._class_color(player)
        return DeckService.eligible_card_ids(
            stats,
            colors=(color,),
            card_types=("spell",),
            rarities=NORMAL_CARD_RARITIES,
            allow_coop=include_coop,
        )
