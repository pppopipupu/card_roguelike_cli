from typing import TYPE_CHECKING, Any
from .event_bus import EventBus

if TYPE_CHECKING:
    from ...engine import GameEngine
    from ..world.map_engine import MapEngine

class BaseBattleEngine:
    game_engine: "GameEngine"
    map_engine: "MapEngine"
    save_manager: Any
    card_player: Any
    enemy_controller: Any
    combat_resolver: Any
    exhaustion_observer: Any

    def __init__(self, save_manager):
        self.save_manager = save_manager
        self.event_bus = self._init_event_bus()
        orig_dispatch = self.event_bus.dispatch
        def decorated_dispatch(event, *args, **kwargs):
            event.engine = self
            return orig_dispatch(event, *args, **kwargs)
        self.event_bus.dispatch = decorated_dispatch

    def _init_event_bus(self):
        return EventBus()

    def _draw_cards(self, p, count, run=None, ignore_focus: bool = False, is_turn_start: bool = False):
        raise NotImplementedError

    def _add_buff_to(self, entity, buff_id: str, buff_name: str, desc: str, count: int = 1, count2=None):
        raise NotImplementedError

    def get_max_hand_size(self, run, player) -> int:
        raise NotImplementedError

    def _log_event(self, run, msg):
        raise NotImplementedError

    def is_battle_won(self, run) -> bool:
        raise NotImplementedError

    def _roll_enemy_intent(self, run):
        raise NotImplementedError
