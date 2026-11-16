import orjson
from typing import Any


def dumps(data, indent: bool = False) -> bytes:
    option = orjson.OPT_NON_STR_KEYS
    if indent:
        option |= orjson.OPT_INDENT_2
    return orjson.dumps(data, option=option)


def loads(data) -> Any:
    return orjson.loads(data)


def load(handle) -> Any:
    return orjson.loads(handle.read())
