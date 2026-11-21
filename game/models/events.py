import msgspec
from typing import Any, List, Optional
from .state import GameRun, Card, MinionState, EnemyState, CardState

class GameEvent(msgspec.Struct, kw_only=True):
    cancelled: bool = False
    engine: Any = None

    def cancel(self):
        self.cancelled = True

class BattleStartEvent(GameEvent):
    run: GameRun

class BattleWinEvent(GameEvent):
    run: GameRun

class TurnStartEvent(GameEvent):
    run: GameRun
    is_player: bool

class TurnEndEvent(GameEvent):
    run: GameRun
    is_player: bool

class LexKelaChangedEvent(GameEvent):
    run: GameRun
    player: Any
    delta: int
    reason: str = ""
    source_card_id: str = ""

class CardPlayEvent(GameEvent):
    run: GameRun
    card: Card
    target: Optional[str]
    cost_a: int = 0
    cost_ba: int = 0

class CardPlayedEvent(GameEvent):
    run: GameRun
    card: Card
    target: Optional[str]
    feedback: str = ""
    is_extra: bool = False

class CardPlayedCountEvent(GameEvent):
    run: GameRun
    count: int

class CardExtraTriggerEvent(GameEvent):
    run: GameRun
    card: Card
    trigger_type: str

class DamageCalculateEvent(GameEvent):
    run: GameRun
    card: Optional[Card]
    source: str
    target: str
    damage_type: str
    base_damage: int
    modified_damage: int = 0
    is_attack: bool = False

class DamageTakeEvent(GameEvent):
    run: GameRun
    source: str
    target: str
    amount: int
    is_fatal: bool = False
    damage_type: str = "effect"

class BeforeDamageApplyEvent(GameEvent):
    run: GameRun
    card: Any
    source: str
    target: str
    damage_type: str
    final_damage: int

class HealEvent(GameEvent):
    run: GameRun
    target: str
    amount: int

class HealCalculateEvent(GameEvent):
    run: GameRun
    target: str
    base_max_hp: int
    modified_max_hp: int = 0

class CardDiscardEvent(GameEvent):
    run: GameRun
    card: CardState
    source: str

class MinionDeathEvent(GameEvent):
    run: GameRun
    minion_id: str
    grid: str
    name: str
    is_enemy: bool

class EnemyBeforeDeathEvent(GameEvent):
    run: GameRun
    enemy: EnemyState

class MinionSummonEvent(GameEvent):
    run: GameRun
    minion_state: MinionState
    grid: str

class CardExhaustEvent(GameEvent):
    run: GameRun
    card: CardState
    source: str

class ShieldGainEvent(GameEvent):
    run: GameRun
    target: str
    base_amount: int
    modified_amount: int = 0

class ShieldDecayEvent(GameEvent):
    run: GameRun
    target: str
    amount: int

class EnemySyncIntentsEvent(GameEvent):
    enemy: EnemyState

class RewardGenerateEvent(GameEvent):
    run: GameRun
    items: List[dict]

class CardSelectInitEvent(GameEvent):
    run: GameRun
    cards: List[str]
    can_skip: bool = True
    upgraded: bool = False

class CardObtainEvent(GameEvent):
    run: GameRun
    card_state: Any

class CardVanishEvent(GameEvent):
    run: GameRun
    card_states: List[CardState]
