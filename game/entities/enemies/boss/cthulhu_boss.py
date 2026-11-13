from typing import List
import random
from ..base import EnemyTemplate, register_enemy
from ....core.inventory.deck_service import DeckService
from ....data.buff_data import BUFF_CONFIG
from ....data.enemy_data import ENEMY_CONFIG
from ....data.locale_data import get_locale_text

CTHULHU_NAME = "伟大的克苏鲁"
CTHULHU_MIST_NAME = "【迷雾】伟大的克苏鲁"
PUZZLE_CARD_ID = "special_rlyeh_astrolabe"
PUZZLE_DAMAGE = 6
PUZZLE_SHIELD = 12
PUZZLE_HP_COST = 8
PUZZLE_OBELISK_DAMAGE = 80
PUZZLE_OBELISK_GOLD = 25
ENTITY_A_INTENTS = ("call_of_rlyeh", "star_spawn_claw", "sunken_tsunami")
ENTITY_BA_INTENTS = ("cosmic_regen", "madness_pulse")
MIST_INTENTS = ("mist_condense_1", "mist_condense_2")


def _intent_entry(name: str, intent_id: str) -> dict:
    for entry in ENEMY_CONFIG.get(name, {}).get("intents", []):
        if entry.get("id") == intent_id:
            return entry
    return {}


def _intent_value(name: str, intent_id: str, fallback: int) -> int:
    entry = _intent_entry(name, intent_id)
    try:
        return int(entry.get("val", fallback))
    except (TypeError, ValueError):
        return fallback


def _intent_desc(intent_id: str, val: int) -> str:
    return get_locale_text(f"i18n_enemy_boss.cthulhu_intent_{intent_id}", val=val)


def _build_intent(name: str, intent_id: str, cost_a: int, cost_ba: int):
    from ....models.state import EnemyIntentState
    entry = _intent_entry(name, intent_id)
    val = _intent_value(name, intent_id, 0)
    desc = entry.get("desc") or _intent_desc(intent_id, val)
    return EnemyIntentState(type=intent_id, val=val, desc=desc, cost_a=cost_a, cost_ba=cost_ba)


def _alive_players(run) -> list:
    party = list(getattr(run, "players", {}).values())
    if party:
        return [p for p in party if p.hp > 0 and not p.downed]
    p = run.player
    return [p] if p.hp > 0 and not p.downed else []


def _target_ref(run, player) -> str:
    uid = run.uid_for(player)
    if uid in run.party_order:
        return f"a{run.party_order.index(uid) + 1}"
    return "p0"


def _cthulhu_enemy(run):
    for enemy in run.enemies:
        if enemy.name in (CTHULHU_NAME, CTHULHU_MIST_NAME):
            return enemy
    return None


def _enemy_ref(run, enemy):
    if enemy in run.enemies:
        return f"e{run.enemies.index(enemy) + 1}"
    return None


def _strip_buff(entity, buff_id: str):
    if not hasattr(entity, "buffs"):
        return
    entity.buffs[:] = [buff for buff in entity.buffs if buff.id != buff_id]


def _reduce_buff_stacks(entity, buff_id: str, amount: int):
    remaining = amount
    for buff in list(getattr(entity, "buffs", [])):
        if remaining <= 0:
            break
        if buff.id != buff_id:
            continue
        removed = min(buff.stacks, remaining)
        buff.stacks -= removed
        remaining -= removed
        if buff.stacks <= 0:
            entity.buffs.remove(buff)


def _clear_player_debuffs(player):
    from ...buffs import is_debuff
    player.buffs[:] = [buff for buff in player.buffs if not is_debuff(buff.id)]


def _damage_and_capture(run, engine, target: str, dmg: int, source: str, damage_type: str) -> str:
    logs = run.node_data.setdefault("battle_logs", [])
    before = len(logs)
    engine._damage_target(run, target, dmg, source=source, damage_type=damage_type)
    return logs.pop() if len(logs) > before else ""


def _battle_engine(engine):
    nested = getattr(engine, "battle_engine", None)
    if nested is not None and hasattr(nested, "_damage_target"):
        return nested
    return engine


def _mark_puzzle_advance(run, uid: str):
    advanced = run.node_data.setdefault("cthulhu_puzzle_advanced", {})
    advanced[uid] = True


@register_enemy(CTHULHU_NAME)
class BossCthulhuTemplate(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List['EnemyIntentState']:
        if enemy.name == CTHULHU_MIST_NAME:
            turns = run.node_data.get("cthulhu_mist_turns", 2)
            intent_id = "mist_condense_2" if turns <= 1 else "mist_condense_1"
            return [_build_intent(CTHULHU_MIST_NAME, intent_id, 1, 0)]
        intents_list = []
        for _ in range(2):
            intents_list.append(_build_intent(CTHULHU_NAME, random.choice(ENTITY_A_INTENTS), 1, 0))
        intents_list.append(_build_intent(CTHULHU_NAME, random.choice(ENTITY_BA_INTENTS), 0, 1))
        return intents_list

    def execute_intent(self, run, engine, enemy, intent, logs: List[str] = None):
        if logs is None:
            logs = []
            from ....models.state import EnemyIntentState
            intent = EnemyIntentState(
                type=getattr(enemy, "intent_type", ""),
                val=getattr(enemy, "intent_val", 0),
                desc=getattr(enemy, "intent_desc", ""),
                cost_a=1,
                cost_ba=0,
            )
        p = run.player
        strength = sum(buff.stacks for buff in enemy.buffs if buff.id == "strength")
        if intent.type in MIST_INTENTS:
            self._execute_mist_intent(run, engine, enemy, intent, logs)
        elif intent.type == "call_of_rlyeh":
            dmg_msg = _damage_and_capture(run, engine, "p0", intent.val + strength, f"enemy:{enemy.name}", "psychic")
            DeckService.add_card_to_draw(p, "curse_intangible_whisper")
            random.shuffle(p.draw_pile)
            logs.append(get_locale_text("i18n_enemy_boss.cthulhu_log_call_of_rlyeh", enemy_name=enemy.name, dmg_msg=dmg_msg))
        elif intent.type == "star_spawn_claw":
            dmg_msg = _damage_and_capture(run, engine, "p0", intent.val + strength, f"enemy:{enemy.name}", "bludgeoning")
            vuln_cfg = BUFF_CONFIG.get("minor_vulnerable_bludgeoning", {})
            engine._add_buff_to(p, "minor_vulnerable_bludgeoning", vuln_cfg.get("name", ""), vuln_cfg.get("desc", ""), 1)
            logs.append(get_locale_text("i18n_enemy_boss.cthulhu_log_star_spawn_claw", enemy_name=enemy.name, dmg_msg=dmg_msg))
        elif intent.type == "sunken_tsunami":
            entry = _intent_entry(CTHULHU_NAME, "sunken_tsunami")
            bonus = int(entry.get("shield_bonus_damage", 4))
            had_shield = p.shield > 0
            dmg_msg = _damage_and_capture(run, engine, "p0", intent.val + strength, f"enemy:{enemy.name}", "cold")
            logs.append(get_locale_text("i18n_enemy_boss.cthulhu_log_sunken_tsunami_player", enemy_name=enemy.name, dmg_msg=dmg_msg))
            if had_shield:
                _damage_and_capture(run, engine, "p0", bonus, f"enemy:{enemy.name}", "true")
                logs.append(get_locale_text("i18n_enemy_boss.cthulhu_log_sunken_tsunami_shield"))
            for grid, minion in list(p.minions.items()):
                minion_msg = _damage_and_capture(run, engine, f"p{grid}", intent.val + strength, f"enemy:{enemy.name}", "cold")
                logs.append(get_locale_text("i18n_enemy_boss.cthulhu_log_sunken_tsunami_minion", minion_name=minion.name, dmg_msg=minion_msg))
        elif intent.type == "cosmic_regen":
            entry = _intent_entry(CTHULHU_NAME, "cosmic_regen")
            heal = int(entry.get("heal", 8))
            target = _enemy_ref(run, enemy)
            if target:
                engine._gain_shield(run, target, intent.val)
                engine._heal_target(run, target, heal)
            logs.append(get_locale_text("i18n_enemy_boss.cthulhu_log_cosmic_regen", enemy_name=enemy.name, shield=intent.val, heal=heal))
        elif intent.type == "madness_pulse":
            engine._add_buff_to(p, "drain_ba", get_locale_text("i18n_enemy_boss.buff_drain_ba"), get_locale_text("i18n_enemy_boss.buff_drain_ba_desc"), 1)
            run.node_data["draw_penalty_next_turn"] = run.node_data.get("draw_penalty_next_turn", 0) + 1
            logs.append(get_locale_text("i18n_enemy_boss.cthulhu_log_madness_pulse", enemy_name=enemy.name))
        return "\n".join(logs)

    def _execute_mist_intent(self, run, engine, enemy, intent, logs: List[str]):
        p = run.player
        if intent.type == "mist_condense_1":
            dmg_msg = _damage_and_capture(run, engine, "p0", intent.val, f"enemy:{enemy.name}", "psychic")
            for grid in list(p.minions.keys()):
                _damage_and_capture(run, engine, f"p{grid}", intent.val, f"enemy:{enemy.name}", "psychic")
            engine._add_buff_to(enemy, "strength", get_locale_text("i18n_battle_core.buff_strength_name"), get_locale_text("i18n_battle_core.buff_strength_desc"), 1)
            logs.append(get_locale_text("i18n_enemy_boss.cthulhu_log_mist_condense_1", enemy_name=enemy.name, dmg_msg=dmg_msg))
            run.node_data["cthulhu_mist_turns"] = 1
        else:
            run.node_data["cthulhu_mist_turns"] = 0
            logs.append(get_locale_text("i18n_enemy_boss.cthulhu_log_mist_condense_2", enemy_name=enemy.name))
            self._revive_from_mist(run, engine, enemy, logs)

    def _revive_from_mist(self, run, engine, enemy, logs: List[str]):
        enemy.name = CTHULHU_NAME
        enemy.hp = enemy.max_hp
        enemy.max_actions = 2
        enemy.max_bonus_actions = 1
        enemy.actions = 2
        enemy.bonus_actions = 1
        _strip_buff(enemy, "cthulhu_mist_immune")
        count = run.node_data.get("cthulhu_revive_count", 0) + 1
        run.node_data["cthulhu_revive_count"] = count
        logs.append(get_locale_text("i18n_enemy_boss.cthulhu_log_revive", enemy_name=enemy.name))
        if count >= 2:
            run.node_data["cthulhu_puzzle_active"] = True
            run.node_data["cthulhu_seal_stage"] = 1
            logs.append(get_locale_text("i18n_enemy_boss.cthulhu_log_puzzle_start"))

    def on_enemy_before_death(self, run, enemy, event, engine):
        if enemy.name != CTHULHU_NAME:
            return
        if run.node_data.get("cthulhu_revive_count", 0) >= 2:
            return
        entity_name = enemy.name
        event.cancel()
        enemy.name = CTHULHU_MIST_NAME
        enemy.hp = 1
        enemy.shield = 0
        enemy.max_actions = 1
        enemy.max_bonus_actions = 0
        enemy.actions = 1
        enemy.bonus_actions = 0
        run.node_data["cthulhu_mist_turns"] = 2
        engine._add_buff_to(
            enemy,
            "cthulhu_mist_immune",
            get_locale_text("i18n_buffs.cthulhu_mist_immune_name"),
            get_locale_text("i18n_buffs.cthulhu_mist_immune_desc"),
            1,
        )
        enemy.intents.clear()
        enemy.intents.append(_build_intent(CTHULHU_MIST_NAME, "mist_condense_1", 1, 0))
        engine._sync_enemy_intents(enemy)
        engine._log_event(run, get_locale_text("i18n_enemy_boss.cthulhu_log_mist_transform", enemy_name=entity_name))

    def on_turn_start(self, event, enemy, engine):
        if not event.is_player:
            return
        run = event.run
        if not run.node_data.get("cthulhu_puzzle_active"):
            return
        run.node_data["cthulhu_puzzle_advanced"] = {}
        for player in _alive_players(run):
            if any(card.id == PUZZLE_CARD_ID for card in player.hand):
                continue
            from ....models.state import CardState
            player.hand.append(CardState(id=PUZZLE_CARD_ID))


register_enemy(CTHULHU_MIST_NAME)(BossCthulhuTemplate)


def resolve_cthulhu_puzzle(run, engine, option_idx: int, player=None) -> str:
    engine = _battle_engine(engine)
    acting = player if player is not None else run.player
    uid = run.uid_for(player) if player is not None else run.user_id
    advanced = run.node_data.setdefault("cthulhu_puzzle_advanced", {})
    if advanced.get(uid):
        return get_locale_text("i18n_cli_core.cthulhu_puzzle_advance_limit")
    try:
        option = int(option_idx)
    except (TypeError, ValueError):
        return get_locale_text("i18n_cli_core.err_cthulhu_puzzle_invalid")
    stage = run.node_data.get("cthulhu_seal_stage", 1)
    try:
        stage = int(stage)
    except (TypeError, ValueError):
        stage = 1
    max_option = 2 if stage >= 3 else 3
    if option < 1 or option > max_option:
        return get_locale_text("i18n_cli_core.err_cthulhu_puzzle_invalid")
    target = _target_ref(run, acting)
    if stage <= 1:
        if option == 1:
            engine._gain_shield(run, target, PUZZLE_SHIELD)
            acting.bonus_actions += 1
            boss = _cthulhu_enemy(run)
            if boss:
                _reduce_buff_stacks(boss, "strength", 2)
            run.node_data["cthulhu_seal_stage"] = 2
            _mark_puzzle_advance(run, uid)
            return get_locale_text("i18n_cli_core.cthulhu_puzzle_stage1_success")
        if option == 2:
            engine._damage_target(run, target, PUZZLE_DAMAGE, source="cthulhu_puzzle", damage_type="psychic")
            return get_locale_text("i18n_cli_core.cthulhu_puzzle_stage1_illusion")
        acting.hp = max(1, acting.hp - PUZZLE_HP_COST)
        run.node_data["cthulhu_seal_stage"] = 2
        _mark_puzzle_advance(run, uid)
        return get_locale_text("i18n_cli_core.cthulhu_puzzle_stage1_blood")
    if stage == 2:
        if option == 2:
            run.node_data["cthulhu_seal_stage"] = 3
            living = _alive_players(run)
            for player_state in living:
                _clear_player_debuffs(player_state)
                engine._draw_cards(player_state, 2, run)
            boss = _cthulhu_enemy(run)
            if boss:
                engine._add_buff_to(
                    boss,
                    "stars_misaligned",
                    get_locale_text("i18n_buffs.stars_misaligned_name"),
                    get_locale_text("i18n_buffs.stars_misaligned_desc"),
                    1,
                )
            _mark_puzzle_advance(run, uid)
            return get_locale_text("i18n_cli_core.cthulhu_puzzle_stage2_success")
        if option == 1:
            engine._damage_target(run, target, PUZZLE_DAMAGE, source="cthulhu_puzzle", damage_type="psychic")
            boss = _cthulhu_enemy(run)
            boss_target = _enemy_ref(run, boss) if boss else None
            if boss_target:
                engine._gain_shield(run, boss_target, 10)
            return get_locale_text("i18n_cli_core.cthulhu_puzzle_stage2_wrong")
        if acting.actions > 0:
            acting.actions -= 1
        else:
            acting.hp = max(1, acting.hp - PUZZLE_HP_COST)
        run.node_data["cthulhu_seal_stage"] = 3
        _mark_puzzle_advance(run, uid)
        return get_locale_text("i18n_cli_core.cthulhu_puzzle_stage2_overload")
    boss = _cthulhu_enemy(run)
    if option == 1:
        run.node_data["cthulhu_final_crash"] = True
        if boss:
            _strip_buff(boss, "cthulhu_mist_immune")
            boss.hp = 0
        _mark_puzzle_advance(run, uid)
        return get_locale_text("i18n_cli_core.cthulhu_puzzle_stage3_crash")
    boss_target = _enemy_ref(run, boss) if boss else None
    if boss_target:
        engine._damage_target(run, boss_target, PUZZLE_OBELISK_DAMAGE, source="cthulhu_puzzle", damage_type="true")
    for player_state in _alive_players(run):
        player_state.gold += PUZZLE_OBELISK_GOLD
    _mark_puzzle_advance(run, uid)
    return get_locale_text("i18n_cli_core.cthulhu_puzzle_stage3_obelisk")
