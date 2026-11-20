import random
from ...data.buff_data import BUFF_CONFIG
from ...data.locale_data import get_locale_text
from ...data.ninja_card_data_basic import NINJA_FOOD_TOKEN_IDS
from ...models.events import LexKelaChangedEvent
from ...models.state import Card, CardState, GameRun


def add_ninja_buff(engine, entity, buff_id: str, stacks: int = 1) -> None:
    if entity is None or stacks <= 0:
        return
    cfg = BUFF_CONFIG.get(buff_id, {})
    engine._add_buff_to(entity, buff_id, cfg.get("name", buff_id), cfg.get("desc", ""), stacks)


def get_card_ninja_tags(card) -> tuple[str, ...]:
    if card is None:
        return ()
    result: list[str] = [str(x) for x in (getattr(card, "ninja_tags", ()) or ())]
    for tag in getattr(card, "tags", ()) or ():
        tname = getattr(tag, "name", "")
        if tname in ("blade", "hand") and tname not in result:
            result.append(tname)
    return tuple(result)


def has_ninja_tag(card, tag: str) -> bool:
    return tag in get_card_ninja_tags(card)


def effective_science_cost_a(card, player) -> int:
    cost_a = int(getattr(card, "cost_a", 0) or 0)
    if cost_a <= 0 or not getattr(card, "science", False):
        return cost_a
    lex = max(0, int(getattr(player, "lex_kela", 0) or 0))
    return max(0, cost_a - lex)


def resolve_card_effective_cost_a(card, card_state, player) -> int:
    base_a = int(getattr(card, "cost_a", 0) or 0)
    if base_a == -1:
        return -1
    temp_a = getattr(card_state, "temp_cost_a", None) if card_state is not None else None
    if temp_a is not None:
        eff = max(0, int(temp_a))
    else:
        delta = int(getattr(card_state, "battle_cost_delta_a", 0) or 0) if card_state is not None else 0
        eff = max(0, base_a + delta)
    if getattr(card, "science", False) and eff > 0 and player is not None:
        lex = max(0, int(getattr(player, "lex_kela", 0) or 0))
        eff = max(0, eff - lex)
    if player is not None and has_ninja_tag(card, "ninjutsu"):
        if any(b.id == "plasma_arrow" and b.stacks > 0 for b in player.buffs):
            return 0
    return eff


def scramble_hand_costs(player, low: int = 0, high: int = 3) -> list[int]:
    results = []
    for st in player.hand:
        val = random.randint(low, high)
        st.temp_cost_a = val
        results.append(val)
    return results


def change_lex_kela(engine, run: GameRun, player, delta: int, reason: str = "", source_card_id: str = "") -> int:
    if player is None or delta == 0:
        return 0
    if delta > 0 and any(b.id == "no_lexkela" and b.stacks > 0 for b in player.buffs):
        engine._log_event(run, get_locale_text("i18n_cards_ninja.lex_blocked"))
        return 0
    actual = delta
    if delta < 0:
        actual = -min(int(getattr(player, "lex_kela", 0) or 0), -delta)
        if actual == 0:
            return 0
    evt = LexKelaChangedEvent(
        run=run,
        player=player,
        delta=actual,
        reason=reason,
        source_card_id=source_card_id,
    )
    engine.event_bus.dispatch(evt)
    if evt.cancelled:
        return 0
    player.lex_kela = max(0, int(getattr(player, "lex_kela", 0) or 0) + actual)
    if actual < 0:
        run.node_data[run.turn_key("lex_kela_spent_this_turn", player)] = True
    if actual > 0 and reason != "turn_end":
        engine._log_event(run, get_locale_text("i18n_cards_ninja.lex_gain", amount=actual, current=player.lex_kela))
    elif actual < 0 and reason != "science":
        engine._log_event(run, get_locale_text("i18n_cards_ninja.lex_spend", amount=-actual, current=player.lex_kela))
    return actual


def consume_ninjutsu_lex(engine, run: GameRun, player, cost, source_card_id: str = "") -> tuple[bool, int]:
    if cost is None:
        return False, 0
    if cost == "X":
        cur = max(0, int(getattr(player, "lex_kela", 0) or 0))
        if cur <= 0:
            return False, 0
        change_lex_kela(engine, run, player, -cur, reason="ninjutsu", source_card_id=source_card_id)
        return True, cur
    need = int(cost)
    if need <= 0:
        return True, 0
    for b in list(player.buffs):
        if b.id in ("free_ninjutsu", "plasma_arrow") and b.stacks > 0:
            b.stacks -= 1
            if b.stacks <= 0:
                player.buffs.remove(b)
            return True, need
    cur = max(0, int(getattr(player, "lex_kela", 0) or 0))
    if cur < need:
        return False, 0
    change_lex_kela(engine, run, player, -need, reason="ninjutsu", source_card_id=source_card_id)
    return True, need


def add_random_food_to_hand(engine, run: GameRun, player, upgraded: bool = False, exclude: tuple[str, ...] = ()) -> str:
    from ..cards.base import ALL_CARDS
    pool = [fid for fid in NINJA_FOOD_TOKEN_IDS if ALL_CARDS[fid].name not in exclude]
    fid = random.choice(pool or list(NINJA_FOOD_TOKEN_IDS))
    max_hand = 9 if "mask_of_void" in player.relics else 12
    st = CardState(id=fid, upgraded=upgraded)
    if len(player.hand) < max_hand:
        player.hand.append(st)
    else:
        player.discard_pile.append(st)
    name = ALL_CARDS[st].name
    engine._log_event(run, get_locale_text("i18n_cards_ninja.food_gained", name=name))
    return name


def add_lan_blade_to_hand(engine, run: GameRun, player, upgraded: bool = False, to_draw: bool = False) -> None:
    st = CardState(id="ninja_lan_blade", upgraded=upgraded)
    if to_draw:
        player.draw_pile.append(st)
        random.shuffle(player.draw_pile)
        return
    max_hand = 9 if "mask_of_void" in player.relics else 12
    if len(player.hand) < max_hand:
        player.hand.append(st)
    else:
        player.discard_pile.append(st)
    engine._log_event(run, get_locale_text("i18n_cards_ninja.lan_blade_gained"))


def count_ninja_tag_in_deck(player, tag: str) -> int:
    from ..cards.base import ALL_CARDS
    total = 0
    for st in list(player.deck) + list(player.hand) + list(player.draw_pile) + list(player.discard_pile):
        card = ALL_CARDS.get(st)
        if has_ninja_tag(card, tag):
            total += 1
    return max(1, total)


def deal_random_enemy_hits(engine, run: GameRun, card: Card, dmg: int, hits: int, dtype: str = "physical") -> int:
    total = 0
    for _ in range(max(0, hits)):
        alive = [i for i, e in enumerate(run.enemies, 1) if e.hp > 0]
        if not alive:
            break
        idx = random.choice(alive)
        engine.combat_resolver.damage_target(run, f"e{idx}", dmg, source="p0", damage_type=dtype, card=card, is_attack=True)
        total += dmg
    return total


def deal_all_enemies(engine, run: GameRun, card: Card, dmg: int, dtype: str = "physical") -> None:
    for i, e in enumerate(run.enemies, 1):
        if e.hp > 0:
            engine.combat_resolver.damage_target(run, f"e{i}", dmg, source="p0", damage_type=dtype, card=card, is_attack=True)


def resolve_enemy_obj(run: GameRun, target: str | None):
    if target and target.startswith("e"):
        try:
            idx = int(target[1:]) - 1
            if 0 <= idx < len(run.enemies) and run.enemies[idx].hp > 0:
                return run.enemies[idx], f"e{idx + 1}"
        except ValueError:
            pass
    for i, e in enumerate(run.enemies, 1):
        if e.hp > 0:
            return e, f"e{i}"
    return None, ""


class NinjaCard(Card):
    def can_play_error(self, run: GameRun, target: str | None, engine) -> str | None:
        if getattr(self, "type", "") == "attack":
            if any(b.id == "we_peace" and b.stacks > 0 for b in run.player.buffs):
                return get_locale_text("i18n_cards_ninja.we_peace_blocked")
        return super().can_play_error(run, target, engine)

    def execute(self, run: GameRun, target: str | None, engine) -> str:
        return get_locale_text("i18n_cards_ninja.card_generic_res", name=self.name)
