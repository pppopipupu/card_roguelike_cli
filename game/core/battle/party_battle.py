import copy
from math import ceil

from ...data.progression.balance_config import (
    COOP_DIFFICULTY_MAX_PLAYERS,
    COOP_HP_MULTIPLIER_DEFAULT,
    COOP_HP_MULTIPLIERS,
)
from ...data.text.locale_data import get_locale_text
from ...data.enemies.enemy_data import AOE_INTENT_TYPES
from ...data.entities.buffs.buff_data import BUFF_CONFIG
from ...models.events import EnemyTargetSelectEvent
from .reward_builder import base_enemy_name




def party_players(run):
    """多人战斗公共辅助：处理玩家集合、目标与同步状态。"""
    return [run.players[uid] for uid in run.party_order if uid in run.players]


def party_slots(run, alive_only=False):
    """多人战斗公共辅助：处理玩家集合、目标与同步状态。"""
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
    """多人战斗公共辅助：处理玩家集合、目标与同步状态。"""
    if uid in run.party_order:
        slot = run.party_order.index(uid) + 1
        return f"a{slot}" if grid is None else f"a{slot}m{grid}"
    return "p0" if grid is None else f"p{grid}"


def alive_uids(run):
    """多人战斗公共辅助：处理玩家集合、目标与同步状态。"""
    return [uid for _, uid, _ in party_slots(run, alive_only=True)]

def is_all_downed(run):
    """多人战斗公共辅助：处理玩家集合、目标与同步状态。"""
    human_uids = run.all_human_uids() if hasattr(run, "all_human_uids") else list(run.players.keys())
    players = [run.players[uid] for uid in human_uids if uid in run.players]
    if not players:
        players = party_players(run)
    return bool(players) and all(player.downed or player.hp <= 0 for player in players)

def enemy_hp_multiplier(count):
    """多人战斗公共辅助：处理玩家集合、目标与同步状态。"""
    capped = min(count, COOP_DIFFICULTY_MAX_PLAYERS)
    if capped <= 2:
        return COOP_HP_MULTIPLIERS[2]
    return COOP_HP_MULTIPLIERS.get(capped, COOP_HP_MULTIPLIER_DEFAULT)


def scale_party_enemies(run):
    """多人战斗公共辅助：处理玩家集合、目标与同步状态。"""
    count = len(run.party_order)
    originals = list(run.enemies)
    if count < 2 or not originals:
        return
    from ...data.enemies.enemy_data import ENEMY_CONFIG
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
            if BUFF_CONFIG.get(buff.id, {}).get("coop_scale"):
                buff.stacks = max(1, ceil(buff.stacks * multiplier))
    run.enemies = expanded
    run.node_data["coop_hp_mult"] = multiplier


def assign_enemy_targets(run, engine=None):
    """为每个存活敌人分配攻击目标，联机时通过事件应用嘲讽与隐匿规则。"""
    alive = alive_uids(run)
    targets = {}
    cursor = int(run.node_data.get("coop_aggro_cursor", 0))
    for index, enemy in enumerate(run.enemies, 1):
        if enemy.hp <= 0:
            continue
        intents = list(getattr(enemy, "intents", []) or [])
        is_aoe = any(getattr(intent, "is_aoe", False) or intent.type in AOE_INTENT_TYPES for intent in intents)
        if is_aoe:
            targets[str(index)] = "ALL"
            continue
        if not alive:
            targets[str(index)] = ""
            continue
        taunt_uids = []
        excluded_uids = []
        if engine is not None:
            select_evt = EnemyTargetSelectEvent(run, enemy, index, list(alive), taunt_uids, excluded_uids)
            engine.event_bus.dispatch(select_evt)
            taunt_uids = list(select_evt.taunt_uids)
            excluded_uids = list(select_evt.excluded_uids)
        pool = taunt_uids or list(alive)
        filtered = [uid for uid in pool if uid not in excluded_uids]
        if filtered:
            pool = filtered
        chosen = pool[cursor % len(pool)]
        cursor += 1
        targets[str(index)] = chosen
    run.node_data["enemy_targets"] = targets
    run.node_data["coop_aggro_cursor"] = cursor


def pick_enemy_target(run, enemy_index, intent, fallback):
    """多人战斗公共辅助：处理玩家集合、目标与同步状态。"""
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
    """多人战斗公共辅助：处理玩家集合、目标与同步状态。"""
    if not run:
        return
    humans = run.all_human_uids() if hasattr(run, "all_human_uids") else list(run.players.keys())
    if len(humans) <= 1 and not getattr(run, "coop_id", ""):
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
    if is_all_downed(run):
        run.node_data["coop_wipe"] = True


def revive_downed_players(run):
    """多人战斗公共辅助：处理玩家集合、目标与同步状态。"""
    revived = {}
    for player in party_players(run):
        if player.downed or player.hp <= 0:
            player.downed = False
            player.hp = 1
            player.shield = 0
            revived[run.uid_for(player)] = get_locale_text("i18n_explore_core.revive_log", player_name=player.name)
    return revived


def revive_downed_ally(save_manager, target_uid: str, run=None) -> str:
    """多人战斗公共辅助：处理玩家集合、目标与同步状态。"""
    target_run = run
    if target_run is None or target_uid not in getattr(target_run, "players", {}):
        target_run = save_manager.load_save(target_uid)
    if target_run is None:
        return ""
    player = target_run.players.get(target_uid)
    if player is None or not player.downed:
        return ""
    player.downed = False
    player.hp = 1
    player.shield = 0
    player.hand.clear()
    player.minions.clear()
    player.amulets.clear()
    player.abilities.clear()
    player.actions = 1
    player.bonus_actions = 1
    save_manager.save_save(target_uid, target_run)
    return get_locale_text("i18n_explore_core.revive_by_ally", player_name=player.name)
