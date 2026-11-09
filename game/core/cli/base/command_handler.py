from typing import Generator

class CommandHandler:
    registry = {}
    registry_all = {}

    def __init_subclass__(cls, names: list[str] = None, allowed_states: list[str] = None, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.names = names or []
        cls.allowed_states = allowed_states if allowed_states is not None else ["menu", "town", "explore", "battle", "dialog"]
        if names:
            inst = cls()
            inst.names = cls.names
            inst.allowed_states = cls.allowed_states
            for name in names:
                cls.registry[name] = inst
                handlers = CommandHandler.registry_all.setdefault(name, [])
                handlers.append(inst)
                handlers.sort(key=lambda handler: len(handler.allowed_states))

    @classmethod
    def resolve(cls, name: str, state: str):
        handlers = cls.registry_all.get(name.lower())
        if not handlers:
            return None, False
        for handler in handlers:
            if state in handler.allowed_states:
                return handler, True
        return None, True

    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        raise NotImplementedError
