from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from contextvars import ContextVar
from enum import Enum
import hashlib

from ..data.locale_data import get_locale_text

current_user_id = ContextVar("current_user_id", default="")

def set_user_id(user_id: str):
    current_user_id.set(user_id)

def get_user_id() -> str:
    return current_user_id.get()

def public_player_id(user_id: str) -> str:
    if not user_id:
        return ""
    digest = hashlib.sha256(user_id.encode("utf-8")).hexdigest().upper()
    return "P" + digest[:12]

class DamageType(Enum):
    ACID = "acid"
    BLUDGEONING = "bludgeoning"
    COLD = "cold"
    FIRE = "fire"
    FORCE = "force"
    LIGHTNING = "lightning"
    NECROTIC = "necrotic"
    PIERCING = "piercing"
    POISON = "poison"
    PSYCHIC = "psychic"
    RADIANT = "radiant"
    SLASHING = "slashing"
    THUNDER = "thunder"
    TRUE = "true"

@dataclass
class UserStats:
    total_damage: int = 0
    total_kills: int = 0
    total_stages: int = 0
    rogue_mode: bool = False
    duel_mode: bool = False
    gp: int = 0
    unlocked_subclasses: List[str] = field(default_factory=list)
    selected_class: str = "法师"
    selected_subclass: str = ""
    killed_icerainboww: bool = False
    unlocked_gatekey: bool = False
    yog_sothoth_kill_count: int = 0
    yog_sothoth_challenge_count: int = 0
    reader_active: bool = False
    reader_page: int = 1
    reader_title: str = ""
    reader_items: List[str] = field(default_factory=list)
    reader_mode: str = "rogue"
    in_town: bool = False
    town_pos: str = "square"
    guaranteed_card: Optional[str] = None
    locked_cards: List[str] = field(default_factory=list)
    purchased_pool: List[str] = field(default_factory=list)
    defeated_town_npcs: List[str] = field(default_factory=list)
    town_inventory: List[str] = field(default_factory=list)
    town_flags: Dict[str, Any] = field(default_factory=dict)
    town_health_bonus: int = 0
    player_name: str = "玩家"
    name_customized: bool = False
    im_account: str = ""
    unlocked_new_cards: List[str] = field(default_factory=list)
    last_checkin_date: str = ""
    daily_blessing: str = ""
    checkin_pending_stamp: bool = False
    collection_stamps: Dict[str, int] = field(default_factory=dict)
    friends: List[str] = field(default_factory=list)
    friend_requests_in: List[Dict[str, Any]] = field(default_factory=list)
    friend_requests_out: List[str] = field(default_factory=list)
    active_lobby_id: str = ""
    active_coop_id: str = ""
    projection_enabled: bool = True
    projection_feed: List[Dict[str, Any]] = field(default_factory=list)
    log_history: List[Dict[str, Any]] = field(default_factory=list)
    team_log_history: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class CardState:
    id: str
    upgraded: bool = False
    gems: List[str] = field(default_factory=list)
    return_left: int = 0
    replay: int = 0
    fragile: int = 0
    no_copy: bool = False
    power_penalty: int = 0

    def __hash__(self):
        return hash((self.id, self.upgraded, tuple(self.gems), self.return_left, self.replay, self.fragile, self.no_copy, self.power_penalty))

    def __eq__(self, other):
        if isinstance(other, str):
            try:
                temp_state = _parse_old_cid(other)
                return (self.id == temp_state.id and 
                        self.upgraded == temp_state.upgraded and 
                        self.gems == temp_state.gems and 
                        self.return_left == temp_state.return_left and 
                        self.replay == temp_state.replay and 
                        self.fragile == temp_state.fragile and 
                        self.no_copy == temp_state.no_copy and
                        self.power_penalty == getattr(temp_state, "power_penalty", 0))
            except (ValueError, TypeError, KeyError):
                return False
        if not isinstance(other, CardState):
            return False
        return (self.id == other.id and 
                self.upgraded == other.upgraded and 
                self.gems == other.gems and 
                self.return_left == other.return_left and 
                self.replay == other.replay and 
                self.fragile == other.fragile and 
                self.no_copy == other.no_copy and
                self.power_penalty == other.power_penalty)

    def __lt__(self, other):
        if isinstance(other, str):
            try:
                temp_state = _parse_old_cid(other)
                return self < temp_state
            except (ValueError, TypeError, KeyError):
                return False
        if not isinstance(other, CardState):
            return NotImplemented
        if self.id != other.id:
            return self.id < other.id
        if self.upgraded != other.upgraded:
            return self.upgraded < other.upgraded
        if self.gems != other.gems:
            return tuple(self.gems) < tuple(other.gems)
        return (self.return_left, self.replay, self.fragile, self.no_copy) < (other.return_left, other.replay, other.fragile, other.no_copy)

def ensure_card_state(c) -> CardState:
    if isinstance(c, CardState):
        return c
    if isinstance(c, str):
        return _parse_old_cid(c)
    if isinstance(c, dict):
        return CardState(
            id=c.get("id", ""),
            upgraded=c.get("upgraded", False),
            gems=c.get("gems", []),
            return_left=c.get("return_left", 0),
            replay=c.get("replay", 0),
            fragile=c.get("fragile", 0),
            no_copy=c.get("no_copy", False),
            power_penalty=c.get("power_penalty", 0)
        )
    return c

def _parse_old_cid(cid: str) -> CardState:
    if not isinstance(cid, str):
        if hasattr(cid, "id"):
            return cid
        raise ValueError("cid must be str")
    parts = cid.split(":")
    first_part = parts[0]
    upgraded = False
    if first_part.endswith("+"):
        upgraded = True
        base_id = first_part[:-1]
    else:
        base_id = first_part
    gems = []
    return_left = 0
    replay = 0
    fragile = 0
    no_copy = False
    i = 1
    while i < len(parts):
        part = parts[i]
        if part == "gems" and i + 1 < len(parts):
            gems = parts[i+1].split(",") if parts[i+1] else []
            i += 2
        elif part == "replay" and i + 1 < len(parts):
            replay = int(parts[i+1])
            i += 2
        elif part == "fragile" and i + 1 < len(parts):
            fragile = int(parts[i+1])
            i += 2
        elif part == "return_left" and i + 1 < len(parts):
            return_left = int(parts[i+1])
            i += 2
        elif part == "no_copy" and i + 1 < len(parts):
            no_copy = (parts[i+1] == "1")
            i += 2
        else:
            i += 1
    return CardState(
        id=base_id,
        upgraded=upgraded,
        gems=gems,
        return_left=return_left,
        replay=replay,
        fragile=fragile,
        no_copy=no_copy
    )

@dataclass
class BuffState:
    id: str
    name: str
    stacks: int = 1
    stacks2: Optional[int] = None
    desc: str = ""
    source_uid: str = ""


@dataclass
class CardTag:
    name: str
    value: int = 0

    def execute(self, card: 'Card', run: 'GameRun', target: Optional[str], engine) -> Optional[str]:
        return None

    def handle_post_play(self, card: 'Card', run: 'GameRun', cid: str, source: str, engine) -> bool:
        return False

@dataclass
class Card:
    id: str
    name: str
    color: str
    type: str
    cost_a: int
    cost_ba: int
    countdown: int = 0
    desc: str = ""
    exhaust: bool = False
    rarity: str = "common"
    fleeting: bool = False
    agile: bool = False
    retain: bool = False
    innate: bool = False
    ethereal: bool = False
    unplayable: bool = False
    damage_type: str = "effect"
    upgraded: bool = False
    tags: List[CardTag] = field(default_factory=list)
    gems: List[str] = field(default_factory=list)
    instant_summon: bool = False
    instant_summon_thresholds: tuple = ()
    instant_summon_piles: tuple = ()

    def get_gem_slots_count(self) -> int:
        rarities = {
            "common": 1,
            "rare": 2,
            "epic": 3,
            "legendary": 4,
            "mythic": 5,
            "artifact": 8
        }
        return rarities.get(self.rarity, 1)

    @property
    def replay(self) -> int:
        return self.get_tag_value("replay")

    @replay.setter
    def replay(self, val: int):
        from ..entities.tags import ReplayTag
        if val > 0:
            self.add_tag(ReplayTag("replay", val))
        else:
            self.remove_tag("replay")

    @property
    def fragile(self) -> int:
        return self.get_tag_value("fragile")

    @fragile.setter
    def fragile(self, val: int):
        from ..entities.tags import FragileTag
        if val > 0:
            self.add_tag(FragileTag("fragile", val))
        else:
            self.remove_tag("fragile")

    def execute(self, run: 'GameRun', target: Optional[str] = None, engine = None) -> str:
        return ""

    def special_action(self, run: 'GameRun', target: Optional[str] = None) -> str:
        return get_locale_text("i18n_models.state.special_action", name=self.name)

    def add_tag(self, tag: CardTag):
        if not hasattr(self, "tags") or self.tags is None:
            self.tags = []
        self.tags = [t for t in self.tags if t.name != tag.name]
        self.tags.append(tag)

    def has_tag(self, name: str) -> bool:
        if not hasattr(self, "tags") or self.tags is None:
            return False
        return any(t.name == name for t in self.tags)

    def get_tag_value(self, name: str) -> int:
        if not hasattr(self, "tags") or self.tags is None:
            return 0
        for t in self.tags:
            if t.name == name:
                return t.value
        return 0

    def remove_tag(self, name: str):
        if hasattr(self, "tags") and self.tags is not None:
            self.tags = [t for t in self.tags if t.name != name]

    def execute_tags(self, run: 'GameRun', target: Optional[str], engine) -> Optional[str]:
        if not hasattr(self, "tags") or not self.tags:
            return None
        logs = []
        for tag in self.tags:
            res = tag.execute(self, run, target, engine)
            if res:
                logs.append(res)
        return "\n".join(logs) if logs else None

    def handle_post_play(self, run: 'GameRun', cid: str, source: str, engine) -> bool:
        if not hasattr(self, "tags") or not self.tags:
            return False
        for tag in self.tags:
            if tag.handle_post_play(self, run, cid, source, engine):
                return True
        return False


@dataclass
class MinionState:
    id: str
    name: str
    hp: int
    max_hp: int
    atk: int
    actions: int
    bonus_actions: int
    attack_actions: int = 1
    buffs: List[BuffState] = field(default_factory=list)

@dataclass
class AmuletState:
    id: str
    name: str
    countdown: int
    desc: str

@dataclass
class PlayerState:
    hp: int
    max_hp: int
    shield: int
    gold: int
    stage: int
    name: str = "玩家"
    deck: List[CardState] = field(default_factory=list)
    draw_pile: List[CardState] = field(default_factory=list)
    discard_pile: List[CardState] = field(default_factory=list)
    exhaust_pile: List[CardState] = field(default_factory=list)
    graveyard: List[CardState] = field(default_factory=list)
    minion_graveyard: List[str] = field(default_factory=list)
    enemy_graveyard: List[str] = field(default_factory=list)
    hand: List[CardState] = field(default_factory=list)
    actions: int = 1
    bonus_actions: int = 1
    minions: Dict[str, MinionState] = field(default_factory=dict)
    amulets: Dict[str, AmuletState] = field(default_factory=dict)
    abilities: List[str] = field(default_factory=list)
    fold_guide: bool = False
    buffs: List[BuffState] = field(default_factory=list)
    relics: List[str] = field(default_factory=list)
    subclass: str = ""
    selected_class: str = "法师"
    potions: List[str] = field(default_factory=list)
    daily_blessing_id: str = ""
    downed: bool = False

    def __post_init__(self):
        if not hasattr(self, "potions") or self.potions is None:
            self.potions = []
        self.deck = [self._ensure_card_state(c) for c in self.deck]
        self.draw_pile = [self._ensure_card_state(c) for c in self.draw_pile]
        self.discard_pile = [self._ensure_card_state(c) for c in self.discard_pile]
        self.exhaust_pile = [self._ensure_card_state(c) for c in self.exhaust_pile]
        self.graveyard = [self._ensure_card_state(c) for c in self.graveyard]
        self.hand = [self._ensure_card_state(c) for c in self.hand]

    def _ensure_card_state(self, c) -> CardState:
        if isinstance(c, CardState):
            return c
        if isinstance(c, str):
            return _parse_old_cid(c)
        if isinstance(c, dict):
            return CardState(
                id=c.get("id", ""),
                upgraded=c.get("upgraded", False),
                gems=c.get("gems", []),
                return_left=c.get("return_left", 0),
                replay=c.get("replay", 0),
                fragile=c.get("fragile", 0),
                no_copy=c.get("no_copy", False)
            )
        return c


@dataclass
class EnemyIntentState:
    type: str = ""
    val: int = 0
    desc: str = ""
    cost_a: int = 1
    cost_ba: int = 0
    cancelled: bool = False
    cancelled_desc: str = ""

@dataclass
class EnemyState:
    name: str
    hp: int
    max_hp: int
    shield: int
    actions: int = 1
    bonus_actions: int = 1
    buffs: List[BuffState] = field(default_factory=list)
    is_summon: bool = False
    max_actions: int = 1
    max_bonus_actions: int = 0
    intents: List[EnemyIntentState] = field(default_factory=list)
    intent_type: str = ""
    intent_val: int = 0
    intent_desc: str = ""
    intent_a_type: str = ""
    intent_a_val: int = 0
    intent_a_desc: str = ""
    intent_a2_type: str = ""
    intent_a2_val: int = 0
    intent_a2_desc: str = ""
    intent_ba_type: str = ""
    intent_ba_val: int = 0
    intent_ba_desc: str = ""
    intent_ba2_type: str = ""
    intent_ba2_val: int = 0
    intent_ba2_desc: str = ""

    def __post_init__(self):
        if not self.intents:
            if self.intent_type or self.intent_desc:
                self.intents.append(EnemyIntentState(
                    type=self.intent_type,
                    val=self.intent_val,
                    desc=self.intent_desc,
                    cost_a=1,
                    cost_ba=0
                ))
            else:
                if self.intent_a_desc:
                    self.intents.append(EnemyIntentState(
                        type=self.intent_a_type,
                        val=self.intent_a_val,
                        desc=self.intent_a_desc,
                        cost_a=1,
                        cost_ba=0
                    ))
                if self.intent_a2_desc:
                    self.intents.append(EnemyIntentState(
                        type=self.intent_a2_type,
                        val=self.intent_a2_val,
                        desc=self.intent_a2_desc,
                        cost_a=1,
                        cost_ba=0
                    ))
                if self.intent_ba_desc:
                    self.intents.append(EnemyIntentState(
                        type=self.intent_ba_type,
                        val=self.intent_ba_val,
                        desc=self.intent_ba_desc,
                        cost_a=0,
                        cost_ba=1
                    ))
                if self.intent_ba2_desc:
                    self.intents.append(EnemyIntentState(
                        type=self.intent_ba2_type,
                        val=self.intent_ba2_val,
                        desc=self.intent_ba2_desc,
                        cost_a=0,
                        cost_ba=1
                    ))

@dataclass
class GameRun:
    user_id: str
    node_type: str
    player: PlayerState
    enemies: List[EnemyState] = field(default_factory=list)
    node_data: Dict = field(default_factory=dict)
    map_data: Dict = field(default_factory=dict)
    player2: Optional[PlayerState] = None
    coop_id: str = ""
    leader_id: str = ""
    party_order: List[str] = field(default_factory=list)
    players: Dict[str, PlayerState] = field(default_factory=dict)

    def uid_for(self, player: PlayerState) -> str:
        for uid, candidate in self.players.items():
            if candidate is player:
                return uid
        return self.user_id

    def turn_key(self, name: str, player: PlayerState = None) -> str:
        if not self.coop_id:
            return name
        uid = self.uid_for(player) if player is not None else self.user_id
        return f"{name}:{uid}"

    def is_coop(self) -> bool:
        return bool(self.coop_id)

def check_and_replace_fireball(run: 'GameRun', card_id: str) -> str:
    import random
    if getattr(run.player, "subclass", "") == "塑能法师" and card_id == "fireball":
        if random.random() < 0.40:
            return "meteor_swarm"
    return card_id
