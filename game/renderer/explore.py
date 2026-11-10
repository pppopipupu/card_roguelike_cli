from ..models.state import GameRun
from ..entities import get_relic_name, get_relic_desc
from ..cards import ALL_CARDS
from .menu import get_card_cost_str
from .formatters import format_relic_bar
from ..data.locale_data import get_locale_text

def render_event(run: GameRun) -> str:
    p = run.player
    data = run.node_data
    relics_str = format_relic_bar(p.relics)
    lines = [
        get_locale_text("renderer_explore.separator"),
        get_locale_text("renderer_explore.event_title", stage=p.stage),
        get_locale_text("renderer_explore.status_line", name=run.player.name, hp=p.hp, max_hp=p.max_hp, gold=p.gold) + relics_str,
        "",
        data.get("description", get_locale_text("renderer_explore.event_default_desc")),
        "",
        get_locale_text("renderer_explore.event_prompt")
    ]
    options = data.get("options", [])
    for idx, opt in enumerate(options, 1):
        lines.append(get_locale_text("renderer_explore.event_option", idx=idx, text=opt.get('text', '')))
    if getattr(run, "coop_id", ""):
        from .party import render_party_status
        lines.append(render_party_status(run))
        votes = data.get("votes", {})
        if votes:
            vote_names = []
            for uid, vote in votes.items():
                member = run.players.get(uid)
                vote_names.append(f"{member.name if member else uid}→{vote}")
            lines.append(get_locale_text("i18n_renderer_extra.event.votes_line", votes=get_locale_text("i18n_renderer_extra.event.vote_separator").join(vote_names)))
        lines.append(get_locale_text("i18n_renderer_extra.event.coop_hint"))
        lines.append("")
    lines.append(get_locale_text("renderer_explore.separator"))
    if p.fold_guide:
        lines.append(get_locale_text("renderer_explore.guide_folded"))
    else:
        lines.append(get_locale_text("renderer_explore.guide_choice"))
    lines.append(get_locale_text("renderer_explore.separator"))
    return "\n".join(lines)

def render_shop(run: GameRun) -> str:
    from .party import render_party_status, render_waiting
    p = run.player
    data = run.node_data
    if getattr(run, "coop_id", "") and data.get("coop_done"):
        return render_waiting(run)
    relics_str = format_relic_bar(p.relics)
    lines = [
        get_locale_text("renderer_explore.separator"),
        get_locale_text("renderer_explore.shop_title", stage=p.stage),
        get_locale_text("renderer_explore.status_line", name=run.player.name, hp=p.hp, max_hp=p.max_hp, gold=p.gold) + relics_str,
        "",
    ]
    if getattr(run, "coop_id", ""):
        lines.append(render_party_status(run))
        lines.append(get_locale_text("renderer_explore.shop_coop_note"))
        lines.append("")
    lines.append(get_locale_text("renderer_explore.shop_intro"))
    lines.append("")
    items = data.get("items", [])
    for idx, item in enumerate(items, 1):
        itype = item.get("type")
        price = item.get("price")
        sold = item.get("sold", False)
        if sold:
            lines.append(get_locale_text("renderer_explore.shop_sold", idx=idx))
            continue
        if itype == "card":
            card = ALL_CARDS.get(item.get("card_id"))
            if card:
                color_ch = "⚫" if card.color == "curse" else ("🔵" if card.color == "wizard" else "⚪")
                cost_str = get_card_cost_str(card)
                lines.append(get_locale_text("renderer_explore.shop_card", idx=idx, color=color_ch, name=card.name, cost=cost_str, price=price, desc=card.desc))
        elif itype == "relic":
            rid = item.get("relic_id")
            lines.append(get_locale_text("renderer_explore.shop_relic", idx=idx, name=get_relic_name(rid), price=price, desc=get_relic_desc(rid)))
        elif itype == "gem":
            from ..data.gem_data import GEM_CONFIG
            gid = item.get("gem_id")
            g_cfg = GEM_CONFIG.get(gid, {})
            lines.append(get_locale_text("renderer_explore.shop_gem", idx=idx, name=g_cfg.get('name', gid), price=price, desc=g_cfg.get('desc', '')))
        elif itype == "remove":
            lines.append(get_locale_text("renderer_explore.shop_remove", idx=idx, price=price))
        elif itype == "upgrade":
            lines.append(get_locale_text("renderer_explore.shop_upgrade", idx=idx, price=price))
        elif itype == "leave":
            lines.append(get_locale_text("renderer_explore.shop_leave", idx=idx))
    lines.append(get_locale_text("renderer_explore.separator"))
    if p.fold_guide:
        lines.append(get_locale_text("renderer_explore.guide_folded"))
    else:
        lines.append(get_locale_text("renderer_explore.shop_prompt"))
    lines.append(get_locale_text("renderer_explore.separator"))
    return "\n".join(lines)

def render_rest(run: GameRun) -> str:
    from .party import render_party_status, render_waiting
    p = run.player
    data = run.node_data
    if getattr(run, "coop_id", "") and data.get("coop_done"):
        return render_waiting(run)
    relics_str = format_relic_bar(p.relics)
    lines = [
        get_locale_text("renderer_explore.separator"),
        get_locale_text("render_rest_title", stage=p.stage),
        get_locale_text("renderer_explore.status_line_hp", name=run.player.name, hp=p.hp, max_hp=p.max_hp) + relics_str,
        "",
    ]
    if getattr(run, "coop_id", ""):
        lines.append(render_party_status(run))
        lines.append("")
    lines.append(get_locale_text("render_rest_desc"))
    items = data.get("items", [])
    available_items = [it for it in items if not it.get("taken")]
    for idx, it in enumerate(available_items, 1):
        itype = it.get("type")
        if itype == "rest_heal":
            lines.append(f" [{idx}] {get_locale_text('render_rest_heal')}")
        elif itype == "rest_meditate":
            lines.append(f" [{idx}] {get_locale_text('render_rest_meditate')}")
        elif itype == "rest_upgrade":
            lines.append(f" [{idx}] {get_locale_text('render_rest_upgrade')}")
        elif itype == "rest_mend":
            lines.append(get_locale_text("renderer_explore.rest_mend", idx=idx))
    lines.append(get_locale_text("renderer_explore.separator"))
    if not available_items:
        lines.append(get_locale_text("render_rest_completed"))
    lines.append(get_locale_text("render_rest_exit"))
    lines.append(get_locale_text("renderer_explore.separator"))
    return "\n".join(lines)

def render_reward(run: GameRun) -> str:
    from .party import render_party_status, render_waiting
    p = run.player
    data = run.node_data
    if getattr(run, "coop_id", "") and data.get("coop_done"):
        return render_waiting(run)
    if data.get("no_reward"):
        lines = [
            get_locale_text("renderer_explore.separator"),
            get_locale_text("renderer_explore.reward_no_reward_title"),
            "",
            get_locale_text("renderer_explore.reward_no_reward_escape"),
            get_locale_text("renderer_explore.reward_no_reward_empty"),
            "",
            get_locale_text("renderer_explore.separator"),
            get_locale_text("render_reward_exit_normal"),
            get_locale_text("renderer_explore.separator")
        ]
        return "\n".join(lines)
    quest_bonus = data.get("quest_bonus", "")
    lines = [
        get_locale_text("renderer_explore.separator"),
        get_locale_text("render_reward_title"),
        get_locale_text("renderer_explore.status_line", name=run.player.name, hp=p.hp, max_hp=p.max_hp, gold=p.gold),
        ""
    ]
    if getattr(run, "coop_id", ""):
        lines.append(render_party_status(run))
        lines.append("")
    if quest_bonus:
        lines.append(quest_bonus)
        lines.append("")
    items = data.get("items", [])
    available_items = [it for it in items if not it.get("taken")]
    has_forced = False
    for idx, it in enumerate(available_items, 1):
        prefix = ""
        if it.get("force"):
            prefix += get_locale_text("label_forced")
            has_forced = True
        if it.get("group_id"):
            prefix += get_locale_text("label_multi_choice")
        if it.get("bind_group"):
            prefix += get_locale_text("label_bundle")
        itype = it.get("type")
        if itype == "gold":
            lines.append(get_locale_text("renderer_explore.item_gold", idx=idx, prefix=prefix, amount=it.get('amount')))
        elif itype == "card_reward":
            lines.append(get_locale_text("renderer_explore.item_card", idx=idx, prefix=prefix))
        elif itype in ("relic", "quest_relic", "boss_relic"):
            rid = it.get("relic_id") or it.get("id")
            lines.append(get_locale_text("renderer_explore.item_relic", idx=idx, prefix=prefix, name=get_relic_name(rid), desc=get_relic_desc(rid)))
        elif itype == "gem":
            from ..data.gem_data import GEM_CONFIG
            gid = it.get("gem_id")
            g_cfg = GEM_CONFIG.get(gid, {})
            lines.append(get_locale_text("renderer_explore.item_gem", idx=idx, prefix=prefix, name=g_cfg.get('name', gid), desc=g_cfg.get('desc', '')))
        elif itype == "quest_card":
            cid = it.get("card_id")
            lines.append(get_locale_text("renderer_explore.reward_quest_card", idx=idx, prefix=prefix, name=ALL_CARDS[cid].name if cid in ALL_CARDS else cid))
        elif itype == "potion":
            from ..data.potion_data import get_potion_name, get_potion_desc
            pid = it.get("potion_id")
            lines.append(get_locale_text("renderer_explore.reward_potion", idx=idx, prefix=prefix, name=get_potion_name(pid), desc=get_potion_desc(pid)))
        elif itype == "shared_relic":
            rid = it.get("relic_id")
            lines.append(get_locale_text("renderer_explore.item_shared_relic", idx=idx, prefix=prefix, name=get_relic_name(rid)))
    lines.append(get_locale_text("renderer_explore.separator"))
    if not available_items:
        lines.append(get_locale_text("render_reward_completed"))
    else:
        if has_forced:
            lines.append(get_locale_text("render_reward_exit_forced"))
        else:
            lines.append(get_locale_text("render_reward_exit_normal"))
    lines.append(get_locale_text("renderer_explore.separator"))
    return "\n".join(lines)

def render_treasure(run: GameRun) -> str:
    from .party import render_party_status, render_waiting
    p = run.player
    data = run.node_data
    if getattr(run, "coop_id", "") and data.get("coop_done"):
        return render_waiting(run)
    text = data.get("text", "")
    state = data.get("state", "pending_remove")
    lines = [
        get_locale_text("renderer_explore.separator"),
        get_locale_text("render_treasure_title", stage=p.stage),
        get_locale_text("renderer_explore.status_line", name=run.player.name, hp=p.hp, max_hp=p.max_hp, gold=p.gold),
        "",
        text,
        ""
    ]
    if getattr(run, "coop_id", ""):
        lines.insert(3, render_party_status(run))
        lines.insert(4, "")
    if state == "pending_remove":
        lines.append(get_locale_text("render_treasure_sacrifice"))
    else:
        items = data.get("items", [])
        available_items = [it for it in items if not it.get("taken")]
        has_forced = False
        for idx, it in enumerate(available_items, 1):
            prefix = ""
            if it.get("force"):
                prefix += get_locale_text("label_forced")
                has_forced = True
            if it.get("group_id"):
                prefix += get_locale_text("label_multi_choice")
            if it.get("bind_group"):
                prefix += get_locale_text("label_bundle")
            itype = it.get("type")
            if itype == "gold":
                lines.append(get_locale_text("renderer_explore.item_gold", idx=idx, prefix=prefix, amount=it.get('amount')))
            elif itype == "card_reward":
                lines.append(get_locale_text("renderer_explore.item_card", idx=idx, prefix=prefix))
            elif itype in ("relic", "quest_relic", "boss_relic"):
                rid = it.get("relic_id") or it.get("id")
                lines.append(get_locale_text("renderer_explore.item_relic", idx=idx, prefix=prefix, name=get_relic_name(rid), desc=get_relic_desc(rid)))
            elif itype == "gem":
                from ..data.gem_data import GEM_CONFIG
                gid = it.get("gem_id")
                g_cfg = GEM_CONFIG.get(gid, {})
                lines.append(get_locale_text("renderer_explore.item_gem", idx=idx, prefix=prefix, name=g_cfg.get('name', gid), desc=g_cfg.get('desc', '')))
            elif itype == "shared_relic":
                rid = it.get("relic_id")
                lines.append(get_locale_text("renderer_explore.item_shared_relic", idx=idx, prefix=prefix, name=get_relic_name(rid)))
    lines.append(get_locale_text("renderer_explore.separator"))
    if state == "pending_remove":
        lines.append(get_locale_text("render_treasure_exit_sacrifice"))
    else:
        available_items = [it for it in data.get("items", []) if not it.get("taken")]
        if not available_items:
            lines.append(get_locale_text("render_treasure_completed"))
        else:
            has_forced = any(it.get("force") for it in available_items)
            if has_forced:
                lines.append(get_locale_text("render_treasure_exit_forced"))
            else:
                lines.append(get_locale_text("render_treasure_exit_normal"))
    lines.append(get_locale_text("renderer_explore.separator"))
    return "\n".join(lines)

def render_corpse_reward(run: GameRun) -> str:
    p = run.player
    data = run.node_data
    dead_name = data.get("dead_name", get_locale_text("renderer_explore.corpse_unknown_name"))
    cause = data.get("cause", get_locale_text("renderer_explore.corpse_unknown_cause"))
    cards = data.get("cards", [])
    picks_left = int(data.get("picks_left", 0))
    lines = [
        get_locale_text("renderer_explore.separator"),
        get_locale_text("renderer_explore.corpse_title", stage=p.stage),
        get_locale_text("renderer_explore.status_line", name=run.player.name, hp=p.hp, max_hp=p.max_hp, gold=p.gold),
        "",
        get_locale_text("renderer_explore.corpse_owner", name=dead_name),
        get_locale_text("renderer_explore.corpse_cause", cause=cause),
        get_locale_text("renderer_explore.corpse_gp", gp=data.get('gp', 0)),
        "",
        data.get("notice", ""),
        "",
        get_locale_text("renderer_explore.corpse_pick_prompt", picks_left=picks_left)
    ]
    from ..models.state import ensure_card_state
    for idx, card_data in enumerate(cards, 1):
        state = ensure_card_state(card_data)
        card = ALL_CARDS.get(state)
        if card:
            color_ch = "⚫" if card.color == "curse" else ("🔵" if card.color == "wizard" else "⚪")
            cost_str = get_card_cost_str(card)
            suffix = ""
            if state.upgraded:
                suffix += get_locale_text("renderer_explore.corpse_upgraded")
            if state.gems:
                suffix += get_locale_text("renderer_explore.corpse_gems", gems=",".join(state.gems))
            lines.append(get_locale_text("renderer_explore.corpse_card", idx=idx, color=color_ch, name=card.name, cost=cost_str, suffix=suffix, desc=card.desc))
    lines.append(get_locale_text("renderer_explore.reward_skip_pick", idx=len(cards) + 1))
    lines.append(get_locale_text("renderer_explore.separator"))
    lines.append(get_locale_text("renderer_explore.guide_choice"))
    lines.append(get_locale_text("renderer_explore.separator"))
    return "\n".join(lines)


def render_card_select(run: GameRun) -> str:
    p = run.player
    data = run.node_data
    title = data.get("title", get_locale_text("renderer_explore.card_select_default_title"))
    relics_str = format_relic_bar(p.relics)
    lines = [
        get_locale_text("renderer_explore.separator"),
        get_locale_text("renderer_explore.card_select_title", title=title),
        get_locale_text("renderer_explore.status_line", name=run.player.name, hp=p.hp, max_hp=p.max_hp, gold=p.gold) + relics_str,
        ""
    ]
    desc = data.get("desc")
    if desc:
        lines.append(desc)
        lines.append("")
    from ..models.state import CardState
    is_upgraded = data.get("force_upgraded", False)
    cards = data.get("cards", [])
    for idx, cid in enumerate(cards, 1):
        card = ALL_CARDS.get(CardState(id=cid, upgraded=is_upgraded))
        if card:
            color_ch = "⚫" if card.color == "curse" else ("🔵" if card.color == "wizard" else "⚪")
            cost_str = get_card_cost_str(card)
            lines.append(get_locale_text("renderer_explore.card_select_card", idx=idx, color=color_ch, name=card.name, cost=cost_str, desc=card.desc))
    skip_idx = len(cards) + 1
    can_skip = data.get("can_skip", True)
    if not can_skip:
        lines.append(get_locale_text("render_card_select_cannot_skip"))
    else:
        lines.append(get_locale_text("render_card_select_skip", skip_idx=skip_idx))
    lines.append(get_locale_text("renderer_explore.separator"))
    if p.fold_guide:
        lines.append(get_locale_text("renderer_explore.guide_folded"))
    else:
        lines.append(get_locale_text("renderer_explore.guide_choice"))
    lines.append(get_locale_text("renderer_explore.separator"))
    return "\n".join(lines)

def render_boss_chest(run: GameRun) -> str:
    p = run.player
    data = run.node_data
    title = data.get("title", get_locale_text("renderer_explore.boss_chest_default_title"))
    desc = data.get("desc", "")
    relics_str = format_relic_bar(p.relics)
    lines = [
        get_locale_text("renderer_explore.separator"),
        get_locale_text("renderer_explore.boss_chest_title", title=title),
        get_locale_text("renderer_explore.status_line", name=run.player.name, hp=p.hp, max_hp=p.max_hp, gold=p.gold) + relics_str,
        "",
        desc,
        ""
    ]
    items = data.get("items", [])
    available_items = [it for it in items if not it.get("taken")]
    for idx, it in enumerate(available_items, 1):
        prefix = ""
        if it.get("group_id"):
            prefix += get_locale_text("label_multi_choice")
        itype = it.get("type")
        id_ = it.get("id")
        if itype == "boss_relic":
            lines.append(get_locale_text("renderer_explore.boss_relic", idx=idx, prefix=prefix, name=get_relic_name(id_), desc=get_relic_desc(id_)))
        elif itype == "boss_card":
            card = ALL_CARDS.get(id_)
            if card:
                color_ch = "⚫" if card.color == "curse" else ("🔵" if card.color == "wizard" else "⚪")
                cost_str = get_card_cost_str(card)
                lines.append(get_locale_text("renderer_explore.boss_card", idx=idx, prefix=prefix, color=color_ch, name=card.name, cost=cost_str, desc=card.desc))
    lines.append(get_locale_text("renderer_explore.separator"))
    if not available_items:
        lines.append(get_locale_text("render_reward_completed"))
    else:
        lines.append(get_locale_text("render_boss_chest_exit"))
    lines.append(get_locale_text("renderer_explore.separator"))
    return "\n".join(lines)
