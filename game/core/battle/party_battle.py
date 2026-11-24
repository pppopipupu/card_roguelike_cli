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
    """按 ``party_order`` 返回当前战斗中的玩家对象。

    缺失于 ``run.players`` 的 UID 会被跳过；返回列表顺序稳定，供需要
    玩家槽位顺序的同步与结算逻辑使用。不修改状态。
    """
    return [run.players[uid] for uid in run.party_order if uid in run.players]


def party_slots(run, alive_only=False):
    """返回 ``(slot, uid, player)`` 槽位列表，槽位从 1 开始。

    ``alive_only=True`` 时排除倒地和生命归零的玩家；缺失玩家不会占位。
    该列表用于目标选择、复活与联机日志，不修改状态。
    """
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
    """把玩家 UID（可带随从格）转换为战斗目标引用。

    队友在 ``party_order`` 中时返回 ``aN`` / ``aNmG``；否则回退为
    ``p0`` / ``pG``。仅做引用映射，不验证玩家是否存活。
    """
    if uid in run.party_order:
        slot = run.party_order.index(uid) + 1
        return f"a{slot}" if grid is None else f"a{slot}m{grid}"
    return "p0" if grid is None else f"p{grid}"


def alive_uids(run):
    """返回当前存活玩家的 UID 列表，顺序同 ``party_order``。

    存活条件为未倒地且生命大于 0；与 ``party_slots(..., alive_only=True)``
    一致，供敌人目标池使用。
    """
    return [uid for _, uid, _ in party_slots(run, alive_only=True)]

def is_all_downed(run):
    """判断所有人类玩家是否均已倒地或生命归零。

    优先使用 ``run.all_human_uids()``，缺失时回退到全部玩家；没有玩家时
    返回 ``False``，避免空队伍被误判为团灭。
    """
    human_uids = run.all_human_uids() if hasattr(run, "all_human_uids") else list(run.players.keys())
    players = [run.players[uid] for uid in human_uids if uid in run.players]
    if not players:
        players = party_players(run)
    return bool(players) and all(player.downed or player.hp <= 0 for player in players)

def enemy_hp_multiplier(count):
    """按队伍人数返回敌人生命倍率。

    人数先按 ``COOP_DIFFICULTY_MAX_PLAYERS`` 截断；2 人使用固定
    ``COOP_HP_MULTIPLIERS[2]``，其余读取配置表，未知人数回退默认值。
    """
    capped = min(count, COOP_DIFFICULTY_MAX_PLAYERS)
    if capped <= 2:
        return COOP_HP_MULTIPLIERS[2]
    return COOP_HP_MULTIPLIERS.get(capped, COOP_HP_MULTIPLIER_DEFAULT)


def scale_party_enemies(run):
    """按队伍人数复制非 Boss 敌人并缩放生命与特定 Buff。

    Boss 仅复制一次以保持独立状态；普通敌人复制两份并追加字母后缀。
    最大生命、当前生命与护盾按倍率向上取整，带 ``coop_scale`` 的 Buff
    同步缩放。结果写回 ``run.enemies``，并记录 ``coop_hp_mult``。
    """
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
            if BUFF_CONFIG.get(buff.id, {}).get("coop_scale") and buff.stacks > 0:
                buff.stacks = max(1, ceil(buff.stacks * multiplier))
    run.enemies = expanded
    run.node_data["coop_hp_mult"] = multiplier


def assign_enemy_targets(run, engine=None):
    """为每个存活敌人分配本回合攻击目标并写入 ``enemy_targets``。

    AOE 意图记录为 ``"ALL"``；单体意图按存活玩家轮询，联机时派发
    ``EnemyTargetSelectEvent``，订阅者可改写 ``taunt_uids`` 与
    ``excluded_uids``。游标保存在 ``coop_aggro_cursor``，保证跨敌人公平。
    """
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
    """读取敌人已分配目标，失效时回退到首个存活玩家。

    AOE 意图返回 ``"ALL"``；记录目标仍存活且未倒地时优先使用；否则
    返回 ``fallback``。本函数不重新分配目标，也不派发事件。
    """
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
    """把玩家标记为倒地并清空其战斗资源。

    单人非联机战斗直接返回；多人战斗中清空手牌、随从、护符与能力，
    设置 ``turn_ready`` 并记录日志。若所有人类玩家均倒地，则写入
    ``coop_wipe``。
    """
    if not run:
        return
    humans = run.all_human_uids() if hasattr(run, "all_human_uids") else list(run.players.keys())
    if len(humans) <= 1:
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
    """在下一层开始时复活所有倒地玩家。

    复活后生命为 1、护盾清零，返回 ``{uid: 日志文本}``；尚未倒地的
    玩家不会出现在结果中。不派发事件。
    """
    revived = {}
    for player in party_players(run):
        if player.downed or player.hp <= 0:
            player.downed = False
            player.hp = 1
            player.shield = 0
            revived[run.uid_for(player)] = get_locale_text("i18n_explore_core.revive_log", player_name=player.name)
    return revived


def revive_downed_ally(save_manager, target_uid: str, run=None) -> str:
    """由队友救治指定倒地玩家并立即写回存档。

    未提供 ``run`` 时按 ``target_uid`` 读取存档；目标不存在或未倒地时
    返回空字符串。复活后生命为 1、护盾清零、动作恢复为 1A 1BA，
    并清空手牌、随从、护符与能力。
    """
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
