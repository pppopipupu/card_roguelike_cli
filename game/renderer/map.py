from ..models.state import GameRun
from ..entities import get_relic_name, get_relic_desc
from ..cards import ALL_CARDS
from ..data.locale_data import get_locale_text
from ..data.map_config import MapConfig

def render_map_select(run: GameRun) -> str:
    from .party import render_party_status
    p = run.player
    options = run.node_data.get("options", [])
    relics_str = ""
    if p.relics:
        relic_items = " ".join([get_locale_text("i18n_renderer_extra.map.relic_item", name=get_relic_name(r)) for r in p.relics])
        relics_str = get_locale_text("i18n_renderer_extra.map.relic_prefix") + relic_items
    lines = [
        get_locale_text("i18n_renderer_extra.map.separator"),
        get_locale_text("i18n_renderer_extra.map.title", stage=p.stage),
        get_locale_text("i18n_renderer_extra.map.status_line", name=run.player.name, hp=p.hp, max_hp=p.max_hp, gold=p.gold) + relics_str,
        ""
    ]
    preview_lines = [get_locale_text("i18n_renderer_extra.map.preview_title")]
    nodes_dict = {}
    nodes_by_stage = {}
    for stage_str, layer in run.map_data.get("nodes", {}).items():
        stg = int(stage_str)
        nodes_by_stage[stg] = layer
        for nd in layer:
            nodes_dict[nd["id"]] = nd
    curr_id = run.map_data.get("current_node_id")
    type_names = {
        "battle": get_locale_text("i18n_renderer_extra.map.node_battle"),
        "elite": get_locale_text("i18n_renderer_extra.map.node_elite"),
        "event": get_locale_text("i18n_renderer_extra.map.node_event"),
        "shop": get_locale_text("i18n_renderer_extra.map.node_shop"),
        "rest": get_locale_text("i18n_renderer_extra.map.node_rest"),
        "treasure": get_locale_text("i18n_renderer_extra.map.node_treasure"),
        "life_merchant": get_locale_text("i18n_renderer_extra.map.node_life_merchant"),
        "boss": get_locale_text("i18n_renderer_extra.map.node_boss"),
        "corpse": get_locale_text("i18n_renderer_extra.map.node_corpse")
    }
    max_preview_stage = min(MapConfig.FINAL_BOSS_STAGE, p.stage + 3)
    curr_layer_nodes = []
    if not curr_id:
        curr_layer_nodes = nodes_by_stage.get(p.stage, [])
    else:
        curr_node = nodes_dict.get(curr_id)
        if curr_node:
            curr_layer_nodes = [nodes_dict[nid] for nid in curr_node.get("next", []) if nid in nodes_dict]
    if curr_layer_nodes:
        preview_lines.append(get_locale_text("i18n_renderer_extra.map.current_line", stage=p.stage))
        for idx, nd in enumerate(curr_layer_nodes, 1):
            next_types = []
            for nid in nd.get("next", []):
                next_node = nodes_dict.get(nid)
                if next_node:
                    next_types.append(type_names.get(next_node["type"], next_node["type"]))
            next_str = get_locale_text("i18n_renderer_extra.map.next_arrow", stage=p.stage + 1, types=", ".join(next_types)) if next_types else get_locale_text("i18n_renderer_extra.map.endpoint")
            preview_lines.append(f"    [{idx}] {type_names.get(nd['type'], nd['type'])}{next_str}")
    for next_s in range(p.stage + 1, max_preview_stage + 1):
        next_layer_nodes = nodes_by_stage.get(next_s, [])
        if not next_layer_nodes:
            continue
        reachable_ids = set()
        prev_layer_nodes = []
        if next_s - 1 == p.stage:
            prev_layer_nodes = curr_layer_nodes
        else:
            prev_layer_nodes = nodes_by_stage.get(next_s - 1, [])
        for pn in prev_layer_nodes:
            for nid in pn.get("next", []):
                reachable_ids.add(nid)
        filtered_nodes = [nd for nd in next_layer_nodes if nd["id"] in reachable_ids]
        if not filtered_nodes:
            filtered_nodes = next_layer_nodes
        layer_title = get_locale_text("i18n_renderer_extra.map.layer_next") if next_s == p.stage + 1 else (get_locale_text("i18n_renderer_extra.map.layer_next2") if next_s == p.stage + 2 else get_locale_text("i18n_renderer_extra.map.layer_target"))
        preview_lines.append(get_locale_text("i18n_renderer_extra.map.layer_line", title=layer_title, stage=next_s))
        for idx, nd in enumerate(filtered_nodes, 1):
            next_types = []
            for nid in nd.get("next", []):
                next_node = nodes_dict.get(nid)
                if next_node:
                    next_types.append(type_names.get(next_node["type"], next_node["type"]))
            next_str = get_locale_text("i18n_renderer_extra.map.next_arrow", stage=next_s + 1, types=", ".join(next_types)) if next_types else get_locale_text("i18n_renderer_extra.map.endpoint")
            preview_lines.append(f"    [{idx}] {type_names.get(nd['type'], nd['type'])}{next_str}")
    lines.extend(preview_lines)
    lines.append("")
    if run.player_count() > 1:
        lines.append(render_party_status(run))
        votes = run.node_data.get("votes", {})
        if votes:
            vote_names = []
            for uid, vote in votes.items():
                member = run.players.get(uid)
                vote_names.append(f"{member.name if member else uid}→{vote}")
            lines.append(get_locale_text("i18n_renderer_extra.map.votes_line", votes=get_locale_text("i18n_renderer_extra.map.vote_separator").join(vote_names)))
        lines.append(get_locale_text("i18n_renderer_extra.map.coop_hint"))
        lines.append("")
    lines.append(get_locale_text("i18n_renderer_extra.map.choose_prompt"))
    for idx, opt in enumerate(options, 1):
        lines.append(f" [{idx}] {opt.get('desc', '')}")
    if p.fold_guide:
        lines.append(get_locale_text("i18n_renderer_extra.map.fold_hint"))
    else:
        lines.append(get_locale_text("i18n_renderer_extra.map.route_cmd"))
    lines.append(get_locale_text("i18n_renderer_extra.map.help_hint"))
    lines.append(get_locale_text("i18n_renderer_extra.map.separator"))
    return "\n".join(lines)

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
