from ..models.state import GameRun
from ..entities import get_relic_name, get_relic_desc
from ..cards import ALL_CARDS
from ..data.locale_data import get_locale_text
def render_start_ancient(run: GameRun) -> str:
    from .party import render_waiting
    p = run.player
    if run.node_data.get("coop_done"):
        return render_waiting(run)
    options = run.node_data.get("options", [])
    style = run.node_data.get("style", "default")
    style_names = {
        "default": get_locale_text("i18n_renderer_extra.map.style_default"),
        "abyss": get_locale_text("i18n_renderer_extra.map.style_abyss"),
        "glacier": get_locale_text("i18n_renderer_extra.map.style_glacier")
    }
    name_str = style_names.get(style, get_locale_text("i18n_renderer_extra.map.style_default"))
    lines = [
        get_locale_text("i18n_renderer_extra.map.separator"),
        get_locale_text("i18n_renderer_extra.map.start_title", style=name_str),
        get_locale_text("i18n_renderer_extra.map.status_line", name=run.player.name, hp=p.hp, max_hp=p.max_hp, gold=p.gold),
        "",
        get_locale_text("i18n_renderer_extra.map.start_intro", style=name_str),
        ""
    ]
    for idx, opt in enumerate(options, 1):
        rid = opt["relic"]
        rname = get_relic_name(rid)
        rdesc = get_relic_desc(rid)
        if opt["type"] == "double":
            lines.append(get_locale_text("i18n_renderer_extra.map.relic_option", idx=idx, style=name_str, rname=rname, rdesc=rdesc))
        else:
            cid = opt["card"]
            cname = ALL_CARDS[cid].name
            cdesc = ALL_CARDS[cid].desc
            lines.append(get_locale_text("i18n_renderer_extra.map.start_card_option", idx=idx, style=name_str, cname=cname, rname=rname, cdesc=cdesc, rdesc=rdesc))
    lines.append("")
    lines.append(get_locale_text("i18n_renderer_extra.map.separator"))
    lines.append(get_locale_text("i18n_renderer_extra.map.contract_cmd"))
    lines.append(get_locale_text("i18n_renderer_extra.map.separator"))
    return "\n".join(lines)

def render_ancient(run: GameRun) -> str:
    p = run.player
    options = run.node_data.get("options", [])
    style = run.node_data.get("style", "default")
    style_names = {
        "default": get_locale_text("i18n_renderer_extra.map.style_default"),
        "abyss": get_locale_text("i18n_renderer_extra.map.style_abyss"),
        "glacier": get_locale_text("i18n_renderer_extra.map.style_glacier")
    }
    name_str = style_names.get(style, get_locale_text("i18n_renderer_extra.map.style_default"))
    lines = [
        get_locale_text("i18n_renderer_extra.map.separator"),
        get_locale_text("i18n_renderer_extra.map.bless_title", stage=p.stage, style=name_str),
        get_locale_text("i18n_renderer_extra.map.status_line", name=run.player.name, hp=p.hp, max_hp=p.max_hp, gold=p.gold),
        "",
        get_locale_text("i18n_renderer_extra.map.bless_intro", style=name_str),
        ""
    ]
    for idx, opt in enumerate(options, 1):
        rid = opt["relic"]
        rname = get_relic_name(rid)
        rdesc = get_relic_desc(rid)
        if opt.get("type") == "double":
            lines.append(get_locale_text("i18n_renderer_extra.map.relic_option", idx=idx, style=name_str, rname=rname, rdesc=rdesc))
            continue
        cid = opt["card"]
        cname = ALL_CARDS[cid].name
        cdesc = ALL_CARDS[cid].desc
        lines.append(get_locale_text("i18n_renderer_extra.map.bless_card_option", idx=idx, rname=rname, cname=cname, rdesc=rdesc, cdesc=cdesc))
    lines.append("")
    lines.append(get_locale_text("i18n_renderer_extra.map.separator"))
    lines.append(get_locale_text("i18n_renderer_extra.map.bless_cmd"))
    lines.append(get_locale_text("i18n_renderer_extra.map.separator"))
    return "\n".join(lines)
