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
        """取消后续结算；订阅者应检查 ``cancelled`` 后停止写入。"""
        self.cancelled = True


class BattleStartEvent(GameEvent):
    """战斗开始事件，按存活玩家逐个派发。

    此时玩家初始资源、手牌与敌人都已构建完成，适合添加战斗初始 Buff、
    记录统计或触发开局被动。该事件没有取消语义。
    """

    run: GameRun


class BattleWinEvent(GameEvent):
    """战斗胜利事件，在胜利清理完成后派发。

    此时奖励、掉落与胜利清理基本完成，适合写统计或跨战继承；
    不提供取消或撤销胜利的语义。
    """

    run: GameRun


class BattleBeforeWinCleanupEvent(GameEvent):
    """战斗胜利清理前事件。

    此时玩家 Buff 尚未被清空，可读取最终层数并结算跨战延续；
    调用 ``cancel()`` 不会阻止胜利，只影响后续订阅者是否继续处理。
    """

    run: GameRun
    player: Any


class TurnStartEvent(GameEvent):
    """回合开始事件。

    ``is_player`` 区分玩家与敌方回合；玩家回合在资源初始化后、
    正式抽牌前派发。该事件没有取消语义。
    """

    run: GameRun
    is_player: bool


class TurnEndEvent(GameEvent):
    """回合结束事件。

    ``is_player`` 区分玩家与敌方回合；玩家回合此时尚未处理手牌去向与
    护符结算。该事件没有取消语义。
    """

    run: GameRun
    is_player: bool


class TurnEndAfterHandEvent(GameEvent):
    """玩家回合末手牌去向处理完毕后派发。

    护符的回合末效果、吟唱倒计时与谢幕曲在此结算；此时
    ``run.player.hand`` 已只保留本回合实际保留的卡牌。
    """

    run: GameRun
    player: Any


class TurnResourceInitEvent(GameEvent):
    """回合资源分配前事件，可修改行动点与附加行动点。

    订阅者应改写 ``actions`` 与 ``bonus_actions``；``is_battle_start``
    用于区分战斗初始资源与常规回合资源。没有取消语义。
    """

    run: GameRun
    player: Any
    actions: int
    bonus_actions: int
    is_battle_start: bool = False


class TurnDrawCalculateEvent(GameEvent):
    """回合抽牌数计算完成、实际抽牌前事件。

    可改写 ``draw_count``；``is_initial`` 表示战斗初始抽牌，
    遗物与消耗状态应据此区分初始/常规抽牌。没有取消语义。
    """

    run: GameRun
    player: Any
    draw_count: int
    is_initial: bool = False


class TurnStartAfterDrawEvent(GameEvent):
    """玩家回合初抽牌动作全部完成后事件。

    此时手牌已更新，适合触发“抽牌后”或回合初能力；``is_initial``
    区分战斗初始抽牌。没有取消语义。
    """

    run: GameRun
    player: Any
    is_initial: bool = False


class HandLimitCalculateEvent(GameEvent):
    """手牌上限查询事件。

    可改写 ``max_hand``；该值会用于抽牌、复制与手牌容量检查。
    没有取消语义。
    """

    run: GameRun
    player: Any
    max_hand: int


class BeforeCardDrawEvent(GameEvent):
    """单次抽牌执行前事件。

    可改写 ``count`` 等参数，或调用 ``cancel()`` 阻止本次抽牌；
    ``is_turn_start`` 区分回合初与效果抽牌。
    """

    run: GameRun
    player: Any
    count: int
    ignore_focus: bool = False
    is_turn_start: bool = False


class CardDrawnEvent(GameEvent):
    """每张牌离开抽牌堆时派发。

    事件携带 ``card_state`` 与可选的 ``card``；将 ``intercepted`` 置为
    True 表示该牌已由订阅者另行处理，核心不再按常规抽牌处理。
    ``depth`` 用于递归抽牌限制。
    """

    run: GameRun
    player: Any
    card_state: CardState
    card: Optional[Card]
    intercepted: bool = False
    depth: int = 0


class CardTurnEndResolveEvent(GameEvent):
    """玩家回合末裁决单张手牌去向。

    可改写 ``action``（discard/exhaust/hand/draw/remove）并设置
    ``handled``；未设置时核心按保留、虚无、取消等规则自行决定。
    """

    run: GameRun
    player: Any
    card_state: CardState
    card: Optional[Card]
    action: str = "discard"
    handled: bool = False


class CardCostCalculateEvent(GameEvent):
    """计算手牌有效费用时派发，供遗物/Buff/卡牌改写费用。

    可改写 ``cost_a``、``cost_ba``、``x_bonus_a`` 与 ``x_bonus_ba``；
    此时费用尚未扣除。没有取消语义。
    """

    run: GameRun
    player: Any
    card: Card
    card_state: CardState
    cost_a: int
    cost_ba: int
    x_bonus_a: int = 0
    x_bonus_ba: int = 0


class CardPlayCheckEvent(GameEvent):
    """出牌前置合法性校验事件。

    订阅者可调用 ``cancel()`` 并将原因写入 ``error_message``；核心在
    取消时直接返回该文案，不扣费、不执行卡牌。没有其他可改写字段。
    """

    run: GameRun
    player: Any
    card: Card
    card_state: CardState
    target: Optional[str]
    error_message: str = ""


class CardPostPlayRouteEvent(GameEvent):
    """卡牌结算完成后裁决去向：discard/exhaust/hand/draw/remove。

    ``destination`` 仅在 ``handled`` 为 True 时生效；``log_key`` 可覆盖
    默认去向日志的本地化键名，供虚空耗竭等来源保留专属文案。
    """

    run: GameRun
    player: Any
    card: Card
    card_state: CardState
    source: str
    destination: str = "discard"
    handled: bool = False
    log_key: str = ""


class CardPostPlayEvent(GameEvent):
    """卡牌完成去向、复制与标记结算后派发。

    此时卡牌已离开手牌，附魔的“打出后”效果应在此处处理；
    ``prev_alive_enemies`` 记录出牌前存活敌人数，供击杀条件附魔判断。
    """

    run: GameRun
    card: Card
    card_state: CardState
    target: Optional[str]
    prev_alive_enemies: int


class CardEffectResolvedEvent(GameEvent):
    """单张卡牌基础效果执行完毕、进入后续修饰前派发。

    该事件允许 Buff 在卡牌效果结束后追加额外执行，例如一分为十；
    订阅者应自行清除一次性标记，避免额外执行递归触发自身。
    """

    run: GameRun
    card: Card
    target: Optional[str]
    result: str = ""


class DamageRedirectEvent(GameEvent):
    """伤害结算最前端派发。

    可改写 ``source``、``target``、``amount``，或调用 ``cancel()`` 取消
    本次伤害；此时尚未计算减伤、护盾与生命扣减。``is_attack`` 与
    ``is_single_target`` 供订阅者判断伤害类型。
    """

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
    """玩家生命归零前派发。

    调用 ``cancel()`` 表示已抵挡本次致死伤害，核心会保留玩家；
    ``fatal_damage`` 为致死伤害值，``source`` 与 ``damage_type`` 供
    免死/复活效果判断。
    """

    run: GameRun
    player: Any
    source: str
    damage_type: str
    fatal_damage: int


class BuffAppliedEvent(GameEvent):
    """Buff 真正写入实体后派发。

    此时层数已生效；``is_new`` 区分新建与叠加，``added_stacks`` 为本次
    添加量。该事件不能撤销添加。
    """

    run: GameRun
    entity: Any
    buff_state: Any
    buff_id: str
    added_stacks: int
    is_new: bool = False


class ShieldDecayCalculateEvent(GameEvent):
    """护盾衰减前派发。

    可改写 ``decay_amount``，或调用 ``cancel()`` 取消本次衰减；
    调用方必须同时检查 ``cancelled`` 与最终衰减量。
    """

    run: GameRun
    entity: Any
    target: str
    current_shield: int
    decay_amount: int


class EnemyTargetSelectEvent(GameEvent):
    """敌方攻击目标分配时派发。

    可改写 ``candidates``、``taunt_uids`` 与 ``excluded_uids``；
    最终目标仍由分配器从过滤后的池中选出。没有取消语义。
    """

    run: GameRun
    enemy: EnemyState
    enemy_index: int
    candidates: List[str]
    taunt_uids: List[str]
    excluded_uids: List[str]


class EnemyRollIntentEvent(GameEvent):
    """敌人生成意图前派发。

    事件携带 ``enemy``，可修改意图列表、资源或描述；没有取消语义。
    """

    run: GameRun
    enemy: EnemyState


class MinionSkillUsedEvent(GameEvent):
    """随从技能成功结算后派发。

    事件携带 ``minion_state``、``grid``、``skill`` 与 ``target``；
    可追加连携、计数或日志，不能撤销技能结算。
    """

    run: GameRun
    player: Any
    minion_state: MinionState
    grid: str
    skill: Any
    target: Optional[str]


class LexKelaChangedEvent(GameEvent):
    """蕾克拉层数变化事件。

    可调用 ``cancel()`` 阻止变化，或读取 ``delta``、``reason`` 与
    ``source_card_id`` 做条件响应；正负变化都会派发。
    """

    run: GameRun
    player: Any
    delta: int
    reason: str = ""
    source_card_id: str = ""


class CardPlayEvent(GameEvent):
    """卡牌进入结算前派发。

    可改写 ``cost_a``、``cost_ba``、``target``，或调用 ``cancel()``
    阻止出牌；取消文案可写入 ``cancel_message``，留空时使用默认提示。
    """

    run: GameRun
    card: Card
    target: Optional[str]
    cost_a: int = 0
    cost_ba: int = 0
    cancel_message: str = ""


class CardPlayedEvent(GameEvent):
    """卡牌效果结算完成后派发。

    事件携带 ``card``、``target``、``feedback`` 与 ``is_extra``；可追加
    ``feedback``，但不能撤销已经完成的出牌。
    """

    run: GameRun
    card: Card
    target: Optional[str]
    feedback: str = ""
    is_extra: bool = False


class CardPlayedCountEvent(GameEvent):
    """本回合出牌计数变化事件。

    ``count`` 为更新后的计数；订阅者可读取但不应直接改写，计数最终值
    以核心写入 ``run.node_data`` 的值为准。
    """

    run: GameRun
    count: int


class CardExtraTriggerEvent(GameEvent):
    """额外出牌触发事件。

    事件携带 ``card`` 与 ``trigger_type``，用于让额外效果订阅者响应
    重放、回响、一分为十等来源；没有取消语义。
    """

    run: GameRun
    card: Card
    trigger_type: str


class DamageCalculateEvent(GameEvent):
    """基础伤害确定后、实际扣减前派发。

    可改写 ``modified_damage``；``base_damage`` 保留原始值，
    ``pierce_shield`` 供后续最终伤害阶段读取。没有取消语义，归零请改写
    ``modified_damage``。
    """

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
    """伤害已扣减生命或护盾后派发。

    ``amount`` 为实际伤害，``is_fatal`` 表示本次伤害导致目标离场；
    可反伤、叠层或写日志，不能撤销伤害。
    """

    run: GameRun
    source: str
    target: str
    amount: int
    is_fatal: bool = False
    damage_type: str = "effect"


class BeforeDamageApplyEvent(GameEvent):
    """最终伤害应用前派发。

    可改写 ``final_damage``，或设置 ``pierce_shield`` 穿透护盾；
    此时伤害计算已完成，不能再修改基础伤害。
    """

    run: GameRun
    card: Any
    source: str
    target: str
    damage_type: str
    final_damage: int
    pierce_shield: bool = False


class HealEvent(GameEvent):
    """治疗结算前派发。

    可改写 ``amount``，或调用 ``cancel()`` 取消治疗；玩家、随从与敌人
    的治疗都会经过此事件。
    """

    run: GameRun
    target: str
    amount: int


class HealCalculateEvent(GameEvent):
    """玩家治疗时计算生命上限修正。

    可改写 ``modified_max_hp``，用于限制本次治疗上限；仅玩家目标派发。
    """

    run: GameRun
    target: str
    base_max_hp: int
    modified_max_hp: int = 0


class CardDiscardEvent(GameEvent):
    """卡牌进入弃牌堆后派发。

    事件携带 ``card`` 与 ``source``；可处理弃牌计数或触发效果，
    不能阻止卡牌进入弃牌堆。
    """

    run: GameRun
    card: CardState
    source: str


class BuffGainEvent(GameEvent):
    """Buff 即将写入实体前派发。

    可改写 ``count`` / ``count2``，或调用 ``cancel()`` 阻止添加；
    ``buff_id``、``buff_name`` 与 ``desc`` 用于识别即将添加的状态。
    """

    run: GameRun
    entity: Any
    buff_id: str
    buff_name: str
    desc: str
    count: int = 1
    count2: Optional[int] = None


class MinionDeathEvent(GameEvent):
    """随从或敌人死亡后派发。

    事件携带 ``minion_id``、``grid``、``name`` 与 ``is_enemy``；
    可用于亡语、掉落或死亡计数，不能阻止死亡。
    """

    run: GameRun
    minion_id: str
    grid: str
    name: str
    is_enemy: bool


class EnemyBeforeDeathEvent(GameEvent):
    """敌人生命归零、移除前派发。

    调用 ``cancel()`` 可阻止本次死亡并保留敌人；适合 Boss 濒死或
    阶段转换。事件携带即将移除的 ``enemy``。
    """

    run: GameRun
    enemy: EnemyState


class MinionSummonEvent(GameEvent):
    """随从召唤成功事件。

    事件携带 ``minion_state`` 与 ``grid``；此时随从已写入战场，
    可追加 Buff、修改状态或写日志。
    """

    run: GameRun
    minion_state: MinionState
    grid: str


class CardExhaustEvent(GameEvent):
    """卡牌进入消耗堆后派发。

    事件携带 ``card`` 与 ``source``；可处理“消耗时”效果或计数，
    不能阻止消耗本身。
    """

    run: GameRun
    card: CardState
    source: str


class ShieldGainEvent(GameEvent):
    """护盾获取前派发。

    可改写 ``modified_amount``；非正值会阻止护盾写入。事件携带
    ``target`` 与 ``base_amount``，没有取消标志。
    """

    run: GameRun
    target: str
    base_amount: int
    modified_amount: int = 0


class ShieldDecayEvent(GameEvent):
    """护盾衰减实际生效后派发。

    事件携带 ``target`` 与 ``amount``，用于记录或触发“护盾流失时”
    效果；不能撤销已经完成的衰减。
    """

    run: GameRun
    target: str
    amount: int


class EnemySyncIntentsEvent(GameEvent):
    """敌人意图同步事件。

    事件携带 ``enemy``，可改写其意图列表、数值或描述；没有取消语义。
    """

    enemy: EnemyState


class RewardGenerateEvent(GameEvent):
    """战斗奖励生成事件。

    可向 ``items`` 追加奖励字典；该阶段没有取消语义，调用方会继续
    处理最终奖励列表。
    """

    run: GameRun
    items: List[dict]


class CardSelectInitEvent(GameEvent):
    """卡牌选择初始化事件。

    可改写 ``cards`` 候选，或调整 ``can_skip`` / ``upgraded``；
    该钩子早于玩家实际选择。
    """

    run: GameRun
    cards: List[str]
    can_skip: bool = True
    upgraded: bool = False


class CardObtainEvent(GameEvent):
    """玩家获得卡牌事件。

    事件携带新获得的 ``card_state``；适合处理获得时的附魔、计数或提示，
    不能撤销已经完成的获得。
    """

    run: GameRun
    card_state: Any


class CardVanishEvent(GameEvent):
    """卡牌被移除事件。

    事件携带被移除的 ``card_states``，用于清理引用或触发遗物效果；
    此时移除已经发生。
    """

    run: GameRun
    card_states: List[CardState]
