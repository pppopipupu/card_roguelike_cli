import msgspec
from typing import Any, List, Optional
from .state import GameRun, Card, MinionState, EnemyState, CardState


class GameEvent(msgspec.Struct, kw_only=True):
    """所有战斗原子事件的基类。

    ``cancelled`` 置位后事件总线停止剩余订阅者；``engine`` 由派发方注入，
    订阅者通过 ``event.engine`` 访问战斗引擎，避免钩子签名携带引擎参数。
    """

    cancelled: bool = False
    engine: Any = None

    def cancel(self):
        """取消后续结算，订阅者应检查 ``cancelled`` 后停止写入。"""
        self.cancelled = True


class BattleStartEvent(GameEvent):
    """战斗开始，双方已完成初始状态构建。"""

    run: GameRun


class BattleWinEvent(GameEvent):
    """战斗胜利，在胜利清理完成之后派发。"""

    run: GameRun


class BattleBeforeWinCleanupEvent(GameEvent):
    """战斗胜利清理前派发，此时玩家 Buff 尚未被清空。"""

    run: GameRun
    player: Any


class TurnStartEvent(GameEvent):
    """回合开始，``is_player`` 区分玩家与敌方回合。"""

    run: GameRun
    is_player: bool


class TurnEndEvent(GameEvent):
    """回合结束，``is_player`` 区分玩家与敌方回合。"""

    run: GameRun
    is_player: bool


class TurnResourceInitEvent(GameEvent):
    """回合资源分配前派发，可修改行动点与附加行动点。"""

    run: GameRun
    player: Any
    actions: int
    bonus_actions: int
    is_battle_start: bool = False


class TurnDrawCalculateEvent(GameEvent):
    """回合抽牌数计算完成、实际抽牌前派发。"""

    run: GameRun
    player: Any
    draw_count: int
    is_initial: bool = False


class TurnStartAfterDrawEvent(GameEvent):
    """玩家回合初抽牌动作全部完成后派发。"""

    run: GameRun
    player: Any
    is_initial: bool = False


class HandLimitCalculateEvent(GameEvent):
    """手牌上限查询时派发，可修改 ``max_hand``。"""

    run: GameRun
    player: Any
    max_hand: int


class BeforeCardDrawEvent(GameEvent):
    """单次抽牌执行前派发，``cancel()`` 阻止本次抽牌。"""

    run: GameRun
    player: Any
    count: int
    ignore_focus: bool = False
    is_turn_start: bool = False


class CardDrawnEvent(GameEvent):
    """每张牌离开抽牌堆时派发，``intercepted`` 表示已另行处理。"""

    run: GameRun
    player: Any
    card_state: CardState
    card: Optional[Card]
    intercepted: bool = False
    depth: int = 0


class CardTurnEndResolveEvent(GameEvent):
    """玩家回合末裁决单张手牌去向，可改写 ``action``。"""

    run: GameRun
    player: Any
    card_state: CardState
    card: Optional[Card]
    action: str = "discard"
    handled: bool = False


class CardCostCalculateEvent(GameEvent):
    """计算手牌有效费用时派发，供遗物/Buff/卡牌改写费用。"""

    run: GameRun
    player: Any
    card: Card
    card_state: CardState
    cost_a: int
    cost_ba: int
    x_bonus_a: int = 0
    x_bonus_ba: int = 0


class CardPlayCheckEvent(GameEvent):
    """出牌前置合法性校验，``cancel()`` 阻止出牌。"""

    run: GameRun
    player: Any
    card: Card
    card_state: CardState
    target: Optional[str]
    error_message: str = ""


class CardPostPlayRouteEvent(GameEvent):
    """卡牌结算完成后裁决去向：discard/exhaust/hand/draw/remove。"""

    run: GameRun
    player: Any
    card: Card
    card_state: CardState
    source: str
    destination: str = "discard"
    handled: bool = False


class DamageRedirectEvent(GameEvent):
    """伤害结算最前端派发，可重定向目标或来源。"""

    run: GameRun
    source: str
    target: str
    damage_type: str
    amount: int
    card: Optional[Card] = None
    is_attack: bool = False
    is_single_target: bool = False
    redirected: bool = False


class PlayerBeforeDeathEvent(GameEvent):
    """玩家生命归零前派发，``cancel()`` 表示已抵挡致死伤害。"""

    run: GameRun
    player: Any
    source: str
    damage_type: str
    fatal_damage: int


class BuffAppliedEvent(GameEvent):
    """Buff 真正写入实体后派发。"""

    run: GameRun
    entity: Any
    buff_state: Any
    buff_id: str
    added_stacks: int
    is_new: bool = False


class ShieldDecayCalculateEvent(GameEvent):
    """护盾衰减前派发，可修改衰减量或 ``cancel()``。"""

    run: GameRun
    entity: Any
    target: str
    current_shield: int
    decay_amount: int


class EnemyTargetSelectEvent(GameEvent):
    """敌方攻击目标分配时派发，可修改候选与排除集合。"""

    run: GameRun
    enemy: EnemyState
    enemy_index: int
    candidates: List[str]
    taunt_uids: List[str]
    excluded_uids: List[str]


class EnemyRollIntentEvent(GameEvent):
    """敌人生成意图前派发，用于调整意图资源。"""

    run: GameRun
    enemy: EnemyState


class MinionSkillUsedEvent(GameEvent):
    """随从技能成功结算后派发。"""

    run: GameRun
    player: Any
    minion_state: MinionState
    grid: str
    skill: Any
    target: Optional[str]


class LexKelaChangedEvent(GameEvent):
    """乐克拉层数变化。"""

    run: GameRun
    player: Any
    delta: int
    reason: str = ""
    source_card_id: str = ""


class CardPlayEvent(GameEvent):
    """卡牌进入结算前派发，可修改费用或取消出牌。"""

    run: GameRun
    card: Card
    target: Optional[str]
    cost_a: int = 0
    cost_ba: int = 0
    cancel_message: str = ""


class CardPlayedEvent(GameEvent):
    """卡牌效果结算完成后派发。"""

    run: GameRun
    card: Card
    target: Optional[str]
    feedback: str = ""
    is_extra: bool = False


class CardPlayedCountEvent(GameEvent):
    """本回合出牌计数变化。"""

    run: GameRun
    count: int


class CardExtraTriggerEvent(GameEvent):
    """额外出牌触发，供额外效果订阅者响应。"""

    run: GameRun
    card: Card
    trigger_type: str


class DamageCalculateEvent(GameEvent):
    """基础伤害确定后、应用伤害前派发，供加成与倍率修正。"""

    run: GameRun
    card: Optional[Card]
    source: str
    target: str
    damage_type: str
    base_damage: int
    modified_damage: int = 0
    is_attack: bool = False
    pierce_shield: bool = False


class DamageTakeEvent(GameEvent):
    """伤害已扣减生命或护盾后派发。"""

    run: GameRun
    source: str
    target: str
    amount: int
    is_fatal: bool = False
    damage_type: str = "effect"


class BeforeDamageApplyEvent(GameEvent):
    """最终伤害应用前派发，可归零、封顶或声明穿透护盾。"""

    run: GameRun
    card: Any
    source: str
    target: str
    damage_type: str
    final_damage: int
    pierce_shield: bool = False


class HealEvent(GameEvent):
    """治疗结算前派发，可修改或取消治疗量。"""

    run: GameRun
    target: str
    amount: int


class HealCalculateEvent(GameEvent):
    """治疗时计算生命上限修正。"""

    run: GameRun
    target: str
    base_max_hp: int
    modified_max_hp: int = 0


class CardDiscardEvent(GameEvent):
    """卡牌进入弃牌堆后派发。"""

    run: GameRun
    card: CardState
    source: str


class BuffGainEvent(GameEvent):
    """Buff 即将写入实体前派发，可取消或修改层数。"""

    run: GameRun
    entity: Any
    buff_id: str
    buff_name: str
    desc: str
    count: int = 1
    count2: Optional[int] = None


class MinionDeathEvent(GameEvent):
    """随从或敌人死亡。"""

    run: GameRun
    minion_id: str
    grid: str
    name: str
    is_enemy: bool


class EnemyBeforeDeathEvent(GameEvent):
    """敌人生命归零、移除前派发，可取消死亡。"""

    run: GameRun
    enemy: EnemyState


class MinionSummonEvent(GameEvent):
    """随从召唤成功。"""

    run: GameRun
    minion_state: MinionState
    grid: str


class CardExhaustEvent(GameEvent):
    """卡牌进入消耗堆。"""

    run: GameRun
    card: CardState
    source: str


class ShieldGainEvent(GameEvent):
    """护盾获取前派发，可修改最终护盾量。"""

    run: GameRun
    target: str
    base_amount: int
    modified_amount: int = 0


class ShieldDecayEvent(GameEvent):
    """护盾衰减结算。"""

    run: GameRun
    target: str
    amount: int


class EnemySyncIntentsEvent(GameEvent):
    """敌人意图同步，Buff 可在此改写意图。"""

    enemy: EnemyState


class RewardGenerateEvent(GameEvent):
    """战斗奖励生成，订阅者可追加奖励条目。"""

    run: GameRun
    items: List[dict]


class CardSelectInitEvent(GameEvent):
    """卡牌选择初始化。"""

    run: GameRun
    cards: List[str]
    can_skip: bool = True
    upgraded: bool = False


class CardObtainEvent(GameEvent):
    """玩家获得卡牌。"""

    run: GameRun
    card_state: Any


class CardVanishEvent(GameEvent):
    """卡牌被移除。"""

    run: GameRun
    card_states: List[CardState]
