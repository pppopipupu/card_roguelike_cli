import re
from ..models.state import GameRun
from ..cards import ALL_CARDS, MINION_SKILLS
from ..entities import get_relic_name, get_relic_desc
from ..data.buff_data import BUFF_CONFIG
from ..data.minion_data import MINION_CONFIG
from .menu import get_card_cost_str
from .card_preview import render_card_description

def void_corrupt_text(text: str) -> str:
    import random
    chars = list(text)
    for i in range(len(chars)):
        if chars[i] not in (" ", "\n", "[", "]", "【", "】", "：", "❤️", "🛡️", "⚡", "⚔️", "A", "B", "H", "P", "G", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "|", "•", "━━━━━━━━━━━━━━━━━━━━", "格", "子", "敌", "人", "手", "牌", "抽", "弃", "消", "耗"):
            if random.random() < 0.25:
                chars[i] = random.choice(['░', '▒', '▓', '■', '?', '▰', '▱'])
    return "".join(chars)

def adjust_intent_desc_with_modifiers(desc: str, strength: int, weak: int) -> str:
    if strength == 0 and weak == 0:
        return desc
    def repl(match):
        prefix = match.group(1)
        val = int(match.group(2))
        suffix = match.group(3)
        base = val + strength
        final_val = int(base * 0.5) if weak > 0 else base
        final_val = max(0, final_val)
        return f"{prefix}{final_val}{suffix}"
    pattern = r"(造成\s*)(\d+)(\s*(?:点)?伤害)"
    return re.sub(pattern, repl, desc)

def render_battle(run: GameRun) -> str:
    from .party import render_party_status
    p = run.player
    will_buff = next((b for b in p.buffs if b.id == "iron_will"), None)
    will_stacks = will_buff.stacks if will_buff else 0
    cur_max = p.max_hp + will_stacks * 10
    relics_str = ""
    if p.relics:
        relics_str = "\n🎒 遗物：" + " ".join([f"【{get_relic_name(r)}】" for r in p.relics])
    potions_str = ""
    if hasattr(p, "potions") and p.potions:
        from ..data.potion_data import get_potion_name
        potions_str = "\n🧪 药水：" + " ".join([f"[{idx}]【{get_potion_name(r)}】" for idx, r in enumerate(p.potions, 1)])
    turn_count = run.node_data.get("turn_count", 1)
    lines = [
        "━━━━━━━━━━━━━━━━━━━━",
        f"⚔️ 【第 {p.stage} 关：战斗阶段 (第 {turn_count} 回合)】",
        f"{run.player.name}：❤️ HP {p.hp}/{cur_max} | 🛡️ 护盾 {p.shield} | ⚡ 动作 {p.actions}A {p.bonus_actions}BA" + relics_str + potions_str
    ]
    if getattr(run, "coop_id", ""):
        lines.append(render_party_status(run))
        if p.downed or p.hp <= 0:
            lines.append("💀 你已倒地，无法行动，正在观战。")
    if p.buffs:
        buff_strs = []
        for b in p.buffs:
            if getattr(b, "stacks2", None) is not None and b.stacks2 > 0:
                buff_strs.append(f"{b.name}({b.stacks},{b.stacks2})")
            elif b.stacks > 1:
                buff_strs.append(f"{b.name} x{b.stacks}")
            else:
                buff_strs.append(f"{b.name}")
        lines.append(f"{run.player.name} Buff：" + " | ".join(buff_strs))
    lines.append("")
    lines.append("【我方战场】")
    if not p.minions and not p.amulets:
        lines.append("（空无一物）")
    else:
        for i in range(1, 7):
            key = str(i)
            if key in p.minions:
                m = p.minions[key]
                skills_desc = ""
                if m.id in MINION_SKILLS:
                    skills_desc = " | 技能: " + " ".join([f"({idx}){s['name']}" for idx, s in enumerate(MINION_SKILLS[m.id], 1)])
                buff_desc = ""
                if getattr(m, "buffs", None):
                    minion_buff_strs = []
                    for b in m.buffs:
                        if getattr(b, "stacks2", None) is not None and b.stacks2 > 0:
                            minion_buff_strs.append(f"{b.name}({b.stacks},{b.stacks2})")
                        elif b.stacks > 1:
                            minion_buff_strs.append(f"{b.name} x{b.stacks}")
                        else:
                            minion_buff_strs.append(f"{b.name}")
                    buff_desc = " | Buff: " + " ".join(minion_buff_strs)
                atk_val = m.atk + (1 if "whetstone" in p.relics else 0)
                lines.append(f" 格子 [{i}] 随从：{m.name} (❤️ HP {m.hp}/{m.max_hp} | ⚔️ 攻击 {atk_val} | ⚡ 动作 {m.actions}A {m.bonus_actions}BA {m.attack_actions}AA{skills_desc}{buff_desc})")
            elif key in p.amulets:
                a = p.amulets[key]
                lines.append(f" 格子 [{i}] 护符：{a.name} (⏳ 吟唱 {a.countdown}) - {a.desc}")
    lines.append("")
    lines.append("【敌方战场】")
    if not run.enemies:
        lines.append("（空无一物）")
    else:
        for idx, enemy in enumerate(run.enemies, 1):
            strength = 0
            weak = 0
            if getattr(enemy, "buffs", None):
                for b in enemy.buffs:
                    if b.id == "strength":
                        strength += b.stacks
                    elif b.id == "weak":
                        weak += b.stacks
            intent_parts = []
            a_parts = []
            ba_parts = []
            for it in getattr(enemy, "intents", []):
                desc = it.cancelled_desc if it.cancelled else it.desc
                if not desc:
                    continue
                desc = adjust_intent_desc_with_modifiers(desc, strength, weak)
                if it.cost_ba > 0:
                    ba_parts.append(desc)
                else:
                    a_parts.append(desc)
            if a_parts:
                intent_parts.append(f"A: {' + '.join(a_parts)}")
            if ba_parts:
                intent_parts.append(f"BA: {' + '.join(ba_parts)}")
            intent_str = f"({', '.join(intent_parts)})" if intent_parts else "无意图"
            shield_str = f" | 🛡️ 护盾 {enemy.shield}" if enemy.shield > 0 else ""
            buff_desc = ""
            if getattr(enemy, "buffs", None):
                enemy_buff_strs = []
                for b in enemy.buffs:
                    if getattr(b, "stacks2", None) is not None and b.stacks2 > 0:
                        enemy_buff_strs.append(f"{b.name}({b.stacks},{b.stacks2})")
                    elif b.stacks > 1:
                        enemy_buff_strs.append(f"{b.name} x{b.stacks}")
                    else:
                        enemy_buff_strs.append(f"{b.name}")
                buff_desc = " | Buff: " + " ".join(enemy_buff_strs)
            e_name = enemy.name
            if e_name == "【万物归一】虚空之门·尤格-索托斯" or enemy.max_hp == 2147483647:
                hp_text = f"0x{enemy.hp:X}/0x{enemy.max_hp:X}"
            else:
                hp_text = f"{enemy.hp}/{enemy.max_hp}"
            if run.node_data.get("is_void_corrupted"):
                e_name = void_corrupt_text(e_name)
                intent_str = void_corrupt_text(intent_str)
            target_label = ""
            if getattr(run, "coop_id", ""):
                target_uid = run.node_data.get("enemy_targets", {}).get(str(idx))
                if target_uid == "ALL":
                    target_label = " | 🎯 全体"
                elif target_uid in getattr(run, "party_order", []):
                    target_label = f" | 🎯 a{run.party_order.index(target_uid) + 1}"
            lines.append(f" 格子 [{idx}] 敌人：{e_name} (❤️ HP {hp_text}{shield_str}{buff_desc} | ⚡ 动作 {enemy.actions}A {enemy.bonus_actions}BA | ⚔️ 意图：{intent_str}{target_label})")
    lines.append("")
    lines.append("【你的手牌】")
    if not p.hand:
        lines.append("（空空如也）")
    else:
        valid_idx = 1
        for cid in p.hand:
            card = ALL_CARDS.get(cid)
            if card:
                color_ch = "⚫" if card.color == "curse" else ("🔴" if card.color == "warrior" else ("🔵" if card.color == "wizard" else "⚪"))
                cost_str = get_card_cost_str(card)
                rarity_map = {
                    "common": "普通",
                    "rare": "稀有",
                    "epic": "珍奇",
                    "legendary": "传奇",
                    "mythic": "神话",
                    "artifact": "神器",
                    "curse": "诅咒"
                }
                rname = rarity_map.get(getattr(card, "rarity", "common"), "普通")
                c_name = card.name
                c_desc = render_card_description(card, run)
                if run.node_data.get("is_void_corrupted"):
                    c_name = void_corrupt_text(c_name)
                    c_desc = void_corrupt_text(c_desc)
                    cost_str = "?A ?BA"
                else:
                    cost_str = get_card_cost_str(card)
                if getattr(card, "unplayable", False):
                    lines.append(f" [{valid_idx}] {color_ch} {c_name} <{rname}> - {c_desc}")
                else:
                    lines.append(f" [{valid_idx}] {color_ch} {c_name} <{rname}> (消耗: {cost_str}) - {c_desc}")
                valid_idx += 1
    if run.node_data.get("pending_discard"):
        lines.append("⚠️ 状态：请选择一张手牌丢弃！请输入：/rogue 选择 <手牌序号>")
        lines.append("━━━━━━━━━━━━━━━━━━━━")
    else:
        lines.append("━━━━━━━━━━━━━━━━━━━━")
    if p.fold_guide:
        lines.append("💬 提示：操作指南已折叠。输入 /rogue 折叠 可展开。")
    else:
        lines.append("💬 战斗指令指南：")
        lines.append("• 使用卡牌：/rogue p <手牌序号|拼音首字母> [目标]")
        lines.append("• 指向目标：敌方 e1-eN (对应敌方格子) | 我方 p0-p6 (p0为自己，p1-p6为随从)")
        lines.append("• 队列打牌：/rogue q [p 1, p 2:e1, p 3]")
        lines.append("• 随从指令：/rogue m <我方格子> a/s <目标格子/技能序号> [技能目标]")
        lines.append("• 结束回合：/rogue e")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)

def render_detailed_battle(run: GameRun) -> str:
    p = run.player
    will_buff = next((b for b in p.buffs if b.id == "iron_will"), None)
    will_stacks = will_buff.stacks if will_buff else 0
    cur_max = p.max_hp + will_stacks * 10
    turn_count = run.node_data.get("turn_count", 1)
    detailed_potions = "无"
    if hasattr(p, "potions") and p.potions:
        from ..data.potion_data import get_potion_name, get_potion_desc
        detailed_potions = " ".join([f"[{idx}]【{get_potion_name(r)}】({get_potion_desc(r)})" for idx, r in enumerate(p.potions, 1)])
    lines = [
        "━━━━━━━━━━━━━━━━━━━━",
        f"⚔️ 【实时战斗详细情报 (第 {turn_count} 回合)】",
        "",
        f"👤 【{run.player.name}领主】",
        f"  生命值：HP {p.hp}/{cur_max}",
        f"  护盾值：{p.shield}",
        f"  动作资源：{p.actions}A {p.bonus_actions}BA",
        f"  药水槽：{detailed_potions}",
        f"  牌堆状态：手牌 {len(p.hand)}张 | 抽牌堆 {len(p.draw_pile)}张 | 弃牌堆 {len(p.discard_pile)}张 | 消耗堆 {len(p.exhaust_pile)}张 | 随从墓地 {len(p.minion_graveyard)}个 | 敌人墓地 {len(p.enemy_graveyard)}个",
    ]
    if p.relics:
        lines.append("  拥有遗物：")
        for r in p.relics:
            rname = get_relic_name(r)
            rdesc = get_relic_desc(r)
            lines.append(f"    • 【{rname}】: {rdesc}")
    else:
        lines.append("  拥有遗物：无")
    if p.buffs:
        lines.append("  当前Buff状态：")
        for b in p.buffs:
            bdesc = b.desc or BUFF_CONFIG.get(b.id, {}).get("desc", "无具体描述")
            if getattr(b, "stacks2", None) is not None and b.stacks2 > 0:
                lines.append(f"    • 【{b.name}】(层数: {b.stacks}, 持续: {b.stacks2}): {bdesc}")
            else:
                lines.append(f"    • 【{b.name}】(层数: {b.stacks}): {bdesc}")
    else:
        lines.append("  当前Buff状态：无")
    lines.append("")
    lines.append("🦁 【我方战场】")
    if not p.minions and not p.amulets:
        lines.append("  （空无一物）")
    else:
        for i in range(1, 7):
            key = str(i)
            if key in p.minions:
                m = p.minions[key]
                atk_val = m.atk + (1 if "whetstone" in p.relics else 0)
                lines.append(f"  格子 [{i}] 随从：{m.name}")
                lines.append(f"    生命值：HP {m.hp}/{m.max_hp}")
                lines.append(f"    攻击力：⚔️ {atk_val}")
                lines.append(f"    剩余动作：{m.actions}A {m.bonus_actions}BA {m.attack_actions}AA")
                m_cfg = MINION_CONFIG.get(m.id, {})
                skills = m_cfg.get("skills", [])
                if skills:
                    lines.append("    技能列表：")
                    for idx, s in enumerate(skills, 1):
                        cost_str = ""
                        if s.get("cost_a", 0) > 0:
                            cost_str += f"{s['cost_a']}A "
                        if s.get("cost_ba", 0) > 0:
                            cost_str += f"{s['cost_ba']}BA "
                        cost_str = cost_str.strip() or "免费"
                        lines.append(f"      ({idx}) 【{s.get('name')}】(消耗: {cost_str}) - {s.get('desc')}")
                else:
                    lines.append("    技能列表：仅有普通攻击 (消耗 1A)")
                if getattr(m, "buffs", None):
                    lines.append("    随从Buff：")
                    for b in m.buffs:
                        bdesc = b.desc or BUFF_CONFIG.get(b.id, {}).get("desc", "无具体描述")
                        if getattr(b, "stacks2", None) is not None and b.stacks2 > 0:
                            lines.append(f"      • 【{b.name}】(层数: {b.stacks}, 持续: {b.stacks2}): {bdesc}")
                        else:
                            lines.append(f"      • 【{b.name}】(层数: {b.stacks}): {bdesc}")
            elif key in p.amulets:
                a = p.amulets[key]
                lines.append(f"  格子 [{i}] 护符：{a.name}")
                lines.append(f"    吟唱时间：⏳ 剩余 {a.countdown} 回合")
                lines.append(f"    效果：{a.desc}")
    lines.append("")
    lines.append("👿 【敌方战场】")
    if not run.enemies:
        lines.append("  （空无一物）")
    else:
        for idx, enemy in enumerate(run.enemies, 1):
            shield_str = f" | 🛡️ 护盾 {enemy.shield}" if enemy.shield > 0 else ""
            e_name = enemy.name
            strength = 0
            weak = 0
            if getattr(enemy, "buffs", None):
                for b in enemy.buffs:
                    if b.id == "strength":
                        strength += b.stacks
                    elif b.id == "weak":
                        weak += b.stacks
            intent_parts = []
            a_parts = []
            ba_parts = []
            for it in getattr(enemy, "intents", []):
                desc = it.cancelled_desc if it.cancelled else it.desc
                if not desc:
                    continue
                desc = adjust_intent_desc_with_modifiers(desc, strength, weak)
                if it.cost_ba > 0:
                    ba_parts.append(desc)
                else:
                    a_parts.append(desc)
            if a_parts:
                intent_parts.append(f"动作(A)：{' + '.join(a_parts)}")
            if ba_parts:
                intent_parts.append(f"附赠动作(BA)：{' + '.join(ba_parts)}")
            intent_str = " | ".join(intent_parts) if intent_parts else "无意图"
            if e_name == "【万物归一】虚空之门·尤格-索托斯" or enemy.max_hp == 2147483647:
                hp_text = f"0x{enemy.hp:X}/0x{enemy.max_hp:X}"
            else:
                hp_text = f"{enemy.hp}/{enemy.max_hp}"
            if run.node_data.get("is_void_corrupted"):
                e_name = void_corrupt_text(e_name)
                intent_str = void_corrupt_text(intent_str)
            lines.append(f"  格子 [{idx}] 敌人：{e_name} (HP {hp_text}{shield_str} | 动作 {enemy.actions}A {enemy.bonus_actions}BA)")
            lines.append(f"    行动意图：{intent_str}")
            if getattr(enemy, "buffs", None):
                lines.append("    敌人Buff：")
                for b in enemy.buffs:
                    bdesc = b.desc or BUFF_CONFIG.get(b.id, {}).get("desc", "无具体描述")
                    if getattr(b, "stacks2", None) is not None and b.stacks2 > 0:
                        lines.append(f"      • 【{b.name}】(层数: {b.stacks}, 持续: {b.stacks2}): {bdesc}")
                    else:
                        lines.append(f"      • 【{b.name}】(层数: {b.stacks}): {bdesc}")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)

def render_draw_pile(run: GameRun) -> str:
    p = run.player
    lines = [
        "━━━━━━━━━━━━━━━━━━━━",
        f"🔮 【抽牌堆卡牌列表】 (共 {len(p.draw_pile)} 张)",
        "当前抽牌堆内还包含以下卡牌（已去重并排序）：",
        ""
    ]
    if not p.draw_pile:
        lines.append("  （当前抽牌堆为空）")
    else:
        counts = {}
        for cid in p.draw_pile:
            name = ALL_CARDS[cid].name if cid in ALL_CARDS else cid
            counts[name] = counts.get(name, 0) + 1
        sorted_names = sorted(counts.keys())
        for idx, name in enumerate(sorted_names, 1):
            lines.append(f"  {idx}. 【{name}】 x{counts[name]}")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)

def render_discard_pile(run: GameRun) -> str:
    p = run.player
    lines = [
        "━━━━━━━━━━━━━━━━━━━━",
        f"🗑️ 【弃牌堆卡牌列表】 (共 {len(p.discard_pile)} 张)",
        "当前弃牌堆内包含以下卡牌（已去重并排序）：",
        ""
    ]
    if not p.discard_pile:
        lines.append("  （当前弃牌堆为空）")
    else:
        counts = {}
        for cid in p.discard_pile:
            name = ALL_CARDS[cid].name if cid in ALL_CARDS else cid
            counts[name] = counts.get(name, 0) + 1
        sorted_names = sorted(counts.keys())
        for idx, name in enumerate(sorted_names, 1):
            lines.append(f"  {idx}. 【{name}】 x{counts[name]}")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)

def render_exhaust_pile(run: GameRun) -> str:
    p = run.player
    lines = [
        "━━━━━━━━━━━━━━━━━━━━",
        f"🔥 【消耗堆卡牌列表】 (共 {len(p.exhaust_pile)} 张)",
        "当前已被消耗的卡牌（已去重并排序）：",
        ""
    ]
    if not p.exhaust_pile:
        lines.append("  （当前消耗堆为空）")
    else:
        counts = {}
        for cid in p.exhaust_pile:
            name = ALL_CARDS[cid].name if cid in ALL_CARDS else cid
            counts[name] = counts.get(name, 0) + 1
        sorted_names = sorted(counts.keys())
        for idx, name in enumerate(sorted_names, 1):
            lines.append(f"  {idx}. 【{name}】 x{counts[name]}")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)

def render_minion_graveyard(run: GameRun) -> str:
    p = run.player
    lines = [
        "━━━━━━━━━━━━━━━━━━━━",
        f"🦁 【我方随从墓地】 (共 {len(p.minion_graveyard)} 个已阵亡随从)",
        "我方本场战斗中已阵亡的随从（已去重并排序）：",
        ""
    ]
    if not p.minion_graveyard:
        lines.append("  （我方当前暂无阵亡随从）")
    else:
        counts = {}
        for mid in p.minion_graveyard:
            name = MINION_CONFIG.get(mid, {}).get("name", mid)
            counts[name] = counts.get(name, 0) + 1
        sorted_names = sorted(counts.keys())
        for idx, name in enumerate(sorted_names, 1):
            lines.append(f"  {idx}. 【{name}】 x{counts[name]}")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)

def render_enemy_graveyard(run: GameRun) -> str:
    p = run.player
    lines = [
        "━━━━━━━━━━━━━━━━━━━━",
        f"💀 【敌方亡灵墓地】 (共 {len(p.enemy_graveyard)} 个已消灭敌人)",
        "敌方本场战斗中已被消灭的单位（已去重并排序）：",
        ""
    ]
    if not p.enemy_graveyard:
        lines.append("  （敌方当前暂无消灭单位）")
    else:
        counts = {}
        for ename in p.enemy_graveyard:
            counts[ename] = counts.get(ename, 0) + 1
        sorted_names = sorted(counts.keys())
        for idx, name in enumerate(sorted_names, 1):
            lines.append(f"  {idx}. 【{name}】 x{counts[name]}")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)
