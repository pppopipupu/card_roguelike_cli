from typing import Optional
from ...data.entities.relic_data import RELIC_CONFIG
from .registry import RELIC_CLASS_REGISTRY

class RelicImpl:
    """遗物行为基类，由 ``RelicTriggerHandler`` 将战斗事件转发到生命周期钩子。

    新增遗物只需继承并通过 ``register_relic`` 注册，覆写所需钩子即可；
    严禁在核心战斗类中按遗物 ID 写特判。钩子统一接收 ``event/run/engine``，
    其中 ``run`` 是当前战斗或节点状态，``engine`` 提供结算与日志入口。
    """

    blocks_in_turn_draw = False

    def __init__(self, relic_id: str):
        self.relic_id = relic_id
        self.name = RELIC_CONFIG.get(relic_id, {}).get("name", relic_id)
        self.desc = RELIC_CONFIG.get(relic_id, {}).get("desc", "")
        self.rarity = RELIC_CONFIG.get(relic_id, {}).get("rarity", "common")

    def on_battle_start(self, run, engine):
        """战斗初始化完成后触发一次，按玩家逐个派发。

        此时敌人、手牌与初始资源已构建；可添加初始 Buff、修改资源或
        写日志。该钩子不接收事件，也没有取消语义。
        """
        pass

    def on_turn_start(self, event, run, engine):
        """在玩家或敌人回合开始时触发。

        ``event.is_player`` 区分行动方；遗物应据此判断是否为玩家回合。
        该阶段可修改资源、叠层或写日志，不提供取消回合的语义。
        """
        pass

    def on_turn_end(self, event, run, engine):
        """在回合结束时触发。

        此事件早于手牌去向与护符结算；可结算回合末效果、扣减计数或写日志。
        不能撤销已经开始的回合结束流程。
        """
        pass

    def on_card_play(self, event, run, engine):
        """在 ``CardPlayEvent`` 阶段修改本次出牌。

        可改写 ``cost_a``、``cost_ba``、``target``，或用 ``event.cancel()``
        阻止出牌；此时卡牌尚未扣费，也未执行效果。
        """
        pass

    def on_card_played(self, event, run, engine):
        """在 ``CardPlayedEvent`` 阶段响应卡牌结算完成。

        事件携带 ``card``、``target``、``feedback`` 与 ``is_extra``；
        可追加反馈、触发追击或计数，但不能撤销本次出牌。
        """
        pass

    def on_damage_calculate(self, event, run, engine):
        """在伤害计算阶段修改玩家作为来源的伤害。

        可改写 ``modified_damage``；事件携带 ``base_damage``、``card``、
        ``damage_type``、``target`` 与 ``is_attack``。
        """
        pass

    def on_damage_calculate_defend(self, event, run, engine):
        """在伤害计算阶段修改玩家作为目标的伤害。

        此时尚未扣减护盾与生命，可改写 ``modified_damage``；事件携带
        ``source``、``card``、``damage_type`` 与 ``is_attack``。
        """
        pass

    def on_damage_take(self, event, run, engine):
        """在 ``DamageTakeEvent`` 阶段响应实际伤害。

        护盾与生命已扣减，``amount`` 为实际伤害，``is_fatal`` 表示本次
        伤害导致目标离场；可反伤、叠层或写日志，不能撤销伤害。
        """
        pass

    def on_damage_take_defend(self, event, run, engine):
        """在 ``DamageTakeEvent`` 阶段处理玩家作为目标的受击后效果。

        与 ``on_damage_take`` 的区别是仅关注玩家受击；可用于受击反制、
        临时护盾或计数。此时伤害已生效。
        """
        pass

    def on_before_damage_apply(self, event, run, engine):
        """在最终伤害写入前调整伤害或穿透属性。

        可改写 ``final_damage`` 或设置 ``pierce_shield``；该阶段早于
        护盾与生命扣减，晚于伤害计算。
        """
        pass

    def on_shield_gain(self, event, run, engine):
        """在 ``ShieldGainEvent`` 阶段修改最终护盾量。

        订阅者应改写 ``event.modified_amount``；非正值会阻止护盾写入。
        事件携带 ``target`` 与 ``base_amount``。
        """
        pass

    def on_shield_decay(self, event, run, engine):
        """在护盾衰减实际生效后触发。

        事件携带 ``target`` 与 ``amount``，用于记录或触发“护盾流失时”
        效果；不能撤销已经完成的衰减。
        """
        pass

    def on_heal(self, event, run, engine):
        """在 ``HealEvent`` 阶段修改或取消治疗。

        可改写 ``event.amount``，或调用 ``event.cancel()``；事件携带
        ``target`` 与治疗量。
        """
        pass

    def on_heal_calculate(self, event, run, engine):
        """在玩家治疗计算生命上限时触发。

        可改写 ``event.modified_max_hp``，用于限制本次治疗上限；
        不处理实际治疗量。
        """
        pass

    def on_node_enter(self, run, engine):
        """玩家进入新地图节点时触发，不限于战斗节点。

        可检查节点类型、记录探索状态或处理进入时的被动效果；
        该钩子不接收事件，也没有取消语义。
        """
        pass

    def modify_initial_draw(self, run, draw_count: int, engine) -> int:
        """调整战斗初始抽牌数并返回新值。

        默认原样返回；``RelicTriggerHandler`` 在
        ``TurnDrawCalculateEvent(is_initial=True)`` 时调用。实现应保持纯计算，
        不要在此直接抽牌。
        """
        return draw_count

    def modify_turn_draw(self, run, draw_count: int, engine) -> int:
        """调整每回合常规抽牌数并返回新值。

        默认原样返回；仅在非初始的 ``TurnDrawCalculateEvent`` 中调用。
        实现应保持纯计算，不要在此直接抽牌。
        """
        return draw_count

    def on_draw_blocked(self, run, engine):
        """在遗物阻止本次抽牌后触发。

        当 ``blocks_in_turn_draw=True`` 且非回合初抽牌被拦截时调用，
        适合写提示日志或追加替代效果；此时本次抽牌已取消。
        """
        pass

    def on_battle_win(self, run, engine):
        """战斗胜利后触发。

        此时胜利清理已完成，可结算战后奖励、跨战继承或统计；
        不提供取消胜利的语义。
        """
        pass

    def on_minion_summon(self, event, run, engine):
        """在随从召唤成功后触发。

        事件携带 ``minion_state`` 与 ``grid``；可追加 Buff、修改随从
        或写日志。该阶段召唤已经完成。
        """
        pass

    def on_minion_death(self, event, run, engine):
        """在随从或敌人死亡后触发。

        事件携带 ``minion_id``、``grid``、``name`` 与 ``is_enemy``；
        适合处理亡语、掉落或死亡计数，不能阻止死亡。
        """
        pass

    def on_reward_generate(self, event, run, engine):
        """在战斗奖励生成时追加或修改奖励条目。

        事件携带 ``items``；可直接追加奖励字典。该阶段没有取消语义，
        调用方会继续处理最终列表。
        """
        pass

    def on_card_select_init(self, event, run, engine):
        """在卡牌选择初始化时调整候选。

        事件携带 ``cards``、``can_skip`` 与 ``upgraded``；可修改候选列表
        或跳过权限。该钩子早于玩家实际选择。
        """
        pass

    def on_card_obtain(self, event, run, engine):
        """在玩家获得卡牌后触发。

        事件携带 ``card_state``；适合处理获得时的附魔、计数或提示，
        不能撤销已经完成的获得。
        """
        pass

    def on_hand_limit_calculate(self, event, run, engine):
        """在手牌上限查询时修改上限。

        可改写 ``event.max_hand``；该值会用于抽牌与复制时的手牌容量检查。
        """
        pass

    def on_turn_draw_calculate(self, event, run, engine):
        """在回合抽牌数计算完成、实际抽牌前触发。

        可改写 ``event.draw_count``；``event.is_initial`` 区分战斗初始抽牌
        与常规回合抽牌。覆写此钩子后不会再调用 ``modify_*_draw`` 回退。
        """
        pass

    def on_before_card_draw(self, event, run, engine):
        """在单次抽牌前触发。

        可调用 ``event.cancel()`` 阻止本次抽牌，或修改 ``count`` 等参数。
        事件携带 ``is_turn_start``，用于区分回合初与效果抽牌。
        """
        pass

    def on_card_drawn(self, event, run, engine):
        """在每张牌离开抽牌堆后触发。

        事件携带 ``card_state``、``card``、``depth`` 与 ``intercepted``；
        将 ``intercepted`` 置为 True 表示该牌已由遗物另行处理。
        """
        pass

    def on_card_discard(self, event, run, engine):
        """在卡牌进入弃牌堆后触发。

        事件携带 ``card`` 与 ``source``；可处理弃牌计数、触发效果或写日志，
        不能阻止卡牌进入弃牌堆。
        """
        pass

    def on_buff_applied(self, event, run, engine):
        """在 Buff 已写入实体后触发。

        事件携带 ``buff_id``、``added_stacks`` 与 ``is_new``；适合处理
        “获得状态时”效果，不能取消本次添加。
        """
        pass

    def on_player_before_death(self, event, run, engine):
        """在玩家生命归零、死亡结算前触发。

        事件携带 ``source``、``damage_type`` 与 ``fatal_damage``；调用
        ``event.cancel()`` 表示遗物已抵挡本次致死伤害。
        """
        pass

    def on_minion_skill_used(self, event, run, engine):
        """在随从技能成功结算后触发。

        事件携带 ``minion_state``、``grid``、``skill`` 与 ``target``；
        可追加连携、计数或日志，不能撤销技能结算。
        """
        pass


def get_relic_impl(relic_id: str) -> Optional[RelicImpl]:
    """按遗物 ID 获取已注册的实现实例。

    未注册的遗物返回 ``None``，调用方应视为无被动；不会抛出异常。
    """
    cls = RELIC_CLASS_REGISTRY.get(relic_id)
    if cls:
        return cls(relic_id)
    return None

def get_relic_name(relic_id: str) -> str:
    """读取遗物展示名称，缺失时回退为 ID。"""
    return RELIC_CONFIG.get(relic_id, {}).get("name", relic_id)

def get_relic_desc(relic_id: str) -> str:
    """读取遗物描述，缺失时返回空字符串。"""
    return RELIC_CONFIG.get(relic_id, {}).get("desc", "")

def get_relic_rarity(relic_id: str) -> str:
    """读取遗物稀有度，缺失时回退为 ``common``。"""
    return RELIC_CONFIG.get(relic_id, {}).get("rarity", "common")

ALL_RELIC_IDS = list(RELIC_CONFIG.keys())
