import copy
import random
from typing import Optional

from ...data.entities.buffs.buff_data import BUFF_CONFIG
from ...data.text.locale_data import get_locale_text
from ...models.events import MinionDeathEvent
from ...models.state import BuffState, CardState, EnemyState, GameRun, PlayerState, ensure_card_state
from ..inventory.deck_service import DeckService

RAINIE_LOVE_ID = "rainie_love"
RAINIE_RAIN_WISH_ID = "rainie_lyric_rain_wish"
RAINIE_RAINBOW_ID = "rainie_lyric_rainbow"
RAINIE_LYRIC_IDS = (
    "rainie_lyric_listen",
    "rainie_lyric_clear",
    "rainie_lyric_breath",
    "rainie_lyric_rain_wish",
    "rainie_lyric_miss",
    "rainie_lyric_transparent",
    "rainie_lyric_rainie_love",
    "rainie_lyric_rain_outside",
    "rainie_lyric_accumulate",
    "rainie_lyric_memory",
    "rainie_lyric_secret",
    "rainie_lyric_continue",
    "rainie_lyric_believe",
    "rainie_lyric_rainbow",
)
LYRIC_NEXT = {
    1: "rainie_lyric_clear",
    2: "rainie_lyric_breath",
    3: "rainie_lyric_rain_wish",
    4: "rainie_lyric_miss",
    5: "rainie_lyric_transparent",
    6: "rainie_lyric_rainie_love",
    7: "rainie_lyric_rain_outside",
    8: "rainie_lyric_accumulate",
    9: "rainie_lyric_memory",
    10: "",
    11: "rainie_lyric_secret",
    12: "rainie_lyric_continue",
    13: "rainie_lyric_believe",
    14: "rainie_lyric_rainbow",
    15: "",
}
REGULAR_DEBUFF_EXCLUDE = {
    "sleep_rain",
    "breath_osmosis",
    "missing_ex",
    "transparent_wrap",
    "social_death",
    "dripping",
    "i_believe_you_will_die",
    "rainy_season",
}
AMPLIFY_EXCLUDE = {
    "rain_wish_replay_pending",
    "rain_wish_rain_pending",
    "rain_wish_retain_hand",
    "rain_wish_free_pending",
    "rainie_transparent",
    "rainie_cross_battle",
}


def lyric_progress_key(run: GameRun, player: PlayerState) -> str:
    return run.turn_key("rainie_lyric_progress", player)


def get_lyric_progress(run: GameRun, player: PlayerState) -> int:
    return int(run.node_data.get(lyric_progress_key(run, player), 0) or 0)


def set_lyric_progress(run: GameRun, player: PlayerState, value: int) -> None:
    run.node_data[lyric_progress_key(run, player)] = max(0, int(value or 0))


def reset_lyric_progress(run: GameRun, player: PlayerState) -> None:
    set_lyric_progress(run, player, 0)
    run.node_data.pop("rainie_social_boss_stunned", None)
    run.node_data.pop("rainie_prophecy_failed", None)
    for key in ("rainie_carried_a", "rainie_carried_ba"):
        run.node_data.pop(run.turn_key(key, player), None)


def player_ref(run: GameRun, uid: str) -> str:
    if not uid or uid not in run.players:
        return "p0"
    from .party_battle import party_target_ref
    return party_target_ref(run, uid)


def player_uid(run: GameRun, player: Optional[PlayerState] = None) -> str:
    target = player if player is not None else run.player
    return run.uid_for(target) if target is not None else run.user_id


def card_name(card_id: str) -> str:
    from ...entities.cards.base import ALL_CARDS
    card = ALL_CARDS.get(card_id)
    return card.name if card is not None else card_id


def buff_name(buff_id: str) -> str:
    return str(BUFF_CONFIG.get(buff_id, {}).get("name", buff_id))


def buff_desc(buff_id: str) -> str:
    return str(BUFF_CONFIG.get(buff_id, {}).get("desc", ""))


def add_buff(engine, entity, buff_id: str, count: int = 1, count2: Optional[int] = None) -> None:
    engine._add_buff_to(entity, buff_id, buff_name(buff_id), buff_desc(buff_id), count, count2)


def find_card(p: PlayerState, card_id: str, form: int = 0):
    piles = (
        ("hand", p.hand),
        ("draw", p.draw_pile),
        ("discard", p.discard_pile),
        ("exhaust", p.exhaust_pile),
    )
    for pile_name, pile in piles:
        for idx, raw in enumerate(pile):
            state = ensure_card_state(raw)
            if state.id != card_id:
                continue
            state_form = int(getattr(state, "lyric_form", 0) or 0)
            if form == 11 and state_form != 11:
                continue
            if form == 4 and state_form not in (0, 4):
                continue
            return pile_name, idx, state
    return None


def has_card(p: PlayerState, card_id: str, form: int = 0) -> bool:
    return find_card(p, card_id, form) is not None


def add_card_to_draw(p: PlayerState, card_id: str, form: int = 0) -> CardState:
    state = CardState(id=card_id, lyric_form=int(form or 0))
    p.draw_pile.append(state)
    return state


def add_next_lyric(run: GameRun, player: PlayerState, current_index: int, form: int = 0) -> str:
    next_index = 11 if form == 11 else int(current_index or 0)
    next_id = LYRIC_NEXT.get(next_index, "")
    if not next_id:
        return ""
    next_form = 4 if next_id == RAINIE_RAIN_WISH_ID else 0
    if has_card(player, next_id, next_form):
        return get_locale_text("i18n_rainie.next_lyric_exists", name=card_name(next_id))
    add_card_to_draw(player, next_id, next_form)
    return get_locale_text("i18n_rainie.next_lyric_added", name=card_name(next_id))


def _find_in_pile(pile: list, card_id: str):
    for idx, raw in enumerate(pile):
        state = ensure_card_state(raw)
        if state.id == card_id:
            return idx, state
    return None


def ensure_rain_wish_11(run: GameRun, player: PlayerState) -> str:
    hand_found = _find_in_pile(player.hand, RAINIE_RAIN_WISH_ID)
    if hand_found:
        hand_found[1].lyric_form = 11
        return get_locale_text("i18n_rainie.rain_wish_switched")
    for pile_name in ("exhaust", "draw", "discard"):
        pile = getattr(player, f"{pile_name}_pile")
        found = _find_in_pile(pile, RAINIE_RAIN_WISH_ID)
        if not found:
            continue
        idx, state = found
        pile.pop(idx)
        state.lyric_form = 11
        player.hand.append(state)
        return get_locale_text("i18n_rainie.rain_wish_retrieved")
    state = CardState(id=RAINIE_RAIN_WISH_ID, lyric_form=11, temp_ethereal=True)
    player.hand.append(state)
    return get_locale_text("i18n_rainie.rain_wish_created")


def copy_exhausted_non_lyric(run: GameRun, player: PlayerState) -> str:
    from ...entities.cards.base import ALL_CARDS
    eligible = []
    for state in player.exhaust_pile:
        state = ensure_card_state(state)
        card = ALL_CARDS.get(state)
        if card is not None and not getattr(card, "lyrics", False):
            eligible.append(state)
    if not eligible:
        return ""
    chosen = random.choice(eligible)
    clone = DeckService.clone_state(chosen)
    clone.temp_retain = True
    player.hand.append(clone)
    return get_locale_text("i18n_rainie.memory_copy", name=card_name(clone.id))


def damage_all(run: GameRun, engine, amount: int, damage_type: str = "cold", source: str = "p0", card=None, times: int = 1) -> None:
    for _ in range(max(0, int(times or 0))):
        for idx in range(len(run.enemies) - 1, -1, -1):
            if idx < len(run.enemies) and run.enemies[idx].hp > 0:
                engine._damage_target(run, f"e{idx + 1}", amount, source=source, damage_type=damage_type, card=card)


def living_enemies(run: GameRun) -> list[EnemyState]:
    return [enemy for enemy in run.enemies if enemy.hp > 0]


def is_boss_enemy(enemy: EnemyState) -> bool:
    from ...data.enemies.enemy_data import ENEMY_CONFIG
    from .reward_builder import base_enemy_name
    return ENEMY_CONFIG.get(base_enemy_name(enemy.name), {}).get("type") == "boss"


def negative_stacks(enemy: EnemyState) -> int:
    from ...entities.buffs.base import is_debuff
    return sum(max(0, int(b.stacks)) for b in enemy.buffs if is_debuff(b.id))


def is_regular_debuff(buff_id: str) -> bool:
    from ...entities.buffs.base import is_debuff
    return is_debuff(buff_id) and buff_id not in REGULAR_DEBUFF_EXCLUDE


def defeat_enemy(engine, run: GameRun, enemy: EnemyState) -> None:
    if enemy not in run.enemies:
        return
    idx = run.enemies.index(enemy)
    grid = f"e{idx + 1}"
    name = enemy.name
    enemy.hp = 0
    run.enemies.pop(idx)
    run.player.enemy_graveyard.append(name)
    engine.event_bus.dispatch(MinionDeathEvent(run, name, grid, name, True))


def clear_debuffs(player: PlayerState) -> int:
    from ...entities.buffs.base import is_debuff
    removed = [b for b in player.buffs if is_debuff(b.id)]
    player.buffs[:] = [b for b in player.buffs if not is_debuff(b.id)]
    return len(removed)


def strip_enemy_defenses(enemy: EnemyState) -> int:
    removed = [
        b for b in enemy.buffs
        if b.id.startswith("resist_") or b.id.startswith("immune_") or b.id == "intangible"
    ]
    enemy.buffs[:] = [b for b in enemy.buffs if b not in removed]
    return len(removed)


def steal_regular_debuffs(engine, run: GameRun, source: PlayerState, enemy: EnemyState) -> int:
    stolen = 0
    for buff in list(enemy.buffs):
        if not is_regular_debuff(buff.id) or buff.stacks <= 0:
            continue
        enemy.buffs.remove(buff)
        add_buff(engine, source, buff.id, buff.stacks)
        stolen += max(1, int(buff.stacks))
    return stolen


def grant_next_card_free(run: GameRun, player: PlayerState) -> None:
    key = run.turn_key("rainie_next_card_free", player)
    run.node_data[key] = True


def apply_legacy_at_battle_start(engine, run: GameRun, player: PlayerState) -> str:
    strength = int(getattr(player, "rainie_legacy_strength", 0) or 0)
    shield = int(getattr(player, "rainie_legacy_shield", 0) or 0)
    player.rainie_cross_battle = False
    if strength <= 0 and shield <= 0:
        return ""
    if strength > 0:
        add_buff(engine, player, "strength", min(15, strength))
    if shield > 0:
        player.shield = min(40, shield)
    player.rainie_legacy_strength = 0
    player.rainie_legacy_shield = 0
    return get_locale_text("i18n_rainie.legacy_applied", strength=min(15, strength), shield=min(40, shield))


def check_social_death(engine, run: GameRun, enemy: EnemyState, player: PlayerState) -> str:
    buff = next((b for b in enemy.buffs if b.id == "social_death"), None)
    if buff is None or enemy.hp <= 0:
        return ""
    threshold_hp = enemy.max_hp * 0.3
    negative = negative_stacks(enemy)
    if is_boss_enemy(enemy):
        if enemy.hp > threshold_hp and negative < 6:
            return ""
        stunned = run.node_data.setdefault("rainie_social_boss_stunned", [])
        marker = enemy.name
        if marker in stunned:
            return ""
        stunned.append(marker)
        enemy.shield = 0
        add_buff(engine, enemy, "stun", 1)
        engine._sync_enemy_intents(enemy)
        return get_locale_text("i18n_rainie.social_boss_stun", name=enemy.name)
    if enemy.hp > threshold_hp and negative < 6:
        return ""
    name = enemy.name
    defeat_enemy(engine, run, enemy)
    return get_locale_text("i18n_rainie.social_flee", name=name)


def snapshot_all_buffs(run: GameRun):
    entities = []
    for player in run.players.values():
        entities.append(player)
        entities.extend(player.minions.values())
    entities.extend(run.enemies)
    seen = set()
    snapshot = []
    for entity in entities:
        if id(entity) in seen:
            continue
        seen.add(id(entity))
        for buff in list(getattr(entity, "buffs", []) or []):
            if buff.stacks > 0 and buff.id not in AMPLIFY_EXCLUDE:
                snapshot.append((entity, copy.copy(buff), int(buff.stacks)))
    return snapshot


def amplify_all_buffs(run: GameRun, snapshot) -> int:
    from ...models.state import MinionState
    changed = 0
    for entity, old_buff, old_stacks in snapshot:
        if isinstance(entity, PlayerState):
            if entity not in run.players.values() or entity.hp <= 0:
                continue
        elif isinstance(entity, EnemyState):
            if entity not in run.enemies or entity.hp <= 0:
                continue
        elif isinstance(entity, MinionState):
            if not any(entity is m for p in run.players.values() for m in p.minions.values()):
                continue
        existing = next((b for b in getattr(entity, "buffs", []) or [] if b.id == old_buff.id), None)
        target_stacks = old_stacks + 1
        if existing is not None:
            existing.stacks = max(int(existing.stacks), target_stacks)
        else:
            restored = copy.copy(old_buff)
            restored.stacks = target_stacks
            entity.buffs.append(restored)
        changed += 1
    return changed
