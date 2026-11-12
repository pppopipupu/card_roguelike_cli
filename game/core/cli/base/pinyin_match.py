import re
from bisect import bisect_right
from typing import Optional
from ....entities import ALL_CARDS
from ....models.state import ensure_card_state

try:
    from pypinyin import Style as _PYPINYIN_STYLE
    from pypinyin import pinyin as _pypinyin
except ImportError:
    _PYPINYIN_STYLE = None
    _pypinyin = None

GB2312_PINYIN_ZONE_STARTS = (
    (0xB0A1, "a"),
    (0xB0C5, "b"),
    (0xB2C1, "c"),
    (0xB4EE, "d"),
    (0xB6EA, "e"),
    (0xB7A2, "f"),
    (0xB8C1, "g"),
    (0xB9FE, "h"),
    (0xBBF7, "j"),
    (0xBFA6, "k"),
    (0xC0AC, "l"),
    (0xC2E8, "m"),
    (0xC4C3, "n"),
    (0xC5B6, "o"),
    (0xC5BE, "p"),
    (0xC6DA, "q"),
    (0xC8BB, "r"),
    (0xC8F6, "s"),
    (0xCBFA, "t"),
    (0xCDDA, "w"),
    (0xCEF4, "x"),
    (0xD1B9, "y"),
    (0xD4D1, "z"),
)
GB2312_LEVEL1_END = 0xD7F9
_ZONE_CODES = tuple(code for code, _ in GB2312_PINYIN_ZONE_STARTS)
_ZONE_LETTERS = tuple(letter for _, letter in GB2312_PINYIN_ZONE_STARTS)
ANY_INITIAL = tuple("abcdefghijklmnopqrstuvwxyz")
BRACKET_SEGMENT_RE = re.compile(r"[（(][^（）()]*[）)]")


def gbk_zone_initial(ch: str) -> str:
    try:
        raw = ch.encode("gbk")
    except (UnicodeEncodeError, LookupError):
        return ""
    if len(raw) != 2:
        return ""
    code = (raw[0] << 8) | raw[1]
    if code < _ZONE_CODES[0] or code > GB2312_LEVEL1_END:
        return ""
    return _ZONE_LETTERS[bisect_right(_ZONE_CODES, code) - 1]


def char_initial_choices(ch: str) -> tuple:
    if ch.isascii():
        return (ch.lower(),) if ch.isalpha() else ()
    if not "\u4e00" <= ch <= "\u9fff":
        return ()
    if _pypinyin is not None:
        try:
            readings = _pypinyin(ch, style=_PYPINYIN_STYLE.FIRST_LETTER, heteronym=True)[0]
        except Exception:
            readings = []
        choices = tuple(sorted({r[:1] for r in readings if r and r[:1].isascii() and r[:1].isalpha()}))
        if choices:
            return choices
    zone = gbk_zone_initial(ch)
    if zone:
        return (zone,)
    return ANY_INITIAL


def strip_name_modifiers(name: str) -> str:
    return BRACKET_SEGMENT_RE.sub("", name.replace("＋", "+")).replace("+", "")


def name_initial_pattern(name: str) -> list:
    choices = [char_initial_choices(ch) for ch in strip_name_modifiers(name)]
    return [c for c in choices if c]


def normalize_initial_query(query: str) -> str:
    if not isinstance(query, str):
        return ""
    cleaned = query.strip().lower()
    if not cleaned or not cleaned.isascii() or not cleaned.isalpha():
        return ""
    return cleaned


def greedy_initial_match(query: str, pattern: list) -> bool:
    if not query or not pattern:
        return False
    pos = 0
    for choices in pattern:
        if query[pos] in choices:
            pos += 1
            if pos == len(query):
                return True
    return False


def prefix_initial_match(query: str, pattern: list) -> bool:
    if not query or not pattern or len(query) > len(pattern):
        return False
    return all(query[idx] in pattern[idx] for idx in range(len(query)))


def find_entry_by_query(entries: list[tuple[str, str]], query: str) -> Optional[str]:
    raw = str(query or "").strip()
    if not raw:
        return None
    for entry_id, name in entries:
        if name == raw:
            return entry_id
    if not raw.isascii():
        for entry_id, name in entries:
            if raw in name:
                return entry_id
    normalized = normalize_initial_query(raw)
    if not normalized:
        return None
    patterns = [(entry_id, name_initial_pattern(name)) for entry_id, name in entries]
    for entry_id, pattern in patterns:
        if prefix_initial_match(normalized, pattern):
            return entry_id
    for entry_id, pattern in patterns:
        if greedy_initial_match(normalized, pattern):
            return entry_id
    return None


def find_hand_index_by_initials(hand: list, query: str) -> Optional[int]:
    normalized = normalize_initial_query(query)
    if not normalized:
        return None
    for idx, entry in enumerate(hand, 1):
        try:
            card = ALL_CARDS.get(ensure_card_state(entry))
        except (TypeError, ValueError):
            card = None
        if not card:
            continue
        if greedy_initial_match(normalized, name_initial_pattern(card.name)):
            return idx
    return None
