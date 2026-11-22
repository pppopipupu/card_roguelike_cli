import random
from dataclasses import asdict, replace
from ...models.state import CardState, ensure_card_state
from ...data.progression.reward_config import EPIC_CARD_RARITY, NORMAL_CARD_RARITIES
from ...data.progression.starting_deck_config import CLASS_STARTING_CARDS, LOCK_SLOT_LIMIT, STARTING_ROLL_COUNTS
from .card_distribution import CardDistributor, CardFilterSpec, CardPoolResolver

UPGRADE_SUFFIX = "+"


class DeckService:
    @staticmethod
    def new_state(card_id, upgraded=False, gems=None, enchantments=None, **flags):
        base_id = card_id.id if isinstance(card_id, CardState) else card_id
        state = CardState(id=base_id, upgraded=upgraded, gems=list(gems or []), enchantments=list(enchantments or []))
        for name in CardState.__dataclass_fields__:
            if name in ("id", "upgraded", "gems", "enchantments"):
                continue
            if name in flags:
                setattr(state, name, flags[name])
        return state

    @staticmethod
    def clone_state(state):
        source = ensure_card_state(state)
        return replace(source, gems=list(source.gems or []), enchantments=list(source.enchantments or []))

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
        return CardDistributor.class_color(player)

    @staticmethod
    def eligible_card_ids(stats, *, colors=None, rarities=None, card_types=None, allow_coop=False, allow_curse=False, allow_duel=False, allow_event=False, allow_token=False, require_available=True, exclude_upgraded=True):
        spec = CardFilterSpec(
            colors=None if colors is None else tuple(colors),
            rarities=None if rarities is None else tuple(rarities),
            card_types=None if card_types is None else tuple(card_types),
            allow_coop=allow_coop,
            allow_curse=allow_curse,
            allow_duel=allow_duel,
            allow_event=allow_event,
            allow_token=allow_token,
            require_available=require_available,
            exclude_upgraded=exclude_upgraded,
        )
        return CardPoolResolver.filter_cards(stats, spec)

    @staticmethod
    def get_reward_card_pool(run, player, stats, *, include_coop=False, difficulty=None):
        if difficulty is not None:
            channel = CardDistributor.resolve_battle_channel(difficulty)
            return CardDistributor.get_pool(channel, run, player, stats, include_coop=include_coop)
        return CardDistributor.get_pool(
            "battle_elite",
            run,
            player,
            stats,
            include_coop=include_coop,
            rarities=NORMAL_CARD_RARITIES,
        )

    @staticmethod
    def get_shop_card_pool(run, player, stats, *, include_coop=False):
        allow_coop = (run is not None and run.player_count() > 1) or include_coop
        return CardDistributor.get_pool("shop", run, player, stats, include_coop=allow_coop)

    @staticmethod
    def get_epic_card_pool(run, player, stats):
        return CardDistributor.get_pool("treasure", run, player, stats, rarities=(EPIC_CARD_RARITY,))

    @staticmethod
    def get_class_spell_pool(player, stats, include_coop=False):
        return CardDistributor.get_pool("rest_meditate", None, player, stats, include_coop=include_coop)

    @staticmethod
    def serialize_cards(cards) -> list[dict]:
        return [asdict(ensure_card_state(c)) for c in (cards or [])]

    @staticmethod
    def clone_cards(cards) -> list[CardState]:
        return [DeckService.clone_state(c) for c in (cards or [])]

    @staticmethod
    def assemble_starting_deck(
        stats,
        *,
        include_random_rolls: bool = True,
        consume_pending: bool = True,
    ) -> list[CardState]:
        from ...entities import ALL_CARDS

        selected_class = getattr(stats, "selected_class", "法师")
        selected_subclass = getattr(stats, "selected_subclass", "")
        locked_cards = list(getattr(stats, "locked_cards", []) or [])[:LOCK_SLOT_LIMIT]
        if consume_pending:
            g_card = getattr(stats, "guaranteed_card", None)
            if g_card:
                if g_card not in locked_cards:
                    locked_cards.append(g_card)
                stats.guaranteed_card = None
            p_pool = getattr(stats, "purchased_pool", [])
            if p_pool:
                locked_cards.extend(p_pool)
                stats.purchased_pool = []
            stats.locked_cards = locked_cards[:LOCK_SLOT_LIMIT]

        deck = list(CLASS_STARTING_CARDS.get(selected_class, CLASS_STARTING_CARDS["法师"])) + list(locked_cards)
        if include_random_rolls:
            allowed_colors = [CardDistributor.class_color(stats), "neutral"]
            commons = [
                cid
                for cid in DeckService.eligible_card_ids(stats, colors=allowed_colors, rarities=("common",))
                if cid != "time_stop"
            ]
            rares = [
                cid
                for cid in DeckService.eligible_card_ids(stats, colors=allowed_colors, rarities=("rare",))
                if cid != "time_stop"
            ]
            epics = [
                cid
                for cid in DeckService.eligible_card_ids(stats, colors=allowed_colors, rarities=("epic",))
                if cid != "time_stop"
            ]
            target_counts = dict(STARTING_ROLL_COUNTS)
            for cid in locked_cards:
                c_obj = ALL_CARDS.get(cid)
                rarity = getattr(c_obj, "rarity", "common") if c_obj else "common"
                if rarity not in target_counts:
                    rarity = "common"
                if target_counts[rarity] > 0:
                    target_counts[rarity] -= 1
                else:
                    for fallback_rarity in ("common", "rare", "epic"):
                        if target_counts[fallback_rarity] > 0:
                            target_counts[fallback_rarity] -= 1
                            break
            for rarity, pool in (("common", commons), ("rare", rares), ("epic", epics)):
                for _ in range(target_counts[rarity]):
                    if pool:
                        deck.append(random.choice(pool))
        if selected_class == "法师" and selected_subclass == "时序法师":
            deck.append("time_stop")
        states = [ensure_card_state(c) for c in deck]
        if include_random_rolls:
            from .enchantment_service import apply_starting_enchantments
            apply_starting_enchantments(states)
        return states
