from dataclasses import dataclass, field
from typing import Any, List, Optional
from .state import GameRun, Card, MinionState, EnemyState

@dataclass
class GameEvent:
    def __post_init__(self):
        self.cancelled = False

    def cancel(self):
        self.cancelled = True

@dataclass
class BattleStartEvent(GameEvent):
    run: GameRun

@dataclass
class BattleWinEvent(GameEvent):
    run: GameRun

@dataclass
class TurnStartEvent(GameEvent):
    run: GameRun
    is_player: bool

@dataclass
class TurnEndEvent(GameEvent):
    run: GameRun
    is_player: bool

@dataclass
class CardPlayEvent(GameEvent):
    run: GameRun
    card: Card
    target: Optional[str]
    cost_a: int = 0
    cost_ba: int = 0

@dataclass
class CardPlayedEvent(GameEvent):
    run: GameRun
    card: Card
    target: Optional[str]
    feedback: str = ""
    is_extra: bool = False

@dataclass
class CardPlayedCountEvent(GameEvent):
    run: GameRun
    count: int

@dataclass
class DamageCalculateEvent(GameEvent):
    run: GameRun
    card: Optional[Card]
    source: str
    target: str
    damage_type: str
    base_damage: int
    modified_damage: int = 0
    is_attack: bool = False

@dataclass
class DamageTakeEvent(GameEvent):
    run: GameRun
    source: str
    target: str
    amount: int
    is_fatal: bool = False
    damage_type: str = "effect"

@dataclass
class BeforeDamageApplyEvent(GameEvent):
    run: GameRun
    card: Any
    source: str
    target: str
    damage_type: str
    final_damage: int

@dataclass
class HealEvent(GameEvent):
    run: GameRun
    target: str
    amount: int

@dataclass
class HealCalculateEvent(GameEvent):
    run: GameRun
    target: str
    base_max_hp: int
    modified_max_hp: int = 0



@dataclass
class CardDiscardEvent(GameEvent):
    run: GameRun
    card_id: str
    source: str

@dataclass
class MinionDeathEvent(GameEvent):
    run: GameRun
    minion_id: str
    grid: str
    name: str
    is_enemy: bool

@dataclass
class EnemyBeforeDeathEvent(GameEvent):
    run: GameRun
    enemy: EnemyState


@dataclass
class MinionSummonEvent(GameEvent):
    run: GameRun
    minion_state: MinionState
    grid: str

@dataclass
class CardExhaustEvent(GameEvent):
    run: GameRun
    card_id: str
    source: str

@dataclass
class ShieldGainEvent(GameEvent):
    run: GameRun
    target: str
    base_amount: int
    modified_amount: int = 0

@dataclass
class ShieldDecayEvent(GameEvent):
    run: GameRun
    target: str
    amount: int

@dataclass
class EnemySyncIntentsEvent(GameEvent):
    enemy: EnemyState

@dataclass
class RewardGenerateEvent(GameEvent):
    run: GameRun
    items: List[dict]

@dataclass
class CardSelectInitEvent(GameEvent):
    run: GameRun
    cards: List[str]
    can_skip: bool = True
    upgraded: bool = False

@dataclass
class CardObtainEvent(GameEvent):
    run: GameRun
    card_state: Any

