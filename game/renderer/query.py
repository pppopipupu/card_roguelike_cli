from ..data.relic_data import RELIC_CONFIG
from ..data.buff_data import BUFF_CONFIG
from ..data.minion_data import MINION_CONFIG
from ..data.card_data import CARD_CONFIG
from ..data.enemy_data import ENEMY_CONFIG
from ..data.keyword_data import KEYWORD_CONFIG
from ..data.gem_data import GEM_CONFIG
from ..data.amulet_data import AMULET_CONFIG
from ..data.potion_data import POTION_CONFIG
from .menu import get_card_cost_str, append_card_subtype
from ..data.locale_data import get_locale_text

def render_query_info(query_str: str, user_id: str | None = None, run=None) -> str:
    from ..models.manager import SaveManager
    boss_cfg = SaveManager().load_admin_config()
    icerainboww_enabled = boss_cfg.get("icerainboww_enabled", True)
    
    stats = SaveManager().load_stats(user_id) if user_id else None
    killed_yog = bool(stats and getattr(stats, "yog_sothoth_kill_count", 0) > 0)
    
    query_str_lower = query_str.strip().lower()
    if not query_str_lower:
        return get_locale_text("renderer_menu.query_empty")
        
    rarity_map = {
        "common": get_locale_text("renderer_menu.rarity_common"),
        "rare": get_locale_text("renderer_menu.rarity_rare"),
        "epic": get_locale_text("renderer_menu.rarity_epic"),
        "legendary": get_locale_text("renderer_menu.rarity_legendary"),
        "mythic": get_locale_text("renderer_menu.rarity_mythic"),
        "artifact": get_locale_text("renderer_menu.rarity_artifact"),
        "curse": get_locale_text("renderer_menu.rarity_curse")
    }
    
    def get_rarity_key(val: str) -> str | None:
        val = val.strip().lower()
        if val in rarity_map:
            return val
        for k, v in rarity_map.items():
            if val == v:
                return k
        return None

    q_search = query_str_lower
    tier_filter = None

    import re
    m = re.search(r"\s+tier\s+(.+)$", query_str_lower)
    if m:
        tier_str = m.group(1).strip()
        tier_filter = get_rarity_key(tier_str)
        if not tier_filter:
            return get_locale_text("renderer_menu.query_invalid_tier")
        q_search = query_str_lower[:m.start()].strip()
    else:
        r_key = get_rarity_key(query_str_lower)
        if r_key is not None:
            tier_filter = r_key
            q_search = ""

    lines = [get_locale_text("renderer_menu.separator"), get_locale_text("renderer_menu.query_result", query=query_str), ""]
    found = False
    
    if not tier_filter and q_search in ("potion", "potions", "药水", "药水一览"):
        found = True
        lines.append(get_locale_text("renderer_menu.potions_all_title"))
        for pid, cfg in POTION_CONFIG.items():
            pname = cfg.get("name", pid)
            rarity = cfg.get("rarity", "common")
            prarity_ch = rarity_map.get(rarity, rarity)
            lines.append(get_locale_text("renderer_menu.potion_all_line", name=pname, rarity=prarity_ch, drink=cfg.get('drink_desc', ''), throw=cfg.get('throw_desc', '')))
        lines.append("")

    for pid, cfg in POTION_CONFIG.items():
        if tier_filter and cfg.get("rarity", "common").lower() != tier_filter:
            continue
        match_keyword = (not q_search) or (q_search == pid.lower()) or (q_search in cfg.get("name", "").lower())
        if match_keyword:
            found = True
            pname = cfg.get("name", pid)
            rarity = cfg.get("rarity", "common")
            prarity_ch = rarity_map.get(rarity, rarity)
            lines.append(get_locale_text("renderer_menu.potion_title", name=pname, id=pid, rarity=prarity_ch))
            lines.append(get_locale_text("renderer_menu.potion_drink_line", drink=cfg.get('drink_desc', '')))
            lines.append(get_locale_text("renderer_menu.potion_throw_line", throw=cfg.get('throw_desc', '')))
            lines.append("")
            
    if not tier_filter and q_search in ("buff", "buffs", "状态", "战斗效果", "效果"):
        found = True
        lines.append(get_locale_text("renderer_menu.buffs_all_title"))
        for bid, cfg in BUFF_CONFIG.items():
            bname = cfg.get("name", bid)
            desc = cfg.get("desc", "")
            lines.append(get_locale_text("renderer_menu.buff_all_line", name=bname, desc=desc))
        lines.append("")
        
    if not tier_filter and q_search in ("keyword", "keywords", "词条", "机制"):
        found = True
        lines.append(get_locale_text("renderer_menu.keywords_all_title"))
        for kid, cfg in KEYWORD_CONFIG.items():
            kname = cfg.get("name", kid)
            desc = cfg.get("desc", "")
            lines.append(get_locale_text("renderer_menu.keywords_all_line", name=kname, desc=desc))
        lines.append("")

    if not tier_filter and q_search in ("gem", "gems", "宝石", "宝石一览"):
        found = True
        lines.append(get_locale_text("renderer_menu.gems_all_title"))
        for gid, cfg in GEM_CONFIG.items():
            gname = cfg.get("name", gid)
            rarity = cfg.get("rarity", "common")
            grarity_ch = rarity_map.get(rarity, rarity)
            desc = cfg.get("desc", "")
            price = cfg.get("price", 0)
            lines.append(get_locale_text("renderer_menu.gem_all_line", name=gname, rarity=grarity_ch, desc=desc, price=price))
        lines.append("")

    if not tier_filter:
        from ..data.damage_type_data import DAMAGE_TYPE_QUERY_ENTRIES
        for dtype, dtype_cfg in DAMAGE_TYPE_QUERY_ENTRIES.items():
            dtype_name = get_locale_text(dtype_cfg["name_key"])
            aliases = dtype_cfg.get("aliases", ())
            if q_search == dtype.lower() or q_search == dtype_name.lower() or any(q_search == alias.lower() for alias in aliases):
                found = True
                lines.append(get_locale_text("renderer_menu.damage_type_title", name=dtype_name, id=dtype))
                category_id = dtype_cfg.get("category")
                if category_id:
                    category_name = get_locale_text(DAMAGE_TYPE_QUERY_ENTRIES[category_id]["name_key"])
                    lines.append(get_locale_text("renderer_menu.damage_type_category_line", category=category_name))
                desc_key = dtype_cfg.get("desc_key")
                if desc_key:
                    lines.append(get_locale_text("renderer_menu.desc_line", desc=get_locale_text(desc_key)))
                members = dtype_cfg.get("members")
                if members:
                    member_names = [get_locale_text(DAMAGE_TYPE_QUERY_ENTRIES[member]["name_key"]) for member in members]
                    lines.append(get_locale_text("renderer_menu.damage_type_members_line", members="、".join(member_names)))
                lines.append("")

    for rid, cfg in RELIC_CONFIG.items():
        if tier_filter and cfg.get("rarity", "common").lower() != tier_filter:
            continue
        match_keyword = (not q_search) or (q_search == rid.lower()) or (q_search in cfg.get("name", "").lower())
        if match_keyword:
            found = True
            rname = cfg.get("name", rid)
            rarity = cfg.get("rarity", "common")
            rname_rarity = rarity_map.get(rarity, rarity)
            desc = cfg.get("desc", "")
            price = cfg.get("price", 0)
            lines.append(get_locale_text("renderer_menu.relic_detail_title", name=rname, id=rid, rarity=rname_rarity))
            lines.append(get_locale_text("renderer_menu.effect_line", desc=desc))
            lines.append(get_locale_text("renderer_menu.price_line", price=price))
            lines.append("")
            
    for bid, cfg in BUFF_CONFIG.items():
        if tier_filter:
            continue
        if q_search == bid.lower() or q_search in cfg.get("name", "").lower():
            found = True
            bname = cfg.get("name", bid)
            desc = cfg.get("desc", "")
            lines.append(get_locale_text("renderer_menu.buff_detail_title", name=bname, id=bid))
            lines.append(get_locale_text("renderer_menu.desc_line", desc=desc))
            lines.append("")
            
    for kid, cfg in KEYWORD_CONFIG.items():
        if tier_filter:
            continue
        if q_search == kid.lower() or q_search in cfg.get("name", "").lower():
            found = True
            kname = cfg.get("name", kid)
            desc = cfg.get("desc", "")
            lines.append(get_locale_text("renderer_menu.keyword_detail_title", name=kname, id=kid))
            lines.append(get_locale_text("renderer_menu.desc_line", desc=desc))
            lines.append("")

    for gid, cfg in GEM_CONFIG.items():
        if tier_filter and cfg.get("rarity", "common").lower() != tier_filter:
            continue
        match_keyword = (not q_search) or (q_search == gid.lower()) or (q_search in cfg.get("name", "").lower()) or (q_search in cfg.get("desc", "").lower())
        if match_keyword:
            found = True
            gname = cfg.get("name", gid)
            rarity = cfg.get("rarity", "common")
            grarity_ch = rarity_map.get(rarity, rarity)
            desc = cfg.get("desc", "")
            price = cfg.get("price", 0)
            lines.append(get_locale_text("renderer_menu.gem_detail_title", name=gname, id=gid, rarity=grarity_ch))
            lines.append(get_locale_text("renderer_menu.effect_line", desc=desc))
            lines.append(get_locale_text("renderer_menu.price_line", price=price))
            lines.append("")
            
    for mid, cfg in MINION_CONFIG.items():
        if tier_filter:
            continue
        if not icerainboww_enabled and (mid == "minion_icerainboww" or mid == "minion_icerainboww+" or "icerainboww" in mid.lower() or "icerainboww" in cfg.get("name", "").lower()):
            continue
        if q_search == mid.lower() or q_search in cfg.get("name", "").lower():
            found = True
            mname = cfg.get("name", mid)
            lines.append(get_locale_text("renderer_menu.minion_title", name=mname, id=mid))
            card_cfg = CARD_CONFIG.get(mid)
            if card_cfg:
                hp = card_cfg.get("minion_hp", 0)
                atk = card_cfg.get("minion_atk", 0)
                lines.append(get_locale_text("renderer_menu.minion_stats_line", hp=hp, atk=atk))
            skills = cfg.get("skills", [])
            if skills:
                lines.append(get_locale_text("renderer_menu.skills_title"))
                for s in skills:
                    cost_str = ""
                    if s.get("cost_a", 0) > 0:
                        cost_str += f"{s['cost_a']}A "
                    if s.get("cost_ba", 0) > 0:
                        cost_str += f"{s['cost_ba']}BA "
                    cost_str = cost_str.strip() or get_locale_text("renderer_menu.free_cost")
                    lines.append(get_locale_text("renderer_menu.skill_line", name=s.get('name'), cost=cost_str, desc=s.get('desc')))
            else:
                lines.append(get_locale_text("renderer_menu.skills_basic"))
            lines.append("")
            
    for cid, cfg in CARD_CONFIG.items():
        if not icerainboww_enabled and (cid == "minion_icerainboww" or cid == "minion_icerainboww+" or "icerainboww" in cid.lower() or "icerainboww" in cfg.get("name", "").lower()):
            continue
        if tier_filter and cfg.get("rarity", "common").lower() != tier_filter:
            continue
        q_clean = q_search[:-1] if q_search.endswith("+") else q_search
        match_keyword = (not q_clean) or (q_clean == cid.lower()) or (q_clean == cfg.get("name", "").lower()) or (q_clean in cid.lower()) or (q_clean in cfg.get("name", "").lower())
        if match_keyword:
            found = True
            cname = cfg.get("name", cid)
            ctype = cfg.get("type", "")
            type_map = {
                "spell": get_locale_text("renderer_menu.type_spell"),
                "amulet": get_locale_text("renderer_menu.type_amulet_generic"),
                "ability": get_locale_text("renderer_menu.type_ability"),
                "minion": get_locale_text("renderer_menu.type_minion")
            }
            ctype_ch = append_card_subtype(type_map.get(ctype, ctype), cid, ctype)
            rarity = cfg.get("rarity", "common")
            rname_rarity = rarity_map.get(rarity, rarity)
            from ..cards import ALL_CARDS
            card_obj = ALL_CARDS.get(cid)
            cost_str = get_card_cost_str(card_obj) if card_obj else get_locale_text("renderer_menu.free_cost")
            desc = cfg.get("desc", "")
            if cid == "neutral_button_magic" and not killed_yog:
                desc = get_locale_text("renderer_menu.card_hidden_desc")
            lines.append(get_locale_text("renderer_menu.card_title", name=cname, id=cid, type_ch=ctype_ch, rarity=rname_rarity))
            lines.append(get_locale_text("renderer_menu.cost_line", cost=cost_str))
            lines.append(get_locale_text("renderer_menu.effect_line", desc=desc))
            lines.append("")
            
            from ..data.card_upgrade_data import CARD_UPGRADE_CONFIG
            if cid in CARD_UPGRADE_CONFIG:
                up_card = ALL_CARDS.get(cid + "+")
                if up_card:
                    up_cost_str = get_card_cost_str(up_card)
                    up_desc = up_card.desc
                    if cid == "neutral_button_magic" and not killed_yog:
                        up_desc = get_locale_text("renderer_menu.card_hidden_desc")
                    lines.append(get_locale_text("renderer_menu.card_upgrade_title", name=up_card.name, id=cid, type_ch=ctype_ch, rarity=rname_rarity))
                    lines.append(get_locale_text("renderer_menu.upgrade_cost_line", cost=up_cost_str))
                    lines.append(get_locale_text("renderer_menu.upgrade_effect_line", desc=up_desc))
                    lines.append("")
                    
    for aid, cfg in AMULET_CONFIG.items():
        if tier_filter:
            continue
        q_clean = q_search[:-1] if q_search.endswith("+") else q_search
        match_keyword = (not q_clean) or (q_clean == aid.lower()) or (q_clean == cfg.get("name", "").lower()) or (q_clean in aid.lower()) or (q_clean in cfg.get("name", "").lower())
        if match_keyword:
            found = True
            aname = cfg.get("name", aid)
            desc = cfg.get("desc", "")
            cd = cfg.get("countdown", 1)
            lines.append(get_locale_text("renderer_menu.amulet_title", name=aname, id=aid))
            lines.append(get_locale_text("renderer_menu.amulet_countdown_line", countdown=cd))
            lines.append(get_locale_text("renderer_menu.effect_line", desc=desc))
            lines.append("")

    for eid, cfg in ENEMY_CONFIG.items():
        if tier_filter:
            continue
        if not icerainboww_enabled and (eid == "Icerainboww" or "icerainboww" in eid.lower() or "icerainboww" in cfg.get("name", "").lower()):
            continue
        is_meta_hidden = eid in ("【终焉】虚空之门·尤格-索托斯", "【时空主宰】亚弗戈蒙")
        if is_meta_hidden:
            match_keyword = (q_search == eid.lower()) or (q_search == cfg.get("name", "").lower())
        else:
            match_keyword = (q_search == eid.lower()) or (q_search in cfg.get("name", "").lower())
        if match_keyword:
            found = True
            ename = cfg.get("name", eid)
            etype = cfg.get("type", "normal")
            type_map = {
                "normal": get_locale_text("renderer_menu.enemy_type_normal"),
                "elite": get_locale_text("renderer_menu.enemy_type_elite"),
                "boss": get_locale_text("renderer_menu.enemy_type_boss"),
                "summon": get_locale_text("renderer_menu.enemy_type_summon")
            }
            etype_ch = type_map.get(etype, etype)
            ehp = cfg.get("hp", get_locale_text("renderer_menu.unknown"))
            eact = cfg.get("actions", "1A 0BA")
            lines.append(get_locale_text("renderer_menu.enemy_title", name=ename, id=eid, type_ch=etype_ch))
            lines.append(get_locale_text("renderer_menu.enemy_stats_line", hp=ehp, actions=eact))
            passive = cfg.get("passive")
            if passive:
                lines.append(get_locale_text("renderer_menu.enemy_passive_line", passive=passive))
            intents = cfg.get("intents", [])
            if intents:
                lines.append(get_locale_text("renderer_menu.enemy_intents_title"))
                for s in intents:
                    lines.append(get_locale_text("renderer_menu.bullet_line", text=(s.get('desc') or s.get('name') or s.get('id'))))
            cycle_info = cfg.get("cycle_info", [])
            if cycle_info:
                lines.append(get_locale_text("renderer_menu.enemy_cycle_title"))
                for c in cycle_info:
                    lines.append(get_locale_text("renderer_menu.bullet_line", text=c))
            summon_goblin = cfg.get("summon_goblin")
            if summon_goblin:
                lines.append(get_locale_text("renderer_menu.enemy_summons_title"))
                s_name = summon_goblin.get("name", get_locale_text("renderer_menu.unknown"))
                s_hp = summon_goblin.get("hp", 0)
                s_desc = summon_goblin.get("intent_desc", "")
                lines.append(get_locale_text("renderer_menu.enemy_summon_line", name=s_name, hp=s_hp, desc=s_desc))
            summon_hound = cfg.get("summon_hound")
            if summon_hound:
                lines.append(get_locale_text("renderer_menu.enemy_summons_title"))
                s_name = summon_hound.get("name", get_locale_text("renderer_menu.unknown"))
                s_hp = summon_hound.get("hp", 0)
                s_desc = summon_hound.get("intent_desc", "")
                lines.append(get_locale_text("renderer_menu.enemy_summon_line", name=s_name, hp=s_hp, desc=s_desc))
            lines.append("")

    from .town import _load_zh_cn
    town_data = _load_zh_cn()
    if town_data:
        items_map = town_data.get("items", {})
        item_descs = town_data.get("item_descs", {})
        for item_id, aliases in items_map.items():
            if tier_filter:
                continue
            if q_search == item_id.lower() or any(q_search == alias.lower() or q_search in alias.lower() for alias in aliases):
                found = True
                ch_name = aliases[0]
                desc = item_descs.get(item_id, get_locale_text("renderer_menu.town_default_item_desc"))
                lines.append(get_locale_text("renderer_menu.town_item_title", name=ch_name, id=item_id))
                lines.append(get_locale_text("renderer_menu.desc_line", desc=desc))
                lines.append("")
                
        npcs_map = town_data.get("interactive_entities", {})
        for npc_id, npc_cfg in npcs_map.items():
            if tier_filter:
                continue
            npc_name = npc_cfg.get("name", npc_id)
            if q_search == npc_id.lower() or q_search == npc_name.lower() or q_search in npc_name.lower():
                found = True
                desc = npc_cfg.get("desc", get_locale_text("renderer_menu.npc_default_desc"))
                lines.append(get_locale_text("renderer_menu.npc_title", name=npc_name, id=npc_id))
                lines.append(get_locale_text("renderer_menu.npc_intro_line", desc=desc))
                
                idle_talks = npc_cfg.get("idle_talk", [])
                if idle_talks:
                    lines.append(get_locale_text("renderer_menu.npc_talk_title"))
                    for t in idle_talks:
                        lines.append(get_locale_text("renderer_menu.bullet_line", text=t))
                lines.append("")
                
    from .item_query import render_item_lore
    item_block = render_item_lore(q_search, stats, run)
    if item_block:
        found = True
        lines.append(item_block)
    if not found:
        lines.append(get_locale_text("renderer_menu.query_not_found"))
        lines.append("")
    lines.append(get_locale_text("renderer_menu.separator"))
    return "\n".join(lines).strip()
