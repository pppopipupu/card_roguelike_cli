from ..models.state import GameRun
from ..cards import ALL_CARDS, MINION_SKILLS
from ..entities.cards.base import get_card_color_icon
from ..entities import get_relic_name, get_relic_desc
from ..data.buff_data import BUFF_CONFIG
from ..data.minion_data import MINION_CONFIG
from ..data.locale_data import t
from .menu import get_card_cost_str
from .card_preview import render_card_description, replace_structured_number
from .formatters import format_buff_detail, format_buff_list, format_relic_bar, format_relic_name_with_counter, get_effective_max_hp

def void_corrupt_text(text: str) -> str:
    import random
    chars = list(text)
    for i in range(len(chars)):
        if chars[i] not in (" ", "\n", "[", "]", "【", "】", "：", "❤️", "🛡️", "⚡", "⚔️", "A", "B", "H", "P", "G", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "|", "•", "━━━━━━━━━━━━━━━━━━━━", "格", "子", "敌", "人", "手", "牌", "抽", "弃", "消", "耗"):
            if random.random() < 0.25:
                chars[i] = random.choice(['░', '▒', '▓', '■', '?', '▰', '▱'])
    return "".join(chars)

def _find_intent_damage_value(desc: str) -> int:
    search_from = 0
    while True:
        marker = desc.find("造成", search_from)
        if marker < 0:
            return 0
        index = marker + 2
        while index < len(desc) and desc[index].isspace():
            index += 1
        start = index
        while index < len(desc) and desc[index].isdigit():
            index += 1
        if start < index:
            value = int(desc[start:index])
            cursor = index
            while cursor < len(desc) and desc[cursor].isspace():
                cursor += 1
            if cursor < len(desc) and desc[cursor] == "点":
                cursor += 1
                while cursor < len(desc) and desc[cursor].isspace():
                    cursor += 1
            if desc.startswith("伤害", cursor):
                return value
        search_from = marker + 2

def adjust_intent_desc_with_modifiers(desc: str, strength: int, weak: int, base_value: int = 0) -> str:
    if strength == 0 and weak == 0:
        return desc
    if base_value <= 0:
        base_value = _find_intent_damage_value(desc)
    if base_value <= 0:
        return desc
    adjusted = base_value + strength
    final_val = int(adjusted * 0.5) if weak > 0 else adjusted
    final_val = max(0, final_val)
    if final_val == base_value:
        return desc
    updated = replace_structured_number(desc, base_value, final_val, ("造成",), ("伤害",))
    if updated != desc:
        return updated
    return replace_structured_number(desc, base_value, final_val, ("造成",))

def render_ally_units(member) -> list[str]:
    lines = []
    for i in range(1, 7):
        key = str(i)
        if key in member.minions:
            m = member.minions[key]
            skills_desc = ""
            if m.id in MINION_SKILLS:
                skills_desc = t("renderer.battle.skill_prefix") + " ".join([f"({idx}){s['name']}" for idx, s in enumerate(MINION_SKILLS[m.id], 1)])
            buff_desc = ""
            if getattr(m, "buffs", None):
                buff_desc = t("renderer.battle.buff_prefix") + format_buff_list(m.buffs, " ")
            atk_val = m.atk + (1 if "whetstone" in member.relics else 0)
            lines.append(t("renderer.battle.minion_line", slot=i, name=m.name, hp=m.hp, max_hp=m.max_hp, atk=atk_val, actions=m.actions, bonus_actions=m.bonus_actions, attack_actions=m.attack_actions, skills=skills_desc, buffs=buff_desc))
        elif key in member.amulets:
            a = member.amulets[key]
            lines.append(t("renderer.battle.amulet_line", slot=i, name=a.name, countdown=a.countdown, desc=a.desc))
    return lines


def render_battle(run: GameRun) -> str:
    from .party import render_party_status
    p = run.player
    cur_max = get_effective_max_hp(p, run)
    relics_str = format_relic_bar(p.relics, getattr(p, "relic_counters", None))
    potions_str = ""
    if hasattr(p, "potions") and p.potions:
        from ..data.potion_data import get_potion_name
        potions_str = t("renderer.battle.potions_label") + " ".join([t("i18n_card_runtime.battle.potion_item", idx=idx, name=get_potion_name(r)) for idx, r in enumerate(p.potions, 1)])
    turn_count = run.node_data.get("turn_count", 1)
    lines = [
        t("renderer.battle.separator"),
        t("renderer.battle.title", stage=p.stage, turn=turn_count),
        t("renderer.battle.status_line", name=run.player.name, hp=p.hp, max_hp=cur_max, shield=p.shield, actions=p.actions, bonus_actions=p.bonus_actions) + relics_str + potions_str
    ]
    if getattr(run, "floor_map", None) is not None or getattr(p, "sp", 10) < getattr(p, "max_sp", 10):
        lines.append(t("i18n_grid_map.battle_sp_line", sp=getattr(p, "sp", 10), max_sp=getattr(p, "max_sp", 10)))
        lines.append(render_party_status(run))
        if p.downed or p.hp <= 0:
            lines.append(t("renderer.battle.downed"))
    if p.buffs:
        lines.append(t("renderer.battle.buff_line", name=run.player.name) + format_buff_list(p.buffs))
    lines.append("")
    lines.append(t("renderer.battle.ally_field"))
    if run.player_count() > 1:
        members = [(idx, uid, run.players[uid]) for idx, uid in enumerate(run.party_order, 1) if uid in run.players]
        if not any(member.minions or member.amulets for _, _, member in members):
            lines.append(t("renderer.battle.empty_field"))
        else:
            for idx, uid, member in members:
                marker = t("renderer_town.party_you_marker") if uid == run.user_id else (t("renderer_town.party_mercenary_marker") if getattr(member, "is_mercenary", False) else "")
                lines.append(t("renderer.battle.ally_field_member", idx=idx, name=member.name, marker=marker))
                unit_lines = render_ally_units(member)
                lines.extend(unit_lines or [t("renderer.battle.empty_field_indent")])
    elif not p.minions and not p.amulets:
        lines.append(t("renderer.battle.empty_field"))
    else:
        lines.extend(render_ally_units(p))
    lines.append("")
    lines.append(t("renderer.battle.enemy_field"))
    if not run.enemies:
        lines.append(t("renderer.battle.empty_field"))
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
                desc = adjust_intent_desc_with_modifiers(desc, strength, weak, getattr(it, "val", 0))
                if it.cost_ba > 0:
                    ba_parts.append(desc)
                else:
                    a_parts.append(desc)
            if a_parts:
                intent_parts.append(f"A: {' + '.join(a_parts)}")
            if ba_parts:
                intent_parts.append(f"BA: {' + '.join(ba_parts)}")
            intent_str = f"({', '.join(intent_parts)})" if intent_parts else t("renderer.battle.no_intent")
            shield_str = t("renderer.battle.shield_suffix", shield=enemy.shield) if enemy.shield > 0 else ""
            buff_desc = ""
            if getattr(enemy, "buffs", None):
                buff_desc = t("renderer.battle.buff_prefix") + format_buff_list(enemy.buffs, " ")
            e_name = enemy.name
            if e_name == "【万物归一】虚空之门·尤格-索托斯" or enemy.max_hp == 2147483647:
                hp_text = f"0x{enemy.hp:X}/0x{enemy.max_hp:X}"
            else:
                hp_text = f"{enemy.hp}/{enemy.max_hp}"
            if run.node_data.get("is_void_corrupted"):
                e_name = void_corrupt_text(e_name)
                intent_str = void_corrupt_text(intent_str)
            target_label = ""
            if run.player_count() > 1:
                target_uid = run.node_data.get("enemy_targets", {}).get(str(idx))
                if target_uid == "ALL":
                    target_label = t("renderer.battle.target_all")
                elif target_uid in getattr(run, "party_order", []):
                    target_label = f" | 🎯 a{run.party_order.index(target_uid) + 1}"
            lines.append(t("renderer.battle.enemy_line", slot=idx, name=e_name, hp=hp_text, shield=shield_str, buffs=buff_desc, actions=enemy.actions, bonus_actions=enemy.bonus_actions, intents=intent_str, target=target_label))
    lines.append("")
    lines.append(t("renderer.battle.hand_title"))
    if not p.hand:
        lines.append(t("renderer.battle.empty_hand"))
    else:
        valid_idx = 1
        for cid in p.hand:
            card = ALL_CARDS.get(cid)
            if card:
                color_ch = get_card_color_icon(card)
                cost_str = get_card_cost_str(card)
                rarity_map = {
                    "common": t("renderer.battle.rarity_common"),
                    "rare": t("renderer.battle.rarity_rare"),
                    "epic": t("renderer.battle.rarity_epic"),
                    "legendary": t("renderer.battle.rarity_legendary"),
                    "mythic": t("renderer.battle.rarity_mythic"),
                    "artifact": t("renderer.battle.rarity_artifact"),
                    "curse": t("renderer.battle.rarity_curse")
                }
                rname = rarity_map.get(getattr(card, "rarity", "common"), t("renderer.battle.rarity_common"))
                c_name = card.name
                c_desc = render_card_description(card, run)
                if run.node_data.get("is_void_corrupted"):
                    c_name = void_corrupt_text(c_name)
                    c_desc = void_corrupt_text(c_desc)
                    cost_str = "?A ?BA"
                else:
                    cost_str = get_card_cost_str(card)
                if getattr(card, "unplayable", False):
                    lines.append(t("renderer.battle.hand_card_unplayable", idx=valid_idx, color=color_ch, name=c_name, rarity=rname, desc=c_desc))
                else:
                    lines.append(t("renderer.battle.hand_card", idx=valid_idx, color=color_ch, name=c_name, rarity=rname, cost=cost_str, desc=c_desc))
                valid_idx += 1
    if run.node_data.get("pending_discard"):
        lines.append(t("renderer.battle.pending_discard"))
        lines.append(t("renderer.battle.separator"))
    else:
        lines.append(t("renderer.battle.separator"))
    if p.fold_guide:
        lines.append(t("renderer.battle.guide_folded"))
    else:
        lines.append(t("renderer.battle.guide_title"))
        lines.append(t("renderer.battle.guide_play"))
        lines.append(t("renderer.battle.guide_target"))
        lines.append(t("renderer.battle.guide_queue"))
        lines.append(t("renderer.battle.guide_minion"))
        lines.append(t("renderer.battle.guide_end"))
    lines.append(t("renderer.battle.separator"))
    return "\n".join(lines)

def render_detailed_battle(run: GameRun) -> str:
    p = run.player
    cur_max = get_effective_max_hp(p, run)
    turn_count = run.node_data.get("turn_count", 1)
    detailed_potions = t("renderer.battle.none")
    if hasattr(p, "potions") and p.potions:
        from ..data.potion_data import get_potion_name, get_potion_desc
        detailed_potions = " ".join([t("i18n_card_runtime.battle.detailed_potion_item", idx=idx, name=get_potion_name(r), desc=get_potion_desc(r)) for idx, r in enumerate(p.potions, 1)])
    lines = [
        t("renderer.battle.separator"),
        t("renderer.battle.detailed_title", turn=turn_count),
        "",
        t("renderer.battle.lord_title", name=run.player.name),
        t("renderer.battle.hp_line", hp=p.hp, max_hp=cur_max),
        t("renderer.battle.shield_line", shield=p.shield),
        t("renderer.battle.actions_line", actions=p.actions, bonus_actions=p.bonus_actions),
        t("renderer.battle.potions_slot", potions=detailed_potions),
        t("renderer.battle.piles_status", hand=len(p.hand), draw=len(p.draw_pile), discard=len(p.discard_pile), exhaust=len(p.exhaust_pile), minion_grave=len(p.minion_graveyard), enemy_grave=len(p.enemy_graveyard)),
    ]
    if p.relics:
        lines.append(t("renderer.battle.relics_title"))
        for r in p.relics:
            rname = format_relic_name_with_counter(r, getattr(p, "relic_counters", None))
            rdesc = get_relic_desc(r)
            lines.append(t("i18n_card_runtime.battle.detailed_relic_line", name=rname, desc=rdesc))
    else:
        lines.append(t("renderer.battle.relics_none"))
    if p.buffs:
        lines.append(t("renderer.battle.buffs_title"))
        for b in p.buffs:
            bdesc = b.desc or BUFF_CONFIG.get(b.id, {}).get("desc", t("renderer.battle.no_desc"))
            lines.append(format_buff_detail(b, bdesc))
    else:
        lines.append(t("renderer.battle.buffs_none"))
    lines.append("")
    lines.append(t("renderer.battle.detailed_ally_field"))
    if not p.minions and not p.amulets:
        lines.append(t("renderer.battle.empty_field_indent"))
    else:
        for i in range(1, 7):
            key = str(i)
            if key in p.minions:
                m = p.minions[key]
                atk_val = m.atk + (1 if "whetstone" in p.relics else 0)
                lines.append(t("renderer.battle.detailed_minion_line", slot=i, name=m.name))
                lines.append(t("renderer.battle.detailed_minion_hp", hp=m.hp, max_hp=m.max_hp))
                lines.append(t("renderer.battle.detailed_minion_atk", atk=atk_val))
                lines.append(t("renderer.battle.detailed_minion_actions", actions=m.actions, bonus_actions=m.bonus_actions, attack_actions=m.attack_actions))
                m_cfg = MINION_CONFIG.get(m.id, {})
                skills = m_cfg.get("skills", [])
                if skills:
                    lines.append(t("renderer.battle.skills_title"))
                    for idx, s in enumerate(skills, 1):
                        cost_str = ""
                        if s.get("cost_a", 0) > 0:
                            cost_str += f"{s['cost_a']}A "
                        if s.get("cost_ba", 0) > 0:
                            cost_str += f"{s['cost_ba']}BA "
                        cost_str = cost_str.strip() or t("renderer.battle.free_cost")
                        lines.append(t("renderer.battle.skill_line", idx=idx, name=s.get('name'), cost=cost_str, desc=s.get('desc')))
                else:
                    lines.append(t("renderer.battle.skills_only_basic"))
                if getattr(m, "buffs", None):
                    lines.append(t("renderer.battle.minion_buffs_title"))
                    for b in m.buffs:
                        bdesc = b.desc or BUFF_CONFIG.get(b.id, {}).get("desc", t("renderer.battle.no_desc"))
                        lines.append(format_buff_detail(b, bdesc, "      "))
            elif key in p.amulets:
                a = p.amulets[key]
                lines.append(t("renderer.battle.detailed_amulet_line", slot=i, name=a.name))
                lines.append(t("renderer.battle.amulet_countdown", countdown=a.countdown))
                lines.append(t("renderer.battle.amulet_effect", desc=a.desc))
    lines.append("")
    lines.append(t("renderer.battle.detailed_enemy_field"))
    if not run.enemies:
        lines.append(t("renderer.battle.empty_field_indent"))
    else:
        for idx, enemy in enumerate(run.enemies, 1):
            shield_str = t("renderer.battle.shield_suffix", shield=enemy.shield) if enemy.shield > 0 else ""
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
                desc = adjust_intent_desc_with_modifiers(desc, strength, weak, getattr(it, "val", 0))
                if it.cost_ba > 0:
                    ba_parts.append(desc)
                else:
                    a_parts.append(desc)
            if a_parts:
                intent_parts.append(t("renderer.battle.detailed_intent_a", descs=' + '.join(a_parts)))
            if ba_parts:
                intent_parts.append(t("renderer.battle.detailed_intent_ba", descs=' + '.join(ba_parts)))
            intent_str = " | ".join(intent_parts) if intent_parts else t("renderer.battle.no_intent")
            if e_name == "【万物归一】虚空之门·尤格-索托斯" or enemy.max_hp == 2147483647:
                hp_text = f"0x{enemy.hp:X}/0x{enemy.max_hp:X}"
            else:
                hp_text = f"{enemy.hp}/{enemy.max_hp}"
            if run.node_data.get("is_void_corrupted"):
                e_name = void_corrupt_text(e_name)
                intent_str = void_corrupt_text(intent_str)
            lines.append(t("renderer.battle.detailed_enemy_line", idx=idx, name=e_name, hp=hp_text, shield=shield_str, actions=enemy.actions, bonus_actions=enemy.bonus_actions))
            lines.append(t("renderer.battle.detailed_intent_line", intents=intent_str))
            if getattr(enemy, "buffs", None):
                lines.append(t("renderer.battle.enemy_buffs_title"))
                for b in enemy.buffs:
                    bdesc = b.desc or BUFF_CONFIG.get(b.id, {}).get("desc", t("renderer.battle.no_desc"))
                    lines.append(format_buff_detail(b, bdesc, "      "))
    lines.append(t("renderer.battle.separator"))
    return "\n".join(lines)

def render_draw_pile(run: GameRun) -> str:
    p = run.player
    lines = [
        t("renderer.battle.separator"),
        t("renderer.battle.draw_pile_title", count=len(p.draw_pile)),
        t("renderer.battle.draw_pile_desc"),
        ""
    ]
    if not p.draw_pile:
        lines.append(t("renderer.battle.draw_pile_empty"))
    else:
        counts = {}
        for cid in p.draw_pile:
            name = ALL_CARDS[cid].name if cid in ALL_CARDS else cid
            counts[name] = counts.get(name, 0) + 1
        sorted_names = sorted(counts.keys())
        for idx, name in enumerate(sorted_names, 1):
            lines.append(t("renderer.battle.pile_item", idx=idx, name=name, count=counts[name]))
    lines.append(t("renderer.battle.separator"))
    return "\n".join(lines)

def render_discard_pile(run: GameRun) -> str:
    p = run.player
    lines = [
        t("renderer.battle.separator"),
        t("renderer.battle.discard_pile_title", count=len(p.discard_pile)),
        t("renderer.battle.discard_pile_desc"),
        ""
    ]
    if not p.discard_pile:
        lines.append(t("renderer.battle.discard_pile_empty"))
    else:
        counts = {}
        for cid in p.discard_pile:
            name = ALL_CARDS[cid].name if cid in ALL_CARDS else cid
            counts[name] = counts.get(name, 0) + 1
        sorted_names = sorted(counts.keys())
        for idx, name in enumerate(sorted_names, 1):
            lines.append(t("renderer.battle.pile_item", idx=idx, name=name, count=counts[name]))
    lines.append(t("renderer.battle.separator"))
    return "\n".join(lines)

def render_exhaust_pile(run: GameRun) -> str:
    p = run.player
    lines = [
        t("renderer.battle.separator"),
        t("renderer.battle.exhaust_pile_title", count=len(p.exhaust_pile)),
        t("renderer.battle.exhaust_pile_desc"),
        ""
    ]
    if not p.exhaust_pile:
        lines.append(t("renderer.battle.exhaust_pile_empty"))
    else:
        counts = {}
        for cid in p.exhaust_pile:
            name = ALL_CARDS[cid].name if cid in ALL_CARDS else cid
            counts[name] = counts.get(name, 0) + 1
        sorted_names = sorted(counts.keys())
        for idx, name in enumerate(sorted_names, 1):
            lines.append(t("renderer.battle.pile_item", idx=idx, name=name, count=counts[name]))
    lines.append(t("renderer.battle.separator"))
    return "\n".join(lines)

def render_minion_graveyard(run: GameRun) -> str:
    p = run.player
    lines = [
        t("renderer.battle.separator"),
        t("renderer.battle.minion_graveyard_title", count=len(p.minion_graveyard)),
        t("renderer.battle.minion_graveyard_desc"),
        ""
    ]
    if not p.minion_graveyard:
        lines.append(t("renderer.battle.minion_graveyard_empty"))
    else:
        counts = {}
        for mid in p.minion_graveyard:
            name = MINION_CONFIG.get(mid, {}).get("name", mid)
            counts[name] = counts.get(name, 0) + 1
        sorted_names = sorted(counts.keys())
        for idx, name in enumerate(sorted_names, 1):
            lines.append(t("renderer.battle.pile_item", idx=idx, name=name, count=counts[name]))
    lines.append(t("renderer.battle.separator"))
    return "\n".join(lines)

def render_enemy_graveyard(run: GameRun) -> str:
    p = run.player
    lines = [
        t("renderer.battle.separator"),
        t("renderer.battle.enemy_graveyard_title", count=len(p.enemy_graveyard)),
        t("renderer.battle.enemy_graveyard_desc"),
        ""
    ]
    if not p.enemy_graveyard:
        lines.append(t("renderer.battle.enemy_graveyard_empty"))
    else:
        counts = {}
        for ename in p.enemy_graveyard:
            counts[ename] = counts.get(ename, 0) + 1
        sorted_names = sorted(counts.keys())
        for idx, name in enumerate(sorted_names, 1):
            lines.append(t("renderer.battle.pile_item", idx=idx, name=name, count=counts[name]))
    lines.append(t("renderer.battle.separator"))
    return "\n".join(lines)
