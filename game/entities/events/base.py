from typing import List

class EventOption:
    registry = {}
    default_text = ""
    default_action = ""

    def __init__(self, text: str | None = None, action: str | None = None):
        self.text = text if text is not None else self.default_text
        self.action = action if action is not None else self.default_action

    def __init_subclass__(cls, action: str | None = None, text: str | None = None, **kwargs):
        super().__init_subclass__(**kwargs)
        if action:
            cls.default_action = action
            if text:
                cls.default_text = text
            cls.registry[action] = cls

    def execute(self, run, engine) -> str:
        res = self._run_effect(run, engine)
        return res

    def _run_effect(self, run, engine) -> str:
        return ""

class EventTemplate:
    def __init__(self, id: str, description: str, options: List[EventOption], min_floor: int | float = 1, max_floor: int | float = 2):
        self.id = id
        self.description = description
        self.options = options
        self.min_floor = min_floor
        self.max_floor = max_floor
