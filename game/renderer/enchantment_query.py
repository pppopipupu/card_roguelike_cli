from ..core.inventory.enchantment_service import (
    get_enchantment_desc,
    get_enchantment_name,
    get_enchantment_rarity_label,
)
from ..data.entities.enchantment_data import (
    ENCHANTMENT_CONFIG,
    ENCHANTMENT_QUERY_OVERVIEW_ALIASES,
)
from ..data.text.locale_data import get_locale_text


def append_enchantment_queries(
    lines: list[str],
    q_search: str,
    tier_filter: str | None,
    raw_query: str = "",
) -> bool:
    if not tier_filter and q_search in ENCHANTMENT_QUERY_OVERVIEW_ALIASES:
        lines.append(get_locale_text("renderer_menu.enchantments_all_title"))
        for eid in ENCHANTMENT_CONFIG:
            ename = get_enchantment_name(eid)
            rarity_label = get_enchantment_rarity_label(eid)
            desc = get_enchantment_desc(eid)
            lines.append(
                get_locale_text(
                    "renderer_menu.enchantment_all_line",
                    name=ename,
                    rarity=rarity_label,
                    desc=desc,
                )
            )
        lines.append("")
        return True

    found = False
    is_overview_alias = q_search in ENCHANTMENT_QUERY_OVERVIEW_ALIASES
    raw_lower = raw_query.strip().lower()
    for eid, cfg in ENCHANTMENT_CONFIG.items():
        ename = get_enchantment_name(eid)
        exact_raw_match = bool(raw_lower) and raw_lower == ename.lower()
        if tier_filter and str(cfg.get("rarity", "common")).lower() != tier_filter and not exact_raw_match:
            continue
        mode = str(cfg.get("name_mode", "none"))
        affix = get_locale_text(f"i18n_enchantment.affixes.{eid}") if mode in ("prefix", "suffix") else ""
        affix_clean = affix.strip()
        match_keyword = (
            (not q_search)
            or (tier_filter is not None and is_overview_alias)
            or (q_search == eid.lower())
            or (q_search in eid.lower())
            or (q_search in ename.lower())
            or (bool(affix_clean) and q_search in affix_clean.lower())
        )
        if not match_keyword:
            continue
        found = True
        rarity_label = get_enchantment_rarity_label(eid)
        desc = get_enchantment_desc(eid)
        lines.append(
            get_locale_text(
                "renderer_menu.enchantment_detail_title",
                name=ename,
                id=eid,
                rarity=rarity_label,
            )
        )
        lines.append(get_locale_text("renderer_menu.effect_line", desc=desc))
        if mode == "prefix":
            lines.append(get_locale_text("renderer_menu.enchantment_affix_prefix", affix=affix_clean))
        elif mode == "suffix":
            lines.append(get_locale_text("renderer_menu.enchantment_affix_suffix", affix=affix_clean))
        else:
            lines.append(get_locale_text("renderer_menu.enchantment_affix_none"))
        lines.append("")
    return found
