from typing import Callable, Dict, List, Type
from ...models.events import GameEvent

class EventBus:
    def __init__(self):
        self._listeners: Dict[Type[GameEvent], List[tuple]] = {}

    def subscribe(self, event_cls: Type[GameEvent], handler: Callable, priority: int = 0):
        if event_cls not in self._listeners:
            self._listeners[event_cls] = []
        self._listeners[event_cls].append((handler, priority))
        self._listeners[event_cls].sort(key=lambda x: x[1], reverse=True)

    def unsubscribe(self, event_cls: Type[GameEvent], handler: Callable):
        if event_cls in self._listeners:
            self._listeners[event_cls] = [item for item in self._listeners[event_cls] if item[0] != handler]

    def dispatch(self, event: GameEvent, *args, **kwargs):
        event_cls = type(event)
        handlers = []
        for registered_cls, list_handlers in self._listeners.items():
            if issubclass(event_cls, registered_cls):
                handlers.extend(list_handlers)
        handlers.sort(key=lambda x: x[1], reverse=True)
        for handler, _ in handlers:
            if event.cancelled:
                break
            handler(event, *args, **kwargs)
