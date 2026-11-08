COMMANDS: dict[str, str] = {}


def command(*names: str):
    def decorator(fn):
        for name in names:
            COMMANDS[name] = fn.__name__
        return fn

    return decorator
