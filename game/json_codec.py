import orjson


def dumps(data, indent: bool = False) -> bytes:
    option = orjson.OPT_NON_STR_KEYS
    if indent:
        option |= orjson.OPT_INDENT_2
    return orjson.dumps(data, option=option)


def loads(data) -> object:
    return orjson.loads(data)


def load(handle) -> object:
    return orjson.loads(handle.read())
