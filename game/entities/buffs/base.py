from typing import List, Optional
import re
from .registry import register_buff, BUFF_CLASS_REGISTRY


def is_debuff(buff_id: str) -> bool:
    """判断 Buff 是否属于负面效果，统一读取 BUFF_CONFIG 元数据。"""
    clean_id = buff_id[:-1] if buff_id.endswith("+") else buff_id
    if clean_id.startswith("minor_vulnerable_") or clean_id.startswith("vulnerable_"):
        return True
    from ...data.entities.buffs.buff_data import BUFF_CONFIG
    cfg = BUFF_CONFIG.get(clean_id, {})
    return cfg.get("is_debuff", False)


def is_positive_buff(buff_id: str) -> bool:
    """判断 Buff 是否属于正面效果，负面与硬控白名单优先排除。"""
    clean_id = buff_id[:-1] if buff_id.endswith("+") else buff_id
    if is_debuff(clean_id):
        return False
    if clean_id in ("stun", "weak", "severe_weak", "electrified", "poison", "agony", "bleed", "void_weakness", "blind"):
        return False
    if "vulnerable" in clean_id:
        return False
    return True


def is_damage_event_from_entity(event, entity) -> bool:
    source = str(getattr(event, "source", "") or "")
    run = event.run
    if entity == run.player:
        if source in ("p0", "player") or source.startswith("player:"):
            return True
        if source == "effect":
            if run.node_data.get("current_acting_enemy_idx") is not None:
                return False
            return getattr(event, "target", "") != "p0"
        return False
    minions = getattr(run.player, "minions", None) or {}
    for grid, minion in minions.items():
        if minion is entity:
            return source == f"p{grid}"
    if entity in run.enemies:
        try:
            idx = run.enemies.index(entity)
            return source == f"e{idx + 1}"
        except ValueError:
            return False
    return False


class BuffImpl:
    """Buff 行为实现基类，所有具名 Buff 必须继承并通过 ``register_buff`` 注册。

    战斗事件总线在生命周期节点派发标准事件，``BuffTriggerHandler`` 会自动
    查找实体身上的 Buff 并调用同名钩子。新增 Buff 只需覆写需要的钩子，
    严禁在核心战斗类中编写针对具体 buff_id 的判断。

    统一钩子签名为 ``(event, buff_state, entity)``，可选第四个参数为引擎；
    引擎也可通过 ``event.engine`` 获取。可选类属性 ``hook_priorities`` 声明
    钩子执行顺序，数值越大越先执行，建议复用 ``event_bus`` 的 ``PRIORITY_*``。
    """

    auto_register = True
    hook_priorities: dict[str, int] = {}

    def __init__(self, stacks: int):
        self.stacks = stacks
        self.upgraded = False
        self.stacks2: Optional[int] = None

    def on_card_play(self, event, buff_state, entity):
        """在 ``CardPlayEvent`` 阶段修改本次出牌。

        此时卡牌尚未扣除费用、尚未进入结算；可改写 ``cost_a``、``cost_ba``
        与 ``target``，调用 ``event.cancel()`` 可阻止出牌。拥有者必须为
        ``event.run.player``；事件取消后后续钩子不再执行。
        """
        pass

    def on_card_played(self, event, buff_state, entity):
        """在 ``CardPlayedEvent`` 阶段处理卡牌效果结算后的反馈。

        事件携带 ``card``、``target``、``feedback`` 与 ``is_extra``；可追加
        ``feedback``，但此时卡牌已离开手牌，不能通过取消撤销本次出牌。
        ``entity`` 可能是玩家或敌人，需按拥有者判断是否响应。
        """
        pass

    def on_card_effect_resolved(self, event, buff_state, entity):
        """基础卡牌效果结束后触发，允许追加额外执行。

        事件为 ``CardEffectResolvedEvent``，携带本次 ``card``、``target``
        与基础效果反馈。订阅者应一次性执行并用自身标记防止递归。
        """
        pass

    def on_turn_start(self, event, buff_state, entity):
        """在 ``TurnStartEvent`` 阶段处理拥有者回合开始。

        ``event.is_player`` 区分玩家与敌方回合；Buff 应自行判断
        ``entity`` 是否就是当前行动方或当前受击方。该事件不提供取消语义。
        """
        pass

    def on_turn_end(self, event, buff_state, entity):
        """在 ``TurnEndEvent`` 阶段处理拥有者回合结束。

        此事件早于手牌去向与护符结算；可修改资源、层数或写日志，
        但不能取消已经开始的回合结束流程。
        """
        pass

    def on_damage_calculate(self, event, buff_state, entity):
        """在 ``DamageCalculateEvent`` 阶段修改拥有者作为来源的伤害。

        可改写 ``modified_damage``；事件携带 ``base_damage``、``card``、
        ``damage_type``、``target`` 与 ``is_attack``。拥有者通常是攻击方，
        防御方钩子应使用 ``on_damage_calculate_defend``。
        """
        pass

    def on_damage_calculate_defend(self, event, buff_state, entity):
        """在 ``DamageCalculateEvent`` 阶段修改拥有者作为目标的伤害。

        此时尚未扣减护盾与生命，可改写 ``modified_damage``；事件携带
        ``source``、``card``、``damage_type`` 与 ``is_attack``。
        """
        pass

    def on_damage_take_defend(self, event, buff_state, entity, engine=None):
        """在 ``DamageTakeEvent`` 阶段响应拥有者实际受到的伤害。

        此时护盾与生命已经扣减，``amount`` 为实际伤害，``is_fatal`` 表示
        本次伤害导致目标离场。可追加反伤、叠层或日志，不能撤销伤害。
        """
        pass

    def on_heal(self, event, buff_state, entity):
        """在 ``HealEvent`` 阶段修改拥有者相关的治疗量。

        事件携带 ``target`` 与 ``amount``；可改写 ``amount`` 或用
        ``event.cancel()`` 取消治疗。玩家、随从与敌人的治疗都会经过此事件。
        """
        pass

    def on_heal_calculate(self, event, buff_state, entity):
        """在 ``HealCalculateEvent`` 阶段修改玩家治疗的生命上限。

        仅玩家目标会派发；可改写 ``modified_max_hp``，用于限制本次治疗
        的上限。该事件不处理实际治疗量，也不提供取消语义。
        """
        pass

    def on_shield_gain(self, event, buff_state, entity):
        """在 ``ShieldGainEvent`` 阶段修改最终获得的护盾。

        事件携带 ``target``、``base_amount`` 与 ``modified_amount``；
        订阅者应改写 ``modified_amount``，返回 0 或负数会阻止护盾写入。
        """
        pass

    def on_enemy_sync_intents(self, event, buff_state, entity):
        """在敌人同步意图后调整其意图数据。

        事件携带 ``enemy``，可修改意图列表、数值或描述；该阶段不提供
        取消语义，改动会直接用于后续敌人行动显示与结算。
        """
        pass

    def on_damage_take_attack(self, event, buff_state, entity, engine=None):
        """在 ``DamageTakeEvent`` 阶段响应拥有者作为来源的伤害。

        此时伤害已经结算；可用于吸血、追击或触发条件效果。事件提供
        ``target``、``amount``、``is_fatal`` 与 ``damage_type``，不能撤销伤害。
        """
        pass

    def on_card_exhaust(self, event, buff_state, entity):
        """在卡牌进入消耗堆时触发。

        事件携带 ``card`` 与 ``source``；此时卡牌已写入消耗堆。适合处理
        “消耗时”效果，不能阻止消耗本身。
        """
        pass

    def on_buff_gain(self, event, buff_state, entity):
        """在 ``BuffGainEvent`` 阶段拦截或修改即将添加的 Buff。

        事件携带 ``buff_id``、``count``、``count2``；可改写层数，或调用
        ``event.cancel()`` 阻止添加。此钩子对即将添加的 Buff 生效，
        不是已存在 Buff 的叠加回调。
        """
        pass

    def on_unit_death(self, event, buff_state, entity):
        """在随从或敌人死亡后触发。

        事件携带 ``minion_id``、``grid``、``name`` 与 ``is_enemy``；
        此时死亡单位已从战场移除，适合处理亡语、层数翻倍或掉落。
        """
        pass

    def on_before_damage_apply(self, event, buff_state, entity, engine=None):
        """在最终伤害写入前调整伤害或穿透属性。

        事件携带 ``final_damage`` 与 ``pierce_shield``；可归零、封顶或
        声明穿透。此时 ``DamageCalculateEvent`` 已完成，不能再修改基础伤害。
        """
        pass

    def on_battle_before_win_cleanup(self, event, buff_state, entity):
        """在战斗胜利清理开始前触发。

        此时玩家 Buff 尚未被清空，可读取最终层数、结算跨战延续或写入
        胜利统计；该事件不提供取消语义。
        """
        pass

    def on_buff_applied(self, event, buff_state, entity):
        """在 Buff 已写入实体后触发。

        事件携带 ``buff_id``、``added_stacks`` 与 ``is_new``；此时层数已
        生效，适合处理“获得状态时”效果，不能再取消本次添加。
        """
        pass

    def on_shield_decay_calculate(self, event, buff_state, entity):
        """在护盾衰减计算时修改衰减量。

        事件携带 ``current_shield`` 与 ``decay_amount``；可改写衰减量，
        或调用 ``event.cancel()`` 取消本次衰减。调用方必须同时检查
        ``cancelled`` 与 ``decay_amount``。
        """
        pass

    def on_turn_start_after_draw(self, event, buff_state, entity):
        """在玩家回合初抽牌全部完成后触发。

        事件携带 ``player`` 与 ``is_initial``；适合处理抽牌后触发的能力。
        此时手牌已更新，但回合资源初始化与出牌阶段尚未完成。
        """
        pass

    def on_before_card_draw(self, event, buff_state, entity):
        """在单次抽牌执行前触发。

        事件携带 ``count``、``ignore_focus`` 与 ``is_turn_start``；可调用
        ``event.cancel()`` 阻止本次抽牌，或修改抽牌参数供后续订阅者使用。
        """
        pass

    def on_card_drawn(self, event, buff_state, entity):
        """在每张牌离开抽牌堆后触发。

        事件携带 ``card_state``、``card``、``depth`` 与 ``intercepted``；
        将 ``intercepted`` 置为 True 表示订阅者已接管该牌，后续抽牌逻辑
        应按拦截处理。
        """
        pass

    def on_card_cost_calculate(self, event, buff_state, entity):
        """在计算手牌有效费用时修改费用。

        事件携带 ``card``、``card_state``、``cost_a``、``cost_ba`` 与
        X 费用加成字段；订阅者应直接改写费用，最终值由出牌流程使用。
        """
        pass

    def on_card_play_check(self, event, buff_state, entity):
        """在出牌前置校验阶段阻止不合法出牌。

        可调用 ``event.cancel()`` 并写入 ``error_message``；此时尚未扣除
        费用。适合检查手牌构成、状态限制等全局条件。
        """
        pass

    def on_card_post_play_route(self, event, buff_state, entity):
        """在卡牌结算后裁决其去向。

        可改写 ``destination``（discard/exhaust/hand/draw/remove）并设置
        ``handled=True``；``log_key`` 可覆盖默认去向日志。未设置 handled
        时，核心按卡牌自身消耗/虚无等规则处理。
        """
        pass

    def on_damage_redirect(self, event, buff_state, entity):
        """在伤害结算最前端重定向目标、来源或数值。

        事件携带 ``source``、``target``、``amount``、``card`` 与
        ``is_attack``；可改写这些字段，或调用 ``event.cancel()`` 取消
        本次伤害。该钩子早于伤害计算与减伤。
        """
        pass

    def on_player_before_death(self, event, buff_state, entity):
        """在玩家生命归零、死亡结算前触发。

        事件携带 ``source``、``damage_type`` 与 ``fatal_damage``；调用
        ``event.cancel()`` 表示已抵挡本次致死伤害，调用方会保留玩家。
        """
        pass

    def on_enemy_target_select(self, event, buff_state, entity):
        """在敌人分配攻击目标时修改候选池。

        事件携带 ``candidates``、``taunt_uids`` 与 ``excluded_uids``；
        可追加嘲讽或排除目标。该事件不提供取消语义，最终仍会选出目标。
        """
        pass

    def on_enemy_roll_intent(self, event, buff_state, entity):
        """在敌人生成意图前调整意图资源。

        事件携带 ``enemy``；可修改其意图列表、行动点或描述。该钩子
        不提供取消语义，改动会用于本回合敌人行动。
        """
        pass

    def on_lex_kela_changed(self, event, buff_state, entity):
        """在蕾克拉层数变化事件中拦截或响应增减。

        事件携带 ``delta``、``reason`` 与 ``source_card_id``；调用
        ``event.cancel()`` 可阻止本次变化。正向与负向变化都会派发。
        """
        pass


def get_buff_impl(buff_id: str, stacks: int, stacks2: Optional[int] = None) -> Optional[BuffImpl]:
    """按 Buff ID 与层数构造实现实例。

    支持三种升级/别名形式：``+``、``_upgraded`` 与 ``_buff``。前两者会把
    ``upgraded`` 置为 True 后查找基础 ID；动态抗性/易伤类按前缀构造。
    找不到实现时返回 ``None``，调用方应视为无钩子而不是报错。
    """
    upgraded = False
    if isinstance(buff_id, str) and buff_id.endswith("_upgraded"):
        upgraded = True
        buff_id = buff_id[: -len("_upgraded")]
    elif isinstance(buff_id, str) and buff_id.endswith("+"):
        upgraded = True
        buff_id = buff_id[:-1]
    if buff_id.startswith("minor_vulnerable_"):
        from .debuffs import MinorVulnerableBuff
        dtype = buff_id[len("minor_vulnerable_"):]
        inst = MinorVulnerableBuff(stacks, dtype)
        inst.stacks2 = stacks2
        inst.upgraded = upgraded
        return inst
    elif buff_id.startswith("vulnerable_"):
        from .debuffs import VulnerableBuff
        dtype = buff_id[len("vulnerable_"):]
        inst = VulnerableBuff(stacks, dtype)
        inst.stacks2 = stacks2
        inst.upgraded = upgraded
        return inst
    elif buff_id.startswith("resist_"):
        from .buffs import ResistBuff
        dtype = buff_id[len("resist_"):]
        inst = ResistBuff(stacks, dtype)
        inst.stacks2 = stacks2
        inst.upgraded = upgraded
        return inst
    elif buff_id.startswith("immune_"):
        from .buffs import ImmuneBuff
        dtype = buff_id[len("immune_"):]
        inst = ImmuneBuff(stacks, dtype)
        inst.stacks2 = stacks2
        inst.upgraded = upgraded
        return inst
    cls = BUFF_CLASS_REGISTRY.get(buff_id)
    if not cls and isinstance(buff_id, str) and buff_id.endswith("_buff"):
        cls = BUFF_CLASS_REGISTRY.get(buff_id[:-5])
    if cls:
        inst = cls(stacks)
        inst.stacks2 = stacks2
        inst.upgraded = upgraded
        return inst
    return None
