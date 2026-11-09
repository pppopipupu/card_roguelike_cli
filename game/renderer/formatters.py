from ..entities import get_relic_name
from ..data.locale_data import get_locale_text


def format_buff_stacks(buff) -> str:
    stacks2 = getattr(buff, "stacks2", None)
    if stacks2 is not None and stacks2 > 0:
        return f"{buff.name}({buff.stacks},{stacks2})"
    if buff.stacks > 1:
        return f"{buff.name} x{buff.stacks}"
    return buff.name


def format_buff_list(buffs, sep: str = " | ") -> str:
    return sep.join(format_buff_stacks(b) for b in buffs)


def format_buff_detail(buff, desc: str, indent: str = "    ") -> str:
    stacks2 = getattr(buff, "stacks2", None)
    if stacks2 is not None and stacks2 > 0:
        return get_locale_text("i18n_renderer_extra.formatters.buff_detail_persist", indent=indent, name=buff.name, stacks=buff.stacks, stacks2=stacks2, desc=desc)
    return get_locale_text("i18n_renderer_extra.formatters.buff_detail", indent=indent, name=buff.name, stacks=buff.stacks, desc=desc)


def get_effective_max_hp(player) -> int:
    total = player.max_hp
    for buff in player.buffs:
        if buff.id.startswith("iron_will"):
            total += buff.stacks * (15 if buff.id.endswith("+") else 10)
    return int(total)


def format_relic_bar(relics) -> str:
    if not relics:
        return ""
    return get_locale_text("i18n_renderer_extra.formatters.relic_prefix") + " ".join(get_locale_text("i18n_renderer_extra.formatters.relic_item", name=get_relic_name(r)) for r in relics)
