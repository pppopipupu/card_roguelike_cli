from typing import Tuple

class ActionHandler:
    registry = {}

    def __init_subclass__(cls, actions: list[str] | None = None, **kwargs):
        super().__init_subclass__(**kwargs)
        if actions:
            for action in actions:
                cls.registry[action] = cls()

    def execute(self, router, user_id: str, run, parts: list[str]) -> Tuple[str, bool, bool]:
        raise NotImplementedError
