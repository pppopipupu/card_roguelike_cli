from functools import lru_cache
import math
import re
from typing import Optional

from ..data.balance_config import SCIENTIFIC_NOTATION_MAX_DIGITS, SCIENTIFIC_NOTATION_PRECISION
from ..entities import get_relic_name
from ..data.locale_data import get_locale_text


def format_buff_stacks(buff) -> str:
    if getattr(buff, "id", "") == "exhaustion":
        return get_locale_text("i18n_renderer_extra.formatters.exhaustion_stack", name=buff.name, stacks=format_large_int(buff.stacks))
    stacks2 = getattr(buff, "stacks2", None)
    if stacks2 is not None and stacks2 > 0:
        return f"{buff.name}({format_large_int(buff.stacks)},{format_large_int(stacks2)})"
    if buff.stacks > 1:
        return f"{buff.name} x{format_large_int(buff.stacks)}"
    return buff.name


def format_buff_list(buffs, sep: str = " | ") -> str:
    return sep.join(format_buff_stacks(b) for b in buffs)


def format_persistent_buff_bar(player) -> str:
    pbuffs = getattr(player, "persistent_buffs", None) or []
    if not pbuffs:
        return ""
    return get_locale_text("i18n_renderer_extra.formatters.persistent_buff_prefix") + format_buff_list(pbuffs, " ")

def format_buff_detail(buff, desc: str, indent: str = "    ") -> str:
    stacks2 = getattr(buff, "stacks2", None)
    if stacks2 is not None and stacks2 > 0:
        return get_locale_text("i18n_renderer_extra.formatters.buff_detail_persist", indent=indent, name=buff.name, stacks=format_large_int(buff.stacks), stacks2=format_large_int(stacks2), desc=desc)
    return get_locale_text("i18n_renderer_extra.formatters.buff_detail", indent=indent, name=buff.name, stacks=format_large_int(buff.stacks), desc=desc)


def get_effective_max_hp(player, run=None) -> int:
    from ..core.world.sp_system import effective_max_hp_for_player
    in_battle = bool(run is not None and getattr(run, "node_type", "") == "battle")
    return effective_max_hp_for_player(player, in_battle=in_battle)


def format_relic_name_with_counter(relic_id: str, relic_counters: Optional[dict] = None) -> str:
    name = get_relic_name(relic_id)
    from ..data.relic_data import RELIC_CONFIG
    cfg = RELIC_CONFIG.get(relic_id, {})
    if "counter_max" in cfg:
        counters = relic_counters if relic_counters is not None else {}
        val = counters.get(relic_id, cfg.get("counter_init", 0))
        return f"{name}({val}/{cfg['counter_max']})"
    return name

def format_relic_bar(relics, relic_counters: Optional[dict] = None) -> str:
    if not relics:
        return ""
    return get_locale_text("i18n_renderer_extra.formatters.relic_prefix") + " ".join(
        get_locale_text("i18n_renderer_extra.formatters.relic_item", name=format_relic_name_with_counter(r, relic_counters))
        for r in relics
    )


def _format_digits_scientific(
    digits: str,
    precision: int = SCIENTIFIC_NOTATION_PRECISION,
    exponent_override: Optional[int] = None,
) -> str:
    exp = (len(digits) - 1) if exponent_override is None else exponent_override
    if precision <= 0:
        lead = int(digits[0])
        if len(digits) > 1 and digits[1] >= "5":
            lead += 1
            if lead == 10:
                lead = 1
                exp += 1
        return f"{lead}e+{exp}"
    needed = precision + 1
    sample = digits[:needed].ljust(needed, "0")
    rounded = int(sample)
    if len(digits) > needed and digits[needed] >= "5":
        rounded += 1
    if rounded >= 10 ** needed:
        rounded //= 10
        exp += 1
    mantissa_str = str(rounded)
    return f"{mantissa_str[0]}.{mantissa_str[1:]}e+{exp}"


def _format_int_scientific(abs_value: int, precision: int) -> str:
    bit_len = abs_value.bit_length()
    if bit_len < 14000:
        return _format_digits_scientific(str(abs_value), precision)
    exp = int((bit_len - 1) * math.log10(2))
    pow10 = 10 ** exp
    while pow10 * 10 <= abs_value:
        pow10 *= 10
        exp += 1
    while pow10 > abs_value:
        pow10 //= 10
        exp -= 1
    scale = max(0, exp - precision - 1)
    head = abs_value // (10 ** scale)
    return _format_digits_scientific(str(head), precision, exponent_override=exp)


def format_large_int(
    value: int,
    max_digits: int = SCIENTIFIC_NOTATION_MAX_DIGITS,
    precision: int = SCIENTIFIC_NOTATION_PRECISION,
) -> str:
    if isinstance(value, bool):
        return str(value)
    if value < 0:
        sign = "-"
        abs_value = -value
    else:
        sign = ""
        abs_value = value
    if abs_value < 10 ** max_digits:
        return f"{sign}{abs_value}"
    return f"{sign}{_format_int_scientific(abs_value, precision)}"


@lru_cache(maxsize=8)
def _get_output_number_pattern(max_digits: int) -> re.Pattern:
    return re.compile(
        r"0[xX][0-9a-fA-F]+"
        r"|[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
        r"|(?<![0-9A-Za-z_])[+-]?(?:\d+\.\d+|\d+(?:\.\d+)?[eE][+-]?\d+)"
        rf"|(?<![0-9A-Za-z_])([+\-xX]?)([1-9]\d{{{max_digits},}})(?![0-9a-z_]|\.\d|[eE][+-]?\d)"
    )


def format_output_numbers(
    text: Optional[str],
    max_digits: int = SCIENTIFIC_NOTATION_MAX_DIGITS,
    precision: int = SCIENTIFIC_NOTATION_PRECISION,
) -> str:
    if not text:
        return "" if text is None else text
    if not isinstance(text, str):
        text = str(text)
    if len(text) <= max_digits:
        return text
    pattern = _get_output_number_pattern(max_digits)

    def _replace(match: re.Match) -> str:
        prefix = match.group(1)
        digits = match.group(2)
        if digits is None:
            return match.group(0)
        return f"{prefix}{_format_digits_scientific(digits, precision)}"

    return pattern.sub(_replace, text)
