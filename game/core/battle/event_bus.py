from typing import Callable, Dict, List, Type
from ...models.events import GameEvent

PRIORITY_SYSTEM_PRE = 1000
PRIORITY_MODIFIER_ADD = 500
PRIORITY_MODIFIER_MUL = 200
PRIORITY_DEFAULT = 0
PRIORITY_OVERRIDE = -200
PRIORITY_INTERCEPT = -500
PRIORITY_POST = -1000


class EventBus:
    """原子战斗事件总线，负责按优先级同步分发事件。

    订阅时显式传入优先级，数值越大越先执行；同优先级保持注册顺序。
    ``dispatch`` 在事件第一次被 ``cancel`` 后停止调用后续订阅者，
    因此取消语义等价于“拦截剩余结算”。

    优先级约定使用模块常量：前置快照使用 ``PRIORITY_SYSTEM_PRE``，
    加法与乘法修正分别使用 ``PRIORITY_MODIFIER_ADD`` 与
    ``PRIORITY_MODIFIER_MUL``，封顶/免疫使用 ``PRIORITY_OVERRIDE``，
    致死拦截使用 ``PRIORITY_INTERCEPT``，收尾统计使用 ``PRIORITY_POST``。
    """

    def __init__(self):
        self._listeners: Dict[Type[GameEvent], List[tuple]] = {}

    def subscribe(self, event_cls: Type[GameEvent], handler: Callable, priority: int = PRIORITY_DEFAULT) -> None:
        """注册事件订阅者。

        参数：
            event_cls: 订阅的事件类型，子类事件同样会触发。
            handler: 接收事件实例的回调，额外位置参数由 dispatch 透传。
            priority: 触发优先级，数值越大越先执行。
        """
        if event_cls not in self._listeners:
            self._listeners[event_cls] = []
        self._listeners[event_cls].append((handler, priority))
        self._listeners[event_cls].sort(key=lambda x: x[1], reverse=True)

    def unsubscribe(self, event_cls: Type[GameEvent], handler: Callable) -> None:
        """移除指定事件类型上的回调，不存在时静默忽略。"""
        if event_cls in self._listeners:
            self._listeners[event_cls] = [item for item in self._listeners[event_cls] if item[0] != handler]

    def dispatch(self, event: GameEvent, *args, **kwargs) -> None:
        """按优先级同步分发事件。

        事件被任意订阅者 ``cancel()`` 后立即停止后续回调；
        事件对象本身携带 ``engine`` 字段，订阅者无需额外传入引擎。
        """
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
