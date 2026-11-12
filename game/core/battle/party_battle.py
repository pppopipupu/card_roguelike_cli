import copy
from math import ceil

from ...data.balance_config import (
    COOP_DIFFICULTY_MAX_PLAYERS,
    COOP_HP_MULTIPLIER_DEFAULT,
    COOP_HP_MULTIPLIERS,
)
from ...data.locale_data import get_locale_text
from ..reward_builder import base_enemy_name


AOE_INTENT_TYPES = {
    "attack_all",
    "aoe_attack",
    "all_attack",
    "aoe_damage",
    "hellfire",
    "electrodynamics",
    "soul_daggers",
    "focus_bloom",
    "sunken_tsunami",
    "mist_condense_1",
    "tail_sweep",
    "inferno_breath",
}


def party_players(run):
    return [run.players[uid] for uid in run.party_order if uid in run.players]


def party_slots(run, alive_only=False):
    slots = []
    for slot, uid in enumerate(run.party_order, 1):
        player = run.players.get(uid)
        if player is None:
            continue
        if alive_only and (player.hp <= 0 or player.downed):
            continue
        slots.append((slot, uid, player))
    return slots


def party_target_ref(run, uid, grid=None):
    if uid in run.party_order:
        slot = run.party_order.index(uid) + 1
        return f"a{slot}" if grid is None else f"a{slot}m{grid}"
    return "p0" if grid is None else f"p{grid}"


def alive_uids(run):
    return [uid for _, uid, _ in party_slots(run, alive_only=True)]

def is_all_downed(run):
    human_uids = run.human_uids() if hasattr(run, "human_uids") else list(run.players.keys())
    players = [run.players[uid] for uid in human_uids if uid in run.players]
    if not players:
        players = party_players(run)
    return bool(players) and all(player.downed or player.hp <= 0 for player in players)

def enemy_hp_multiplier(count):
    capped = min(count, COOP_DIFFICULTY_MAX_PLAYERS)
    if capped <= 2:
        return COOP_HP_MULTIPLIERS[2]
    return COOP_HP_MULTIPLIERS.get(capped, COOP_HP_MULTIPLIER_DEFAULT)


def scale_party_enemies(run):
    count = len(run.party_order)
    originals = list(run.enemies)
    if count < 2 or not originals:
        return
    from ...data.enemy_data import ENEMY_CONFIG
    multiplier = enemy_hp_multiplier(count)
    expanded = []
    sequence = 0
    for enemy in originals:
        base_name = base_enemy_name(enemy.name)
        if ENEMY_CONFIG.get(base_name, {}).get("type") == "boss":
            clone = copy.deepcopy(enemy)
            clone.name = base_name
            expanded.append(clone)
            continue
        for _ in range(2):
            clone = copy.deepcopy(enemy)
            clone.name = f"{base_name} {chr(65 + sequence)}" if sequence < 26 else f"{base_name} {sequence + 1}"
            expanded.append(clone)
            sequence += 1
    for enemy in expanded:
        enemy.max_hp = max(1, ceil(enemy.max_hp * multiplier))
        enemy.hp = max(1, ceil(enemy.hp * multiplier))
        enemy.shield = max(0, ceil(enemy.shield * multiplier))
        for buff in enemy.buffs:
            if buff.id in ("unyielding", "strength"):
                buff.stacks = max(1, ceil(buff.stacks * multiplier))
    run.enemies = expanded
    run.node_data["coop_hp_mult"] = multiplier


def assign_enemy_targets(run):
    alive = alive_uids(run)
    targets = {}
    cursor = int(run.node_data.get("coop_aggro_cursor", 0))
    for index, enemy in enumerate(run.enemies, 1):
        if enemy.hp <= 0:
            continue
        intents = list(getattr(enemy, "intents", []) or [])
        is_aoe = any(intent.type in AOE_INTENT_TYPES for intent in intents)
        if is_aoe:
            targets[str(index)] = "ALL"
            continue
        if not alive:
            targets[str(index)] = ""
            continue
        taunt_uids = [
            uid
            for uid in alive
            if any(buff.id == "coop_aegis" for buff in run.players[uid].buffs)
        ]
        pool = taunt_uids or alive
        chosen = pool[cursor % len(pool)]
        cursor += 1
        targets[str(index)] = chosen
    run.node_data["enemy_targets"] = targets
    run.node_data["coop_aggro_cursor"] = cursor


def pick_enemy_target(run, enemy_index, intent, fallback):
    targets = run.node_data.get("enemy_targets", {})
    marked = targets.get(str(enemy_index))
    if intent.type in AOE_INTENT_TYPES:
        return "ALL"
    if marked and marked in run.players:
        player = run.players[marked]
        if player.hp > 0 and not player.downed:
            return marked
    alive = alive_uids(run)
    return alive[0] if alive else fallback


def mark_downed(battle_engine, run, player):
    if not run or run.player_count() <= 1:
        return
    uid = run.uid_for(player)
    if not uid or player.downed:
        return
    player.downed = True
    player.hp = 0
    player.shield = 0
    player.hand.clear()
    player.minions.clear()
    player.amulets.clear()
    player.abilities.clear()
    ready = run.node_data.setdefault("turn_ready", {})
    ready[uid] = True
    battle_engine._log_event(run, get_locale_text("i18n_explore_core.downed_log", player_name=player.name))
    if not alive_uids(run):
        run.node_data["coop_wipe"] = True


def revive_downed_players(run):
    revived = {}
    for player in party_players(run):
        if player.downed or player.hp <= 0:
            player.downed = False
            player.hp = 1
            player.shield = 0
            revived[run.uid_for(player)] = get_locale_text("i18n_explore_core.revive_log", player_name=player.name)
    return revived
