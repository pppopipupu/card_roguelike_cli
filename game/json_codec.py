import json
import orjson


def dumps(data, indent: bool = False) -> bytes:
    option = orjson.OPT_NON_STR_KEYS
    if indent:
        option |= orjson.OPT_INDENT_2
    try:
        return orjson.dumps(data, option=option)
    except TypeError:
        return json.dumps(data, ensure_ascii=False, indent=2 if indent else None).encode("utf-8")


def loads(data) -> object:
    try:
        return orjson.loads(data)
    except orjson.JSONDecodeError:
        return json.loads(data)


def load(handle) -> object:
    return loads(handle.read())
