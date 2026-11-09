from ..models.state import GameRun
from ..entities import get_relic_name, get_relic_desc
from ..cards import ALL_CARDS
from .menu import get_card_cost_str
from ..data.locale_data import get_locale_text

def render_event(run: GameRun) -> str:
    p = run.player
    data = run.node_data
    relics_str = ""
    if p.relics:
        relics_str = "\n🎒 遗物：" + " ".join([f"【{get_relic_name(r)}】" for r in p.relics])
    lines = [
        "━━━━━━━━━━━━━━━━━━━━",
        f"✨ 【第 {p.stage} 关：随机事件】",
        f"{run.player.name}：❤️ HP {p.hp}/{p.max_hp} | 🪙 金币 {p.gold}" + relics_str,
        "",
        data.get("description", "发生了一个神秘的事件。"),
        "",
        "请做出你的选择："
    ]
    options = data.get("options", [])
    for idx, opt in enumerate(options, 1):
        lines.append(f" [{idx}] {opt.get('text', '')}")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    if p.fold_guide:
        lines.append("💬 提示：操作指南已折叠。输入 /rogue 折叠 可展开。")
    else:
        lines.append("💬 选择指令：/rogue c <序号>")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)

def render_shop(run: GameRun) -> str:
    from .party import render_party_status, render_waiting
    p = run.player
    data = run.node_data
    if getattr(run, "coop_id", "") and data.get("coop_done"):
        return render_waiting(run)
    relics_str = ""
    if p.relics:
        relics_str = "\n🎒 遗物：" + " ".join([f"【{get_relic_name(r)}】" for r in p.relics])
    lines = [
        "━━━━━━━━━━━━━━━━━━━━",
        f"🛒 【第 {p.stage} 关：奇妙商店】",
        f"{run.player.name}：❤️ HP {p.hp}/{p.max_hp} | 🪙 金币 {p.gold}" + relics_str,
        "",
    ]
    if getattr(run, "coop_id", ""):
        lines.append(render_party_status(run))
        lines.append("🛒 商人摊开多份货架，每名队员的货架与金币彼此独立。")
        lines.append("")
    lines.append("一位旅商展示着他的精致收藏：")
    lines.append("")
    items = data.get("items", [])
    for idx, item in enumerate(items, 1):
        itype = item.get("type")
        price = item.get("price")
        sold = item.get("sold", False)
        if sold:
            lines.append(f" [{idx}] 【已售罄】")
            continue
        if itype == "card":
            card = ALL_CARDS.get(item.get("card_id"))
            if card:
                color_ch = "⚫" if card.color == "curse" else ("🔵" if card.color == "wizard" else "⚪")
                cost_str = get_card_cost_str(card)
                lines.append(f" [{idx}] {color_ch} {card.name} (卡牌 | 消耗: {cost_str}) - 🪙 {price}金币 | {card.desc}")
        elif itype == "relic":
            rid = item.get("relic_id")
            lines.append(f" [{idx}] 🎒 {get_relic_name(rid)} (遗物) - 🪙 {price}金币 | {get_relic_desc(rid)}")
        elif itype == "gem":
            from ..data.gem_data import GEM_CONFIG
            gid = item.get("gem_id")
            g_cfg = GEM_CONFIG.get(gid, {})
            lines.append(f" [{idx}] 💎 {g_cfg.get('name', gid)} (宝石) - 🪙 {price}金币 | {g_cfg.get('desc', '')}")
        elif itype == "remove":
            lines.append(f" [{idx}] 🧹 净化服务 (移除卡组中任意一张牌) - 🪙 {price}金币")
        elif itype == "upgrade":
            lines.append(f" [{idx}] 🔨 强化服务 (将卡组中任意一张牌永久升级为带【+】的强力变体) - 🪙 {price}金币")
        elif itype == "leave":
            lines.append(f" [{idx}] 🚪 离开商店，继续冒险")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    if p.fold_guide:
        lines.append("💬 提示：操作指南已折叠。输入 /rogue 折叠 可展开。")
    else:
        lines.append("💬 购买/选择指令：/rogue c <商品序号>")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)

def render_rest(run: GameRun) -> str:
    from .party import render_party_status, render_waiting
    p = run.player
    data = run.node_data
    if getattr(run, "coop_id", "") and data.get("coop_done"):
        return render_waiting(run)
    if getattr(run, "coop_id", "") and data.get("pending_cards") is not None:
        cards = data.get("pending_cards", [])
        lines = [
            "━━━━━━━━━━━━━━━━━━━━",
            f"🔥 【第 {p.stage} 关：篝火营地 · 冥想】",
            render_party_status(run),
            "",
            "你面对篝火静静冥想，脑海中浮现出了三道奥术灵光：",
        ]
        for idx, cid in enumerate(cards, 1):
            card = ALL_CARDS.get(cid)
            lines.append(f" [{idx}] {card.name if card else cid}")
        lines.append(f" [{len(cards) + 1}] 放弃感悟")
        lines.append("━━━━━━━━━━━━━━━━━━━━")
        return "\n".join(lines)
    relics_str = ""
    if p.relics:
        relics_str = "\n🎒 遗物：" + " ".join([f"【{get_relic_name(r)}】" for r in p.relics])
    lines = [
        "━━━━━━━━━━━━━━━━━━━━",
        get_locale_text("render_rest_title", stage=p.stage),
        f"{run.player.name}：❤️ HP {p.hp}/{p.max_hp}" + relics_str,
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
            lines.append(f" [{idx}] 🩹 救治队友：指定一名队友，恢复其 30% 最大生命值并净化 1 层负面状态")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    if not available_items:
        lines.append(get_locale_text("render_rest_completed"))
    lines.append(get_locale_text("render_rest_exit"))
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)

def render_reward(run: GameRun) -> str:
    from .party import render_party_status, render_waiting
    p = run.player
    data = run.node_data
    if getattr(run, "coop_id", "") and data.get("coop_done"):
        return render_waiting(run)
    if getattr(run, "coop_id", "") and data.get("pending_cards") is not None:
        cards = data.get("pending_cards", [])
        lines = [
            "━━━━━━━━━━━━━━━━━━━━",
            "🃏 【个人卡牌三选一】",
            render_party_status(run),
            "",
            "请选择一张加入你的卡组：",
        ]
        for idx, cid in enumerate(cards, 1):
            card = ALL_CARDS.get(cid)
            lines.append(f" [{idx}] {card.name if card else cid}")
        lines.append(f" [{len(cards) + 1}] 跳过本次选卡")
        lines.append("━━━━━━━━━━━━━━━━━━━━")
        return "\n".join(lines)
    if data.get("no_reward"):
        lines = [
            "━━━━━━━━━━━━━━━━━━━━",
            "🎁 【离开遭遇战】",
            "",
            "🔮 你咏唱了【异界传送】，狼狈地穿过传送门逃离了战场。",
            "由于你半途脱逃，本场遭遇战你没有获得任何战利品与金币！",
            "",
            "━━━━━━━━━━━━━━━━━━━━",
            get_locale_text("render_reward_exit_normal"),
            "━━━━━━━━━━━━━━━━━━━━"
        ]
        return "\n".join(lines)
    quest_bonus = data.get("quest_bonus", "")
    lines = [
        "━━━━━━━━━━━━━━━━━━━━",
        get_locale_text("render_reward_title"),
        f"{run.player.name}：❤️ HP {p.hp}/{p.max_hp} | 🪙 金币 {p.gold}",
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
            lines.append(f" [{idx}] {prefix}🪙 {it.get('amount')} 金币")
        elif itype == "card_reward":
            lines.append(f" [{idx}] {prefix}🃏 卡牌奖励")
        elif itype in ("relic", "quest_relic", "boss_relic"):
            rid = it.get("relic_id") or it.get("id")
            lines.append(f" [{idx}] {prefix}🎒 {get_relic_name(rid)} (遗物) - {get_relic_desc(rid)}")
        elif itype == "gem":
            from ..data.gem_data import GEM_CONFIG
            gid = it.get("gem_id")
            g_cfg = GEM_CONFIG.get(gid, {})
            lines.append(f" [{idx}] {prefix}💎 {g_cfg.get('name', gid)} (宝石) - {g_cfg.get('desc', '')}")
        elif itype == "quest_card":
            cid = it.get("card_id")
            lines.append(f" [{idx}] {prefix}🃏 任务卡牌【{ALL_CARDS[cid].name if cid in ALL_CARDS else cid}】")
        elif itype == "potion":
            from ..data.potion_data import get_potion_name, get_potion_desc
            pid = it.get("potion_id")
            lines.append(f" [{idx}] {prefix}🧪 {get_potion_name(pid)} (药水) - {get_potion_desc(pid)}")
        elif itype == "shared_relic":
            rid = it.get("relic_id")
            lines.append(f" [{idx}] {prefix}🎒 共享遗物【{get_relic_name(rid)}】 (全队争夺，猜拳裁决)")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    if not available_items:
        lines.append(get_locale_text("render_reward_completed"))
    else:
        if has_forced:
            lines.append(get_locale_text("render_reward_exit_forced"))
        else:
            lines.append(get_locale_text("render_reward_exit_normal"))
    lines.append("━━━━━━━━━━━━━━━━━━━━")
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
        "━━━━━━━━━━━━━━━━━━━━",
        get_locale_text("render_treasure_title", stage=p.stage),
        f"{run.player.name}：❤️ HP {p.hp}/{p.max_hp} | 🪙 金币 {p.gold}",
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
                lines.append(f" [{idx}] {prefix}🪙 {it.get('amount')} 金币")
            elif itype == "card_reward":
                lines.append(f" [{idx}] {prefix}🃏 卡牌奖励")
            elif itype in ("relic", "quest_relic", "boss_relic"):
                rid = it.get("relic_id") or it.get("id")
                lines.append(f" [{idx}] {prefix}🎒 {get_relic_name(rid)} (遗物) - {get_relic_desc(rid)}")
            elif itype == "gem":
                from ..data.gem_data import GEM_CONFIG
                gid = it.get("gem_id")
                g_cfg = GEM_CONFIG.get(gid, {})
                lines.append(f" [{idx}] {prefix}💎 {g_cfg.get('name', gid)} (宝石) - {g_cfg.get('desc', '')}")
            elif itype == "shared_relic":
                rid = it.get("relic_id")
                lines.append(f" [{idx}] {prefix}🎒 共享遗物【{get_relic_name(rid)}】 (全队争夺，猜拳裁决)")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
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
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)

def render_corpse_reward(run: GameRun) -> str:
    p = run.player
    data = run.node_data
    dead_name = data.get("dead_name", "玩家")
    cause = data.get("cause", "死因不明")
    cards = data.get("cards", [])
    picks_left = int(data.get("picks_left", 0))
    lines = [
        "━━━━━━━━━━━━━━━━━━━━",
        f"💀 【第 {p.stage} 层：搜刮尸体】",
        f"{run.player.name}：❤️ HP {p.hp}/{p.max_hp} | 🪙 金币 {p.gold}",
        "",
        f"尸体主人：{dead_name}",
        f"死因：{cause}",
        f"已获得：{data.get('gp', 0)} GP",
        "",
        data.get("notice", ""),
        "",
        f"还可以挑选 {picks_left} 张卡牌（每次都可以跳过）："
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
                suffix += " [已升级]"
            if state.gems:
                suffix += f" [宝石:{','.join(state.gems)}]"
            lines.append(f" [{idx}] {color_ch} {card.name} (消耗: {cost_str}){suffix} - {card.desc}")
    lines.append(f" [{len(cards) + 1}] 跳过本次选卡")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("💬 选择指令：/rogue c <序号>")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)


def render_card_select(run: GameRun) -> str:
    p = run.player
    data = run.node_data
    title = data.get("title", "选择你的卡牌奖励")
    relics_str = ""
    if p.relics:
        relics_str = "\n🎒 遗物：" + " ".join([f"【{get_relic_name(r)}】" for r in p.relics])
    lines = [
        "━━━━━━━━━━━━━━━━━━━━",
        f"🎁 【{title}】",
        f"{run.player.name}：❤️ HP {p.hp}/{p.max_hp} | 🪙 金币 {p.gold}" + relics_str,
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
            lines.append(f" [{idx}] {color_ch} {card.name} (消耗: {cost_str}) - {card.desc}")
    skip_idx = len(cards) + 1
    can_skip = data.get("can_skip", True)
    if not can_skip:
        lines.append(get_locale_text("render_card_select_cannot_skip"))
    else:
        lines.append(get_locale_text("render_card_select_skip", skip_idx=skip_idx))
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    if p.fold_guide:
        lines.append("💬 提示：操作指南已折叠。输入 /rogue 折叠 可展开。")
    else:
        lines.append("💬 选择指令：/rogue c <序号>")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)

def render_boss_chest(run: GameRun) -> str:
    p = run.player
    data = run.node_data
    title = data.get("title", "BOSS 战利品：神话宝箱")
    desc = data.get("desc", "")
    relics_str = ""
    if p.relics:
        relics_str = "\n🎒 遗物：" + " ".join([f"【{get_relic_name(r)}】" for r in p.relics])
    lines = [
        "━━━━━━━━━━━━━━━━━━━━",
        f"🏆 【{title}】",
        f"{run.player.name}：❤️ HP {p.hp}/{p.max_hp} | 🪙 金币 {p.gold}" + relics_str,
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
            lines.append(f" [{idx}] {prefix}🎒 神话遗物【{get_relic_name(id_)}】 - {get_relic_desc(id_)}")
        elif itype == "boss_card":
            card = ALL_CARDS.get(id_)
            if card:
                color_ch = "⚫" if card.color == "curse" else ("🔵" if card.color == "wizard" else "⚪")
                cost_str = get_card_cost_str(card)
                lines.append(f" [{idx}] {prefix}{color_ch} 神话卡牌【{card.name}】 (消耗: {cost_str}) - {card.desc}")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    if not available_items:
        lines.append(get_locale_text("render_reward_completed"))
    else:
        lines.append(get_locale_text("render_boss_chest_exit"))
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)
