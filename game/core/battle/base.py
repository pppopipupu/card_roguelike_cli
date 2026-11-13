from .event_bus import EventBus

class BaseBattleEngine:
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
