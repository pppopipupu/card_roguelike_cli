from ..models.state import GameRun
from ..data.world.ancient_node_config import ANCIENT_DEITIES, SPEED_DESCENT_TIERS
from ..entities import get_relic_name, get_relic_desc
from ..cards import ALL_CARDS
from ..data.text.locale_data import get_locale_text
from .formatters import format_npcs_and_players_line
from .world_grid import get_run_coord_prefix


def _world_players_line(run: GameRun) -> str:
    from ..core.world.presence import render_players_for
    return format_npcs_and_players_line(None, render_players_for(run.user_id, run=run))


def _resolve_deity_info(style: str) -> tuple[str, str, str, str]:
    cfg = ANCIENT_DEITIES.get(style, ANCIENT_DEITIES["default"])
    return (
        get_locale_text(cfg["style_key"]),
        get_locale_text(cfg["name_key"]),
        get_locale_text(cfg["title_key"]),
        get_locale_text(cfg["desc_key"]),
    )


def render_start_ancient(run: GameRun) -> str:
    from .party import render_waiting
    p = run.player
    if run.node_data.get("coop_done"):
        return render_waiting(run)
    if run.node_data.get("speed_descent_menu"):
        from ..models.manager import SaveManager
        stats = SaveManager().load_stats(run.user_id)
        gp = int(getattr(stats, "gp", 0) or 0)
        lines = [
            get_locale_text("i18n_renderer_extra.map.separator"),
            get_locale_text("i18n_renderer_extra.map.speed_descent_menu_title"),
            get_locale_text("i18n_renderer_extra.map.speed_descent_gp_line", gp=gp),
            "",
        ]
        for idx, tier in enumerate(SPEED_DESCENT_TIERS, 1):
            lines.append(
                get_locale_text(
                    "i18n_renderer_extra.map.speed_descent_tier_option",
                    idx=idx,
                    floor=tier["floor"],
                    gp_cost=tier["gp_cost"],
                    picks=tier["ancient_picks"],
                )
            )
        lines.append(
            get_locale_text(
                "i18n_renderer_extra.map.speed_descent_back_option",
                idx=len(SPEED_DESCENT_TIERS) + 1,
            )
        )
        lines.append("")
        lines.append(get_locale_text("i18n_renderer_extra.map.separator"))
        lines.append(get_locale_text("i18n_renderer_extra.map.speed_descent_cmd"))
        lines.append(get_locale_text("i18n_renderer_extra.map.separator"))
        return "\n".join(lines)
    options = run.node_data.get("options", [])
    style = run.node_data.get("deity") or run.node_data.get("style", "default")
    name_str, deity_name, deity_title, deity_desc = _resolve_deity_info(style)
    lines = [
        get_locale_text("i18n_renderer_extra.map.separator"),
        get_locale_text("i18n_renderer_extra.map.start_title", style=name_str, deity=deity_name),
        get_locale_text("i18n_renderer_extra.map.status_line", name=run.player.name, hp=p.hp, max_hp=p.max_hp, gold=p.gold),
    ]
    npcs_line = _world_players_line(run)
    if npcs_line:
        lines.append(npcs_line)
    lines.extend([
        "",
        get_locale_text("i18n_renderer_extra.map.deity_banner", deity=deity_name, title=deity_title, desc=deity_desc),
        get_locale_text("i18n_renderer_extra.map.start_intro", style=name_str, deity=deity_name),
        "",
    ])
    for idx, opt in enumerate(options, 1):
        if opt.get("type") == "speed_descent":
            lines.append(get_locale_text("i18n_renderer_extra.map.speed_descent_option", idx=idx))
            continue
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
    lines.append(get_locale_text("i18n_renderer_extra.map.fold_hint") if p.fold_guide else get_locale_text("i18n_renderer_extra.map.contract_cmd"))
    lines.append(get_locale_text("i18n_renderer_extra.map.separator"))
    return "\n".join(lines)


def render_ancient(run: GameRun) -> str:
    from .party import render_waiting
    p = run.player
    if run.node_data.get("coop_done"):
        return render_waiting(run)
    if run.node_data.get("speed_descent_menu"):
        from ..models.manager import SaveManager
        stats = SaveManager().load_stats(run.user_id)
        gp = int(getattr(stats, "gp", 0) or 0)
        lines = [
            get_locale_text("i18n_renderer_extra.map.separator"),
            get_locale_text("i18n_renderer_extra.map.speed_descent_menu_title"),
            get_locale_text("i18n_renderer_extra.map.speed_descent_gp_line", gp=gp),
            "",
        ]
        for idx, tier in enumerate(SPEED_DESCENT_TIERS, 1):
            lines.append(
                get_locale_text(
                    "i18n_renderer_extra.map.speed_descent_tier_option",
                    idx=idx,
                    floor=tier["floor"],
                    gp_cost=tier["gp_cost"],
                    picks=tier["ancient_picks"],
                )
            )
        lines.append(
            get_locale_text(
                "i18n_renderer_extra.map.speed_descent_back_option",
                idx=len(SPEED_DESCENT_TIERS) + 1,
            )
        )
        lines.append("")
        lines.append(get_locale_text("i18n_renderer_extra.map.separator"))
        lines.append(get_locale_text("i18n_renderer_extra.map.speed_descent_cmd"))
        lines.append(get_locale_text("i18n_renderer_extra.map.separator"))
        return "\n".join(lines)
    options = run.node_data.get("options", [])
    style = run.node_data.get("deity") or run.node_data.get("style", "default")
    name_str, deity_name, deity_title, deity_desc = _resolve_deity_info(style)
    lines = [
        get_locale_text("i18n_renderer_extra.map.separator"),
        get_locale_text("i18n_renderer_extra.map.bless_title", coord_prefix=get_run_coord_prefix(run), style=name_str, deity=deity_name),
        get_locale_text("i18n_renderer_extra.map.status_line", name=run.player.name, hp=p.hp, max_hp=p.max_hp, gold=p.gold),
    ]
    npcs_line = _world_players_line(run)
    if npcs_line:
        lines.append(npcs_line)
    lines.extend([
        "",
        get_locale_text("i18n_renderer_extra.map.deity_banner", deity=deity_name, title=deity_title, desc=deity_desc),
        get_locale_text("i18n_renderer_extra.map.bless_intro", style=name_str, deity=deity_name),
    ])
    sd_total = int(run.node_data.get("speed_descent_picks_total", 0) or 0)
    if sd_total > 0:
        sd_cur = int(run.node_data.get("speed_descent_pick_index", 1) or 1)
        lines.append(get_locale_text("i18n_renderer_extra.map.speed_descent_progress", current=sd_cur, total=sd_total))
    lines.append("")
    for idx, opt in enumerate(options, 1):
        if opt.get("type") == "speed_descent":
            lines.append(get_locale_text("i18n_renderer_extra.map.speed_descent_option", idx=idx))
            continue
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
    lines.append(get_locale_text("i18n_renderer_extra.map.fold_hint") if p.fold_guide else get_locale_text("i18n_renderer_extra.map.bless_cmd"))
    lines.append(get_locale_text("i18n_renderer_extra.map.separator"))
    return "\n".join(lines)
