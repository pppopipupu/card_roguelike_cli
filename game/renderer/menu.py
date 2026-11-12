from ..models.state import GameRun, UserStats
from ..cards import ALL_CARDS
from ..data.locale_data import t

def render_menu(stats: UserStats = None) -> str:
    subclass_str = t("renderer_menu.none")
    gp_val = 0
    selected_class = "法师"
    if stats:
        gp_val = getattr(stats, "gp", 0)
        selected_class = getattr(stats, "selected_class", "法师")
        subclass_str = getattr(stats, "selected_subclass", "") or t("renderer_menu.none")
    title_suffix = t("renderer_menu.title_suffix_warrior") if selected_class == "战士" else t("renderer_menu.title_suffix_wizard")
    class_info = t("renderer_menu.class_warrior") if selected_class == "战士" else t("renderer_menu.class_wizard", subclass=subclass_str)
    lines = [
        t("renderer_menu.separator"),
        t("renderer_menu.title", suffix=title_suffix),
        "",
        t("renderer_menu.gp_line", gp=gp_val),
        class_info,
        "",
        t("renderer_menu.rogue_intro"),
        t("renderer_menu.town_intro"),
        "",
        t("renderer_menu.mechanics_actions"),
        t("renderer_menu.mechanics_minions"),
        "",
        t("renderer_menu.start_section"),
        t("renderer_menu.cmd_start"),
        t("renderer_menu.cmd_town"),
        "",
        t("renderer_menu.other_section"),
        t("renderer_menu.cmd_class"),
        t("renderer_menu.cmd_overview"),
        t("renderer_menu.cmd_achievement"),
        t("renderer_menu.cmd_status"),
        t("renderer_menu.cmd_deck"),
        t("renderer_menu.cmd_stat"),
        t("renderer_menu.cmd_checkin"),
        t("renderer_menu.cmd_abandon"),
        "",
        t("renderer_menu.help_tip"),
        t("renderer_menu.separator")
    ]
    return "\n".join(lines)

def get_card_cost_str(card) -> str:
    cost_str = ""
    if card.cost_a == -1 and card.cost_ba == -1:
        cost_str = "X A Y BA"
    else:
        if card.cost_a == -1:
            cost_str += "X A "
        elif card.cost_a > 0:
            cost_str += f"{card.cost_a}A "
        if card.cost_ba == -1:
            cost_str += "X BA "
        elif card.cost_ba > 0:
            cost_str += f"{card.cost_ba}BA "
    return cost_str.strip() or t("renderer_menu.free_cost")

def append_card_subtype(type_ch: str, cid: str, ctype: str) -> str:
    if ctype != "spell":
        return type_ch
    from ..data.card_subtype_data import ATTACK_SPELL_IDS, SKILL_SPELL_IDS
    base_cid = cid.rstrip("+")
    if base_cid in ATTACK_SPELL_IDS:
        subtype_ch = t("renderer_menu.subtype_attack")
    elif base_cid in SKILL_SPELL_IDS:
        subtype_ch = t("renderer_menu.subtype_skill")
    else:
        return type_ch
    return t("renderer_menu.card_type_with_subtype", type_ch=type_ch, subtype_ch=subtype_ch)

def get_rogue_card_library_items(user_id: str | None = None) -> list:
    from ..cards import ALL_CARDS
    from ..models.manager import SaveManager
    boss_cfg = SaveManager().load_admin_config()
    icerainboww_enabled = boss_cfg.get("icerainboww_enabled", True)
    
    killed_yog = False
    if user_id:
        stats = SaveManager().load_stats(user_id)
        if stats and getattr(stats, "yog_sothoth_kill_count", 0) > 0:
            killed_yog = True
    neutrals = []
    blue_spells = []
    red_cards = []
    merc_cards = []
    curses = []
    rarity_map = {
        "common": t("renderer_menu.rarity_common"),
        "rare": t("renderer_menu.rarity_rare"),
        "epic": t("renderer_menu.rarity_epic"),
        "legendary": t("renderer_menu.rarity_legendary"),
        "mythic": t("renderer_menu.rarity_mythic"),
        "artifact": t("renderer_menu.rarity_artifact"),
        "curse": t("renderer_menu.rarity_curse")
    }
    for cid, card in ALL_CARDS.items():
        if card.upgraded:
            continue
        if cid == "neutral_button_magic" and not killed_yog:
            continue
        if not icerainboww_enabled and cid in ("minion_icerainboww", "minion_icerainboww+"):
            continue
        cost_str = get_card_cost_str(card)
        type_ch = ""
        if card.type == "spell":
            type_ch = t("renderer_menu.type_spell")
        elif card.type == "amulet":
            type_ch = t("renderer_menu.type_amulet", countdown=card.countdown)
        elif card.type == "ability":
            type_ch = t("renderer_menu.type_ability")
        elif card.type == "minion":
            type_ch = t("renderer_menu.type_minion")
        type_ch = append_card_subtype(type_ch, cid, card.type)
        rname = rarity_map.get(getattr(card, "rarity", "common"), t("renderer_menu.rarity_common"))
        info = t("renderer_menu.card_info", name=card.name, type_ch=type_ch, rarity=rname, cost=cost_str, desc=card.desc)
        
        up_card = ALL_CARDS.get(cid + "+")
        if up_card:
            up_cost_str = get_card_cost_str(up_card)
            info += t("renderer_menu.card_upgrade", name=up_card.name, cost=up_cost_str, desc=up_card.desc)
            
        if card.color == "curse":
            curses.append(t("renderer_menu.prefix_curse", info=info))
        elif card.color == "neutral":
            neutrals.append(t("renderer_menu.prefix_neutral", info=info))
        elif card.color == "warrior":
            red_cards.append(t("renderer_menu.prefix_warrior", info=info))
        elif card.color == "mercenary":
            merc_cards.append(t("renderer_menu.prefix_mercenary", info=info))
        else:
            blue_spells.append(t("renderer_menu.prefix_wizard", info=info))
            
    return neutrals + blue_spells + red_cards + merc_cards + curses
def get_rogue_relic_library_items() -> list:
    from ..data.relic_data import RELIC_CONFIG
    items = []
    rarity_map = {
        "common": t("renderer_menu.rarity_common"),
        "rare": t("renderer_menu.rarity_rare"),
        "epic": t("renderer_menu.rarity_epic"),
        "legendary": t("renderer_menu.rarity_legendary"),
        "mythic": t("renderer_menu.rarity_mythic"),
        "artifact": t("renderer_menu.rarity_artifact"),
        "curse": t("renderer_menu.rarity_curse")
    }
    for rid, cfg in RELIC_CONFIG.items():
        rname = cfg.get("name", rid)
        rarity = cfg.get("rarity", "common")
        rname_rarity = rarity_map.get(rarity, rarity)
        desc = cfg.get("desc", "")
        price = cfg.get("price", 0)
        items.append(t("renderer_menu.relic_library_item", name=rname, rarity=rname_rarity, desc=desc, price=price))
    return items



def render_reader_page(stats: UserStats) -> str:
    total_items = len(stats.reader_items)
    page_size = 10
    total_pages = max(1, (total_items + page_size - 1) // page_size)
    page = max(1, min(stats.reader_page, total_pages))
    
    start_idx = (page - 1) * page_size
    end_idx = min(start_idx + page_size, total_items)
    
    lines = [
        t("renderer_menu.separator"),
        t("renderer_menu.reader_title", title=stats.reader_title, page=page, total_pages=total_pages),
        ""
    ]
    if total_items == 0:
        lines.append(t("renderer_menu.reader_empty"))
    else:
        for i in range(start_idx, end_idx):
            lines.append(f"{i + 1}. {stats.reader_items[i]}")
        
    lines.append("")
    lines.append(t("renderer_menu.reader_prompt"))
    lines.append(t("renderer_menu.separator"))
    return "\n".join(lines)

def render_card_library() -> str:
    from ..models.manager import SaveManager
    boss_cfg = SaveManager().load_admin_config()
    icerainboww_enabled = boss_cfg.get("icerainboww_enabled", True)
    lines = [
        t("renderer_menu.separator"),
        t("renderer_menu.card_library_title"),
        ""
    ]
    neutrals = []
    blue_spells = []
    red_cards = []
    curses = []
    for cid, card in ALL_CARDS.items():
        if not icerainboww_enabled and cid in ("minion_icerainboww", "minion_icerainboww+"):
            continue
        cost_str = get_card_cost_str(card)
        type_ch = ""
        if card.type == "spell":
            type_ch = t("renderer_menu.type_spell")
        elif card.type == "amulet":
            type_ch = t("renderer_menu.type_amulet", countdown=card.countdown)
        elif card.type == "ability":
            type_ch = t("renderer_menu.type_ability")
        elif card.type == "minion":
            type_ch = t("renderer_menu.type_minion")
        type_ch = append_card_subtype(type_ch, cid, card.type)
        rarity_map = {
            "common": t("renderer_menu.rarity_common"),
            "rare": t("renderer_menu.rarity_rare"),
            "epic": t("renderer_menu.rarity_epic"),
            "legendary": t("renderer_menu.rarity_legendary"),
            "mythic": t("renderer_menu.rarity_mythic"),
            "artifact": t("renderer_menu.rarity_artifact"),
            "curse": t("renderer_menu.rarity_curse")
        }
        rname = rarity_map.get(getattr(card, "rarity", "common"), t("renderer_menu.rarity_common"))
        info = t("renderer_menu.card_info", name=card.name, type_ch=type_ch, rarity=rname, cost=cost_str, desc=card.desc)
        
        up_card = ALL_CARDS.get(cid + "+")
        if up_card:
            up_cost_str = get_card_cost_str(up_card)
            info += t("renderer_menu.card_upgrade", name=up_card.name, cost=up_cost_str, desc=up_card.desc)
            
        if card.color == "curse":
            curses.append(info)
        elif card.color == "neutral":
            neutrals.append(info)
        elif card.color == "warrior":
            red_cards.append(info)
        else:
            blue_spells.append(info)
    lines.append(t("renderer_menu.section_colorless"))
    lines.extend(neutrals)
    lines.append("")
    lines.append(t("renderer_menu.section_blue"))
    lines.extend(blue_spells)
    lines.append("")
    lines.append(t("renderer_menu.section_red"))
    lines.extend(red_cards)
    lines.append("")
    lines.append(t("renderer_menu.section_gray"))
    lines.extend(curses)
    lines.append(t("renderer_menu.separator"))
    return "\n".join(lines)

def render_relic_library() -> str:
    from ..data.relic_data import RELIC_CONFIG
    lines = [
        t("renderer_menu.separator"),
        t("renderer_menu.relic_library_title"),
        ""
    ]
    rarity_map = {
        "common": t("renderer_menu.rarity_common"),
        "rare": t("renderer_menu.rarity_rare"),
        "epic": t("renderer_menu.rarity_epic"),
        "legendary": t("renderer_menu.rarity_legendary"),
        "mythic": t("renderer_menu.rarity_mythic"),
        "artifact": t("renderer_menu.rarity_artifact"),
        "curse": t("renderer_menu.rarity_curse")
    }
    commons = []
    rares = []
    epics = []
    legendaries = []
    mythics = []
    artifacts = []
    curses = []
    for rid, relic in RELIC_CONFIG.items():
        r = relic.get("rarity", "common")
        rname = rarity_map.get(r, t("renderer_menu.rarity_common"))
        name = relic.get("name", rid)
        desc = relic.get("desc", "")
        price = relic.get("price", 0)
        info = t("renderer_menu.relic_library_line", name=name, rarity=rname, price=price, desc=desc)
        if r == "common":
            commons.append(info)
        elif r == "rare":
            rares.append(info)
        elif r == "epic":
            epics.append(info)
        elif r == "legendary":
            legendaries.append(info)
        elif r == "mythic":
            mythics.append(info)
        elif r == "artifact":
            artifacts.append(info)
        elif r == "curse":
            curses.append(info)
    lines.append(t("renderer_menu.relic_section", rarity=t("renderer_menu.rarity_common")))
    lines.extend(commons)
    lines.append("")
    lines.append(t("renderer_menu.relic_section", rarity=t("renderer_menu.rarity_rare")))
    lines.extend(rares)
    lines.append("")
    lines.append(t("renderer_menu.relic_section", rarity=t("renderer_menu.rarity_epic")))
    lines.extend(epics)
    lines.append("")
    lines.append(t("renderer_menu.relic_section", rarity=t("renderer_menu.rarity_legendary")))
    lines.extend(legendaries)
    lines.append("")
    lines.append(t("renderer_menu.relic_section", rarity=t("renderer_menu.rarity_mythic")))
    lines.extend(mythics)
    lines.append("")
    lines.append(t("renderer_menu.relic_section", rarity=t("renderer_menu.rarity_artifact")))
    lines.extend(artifacts)
    lines.append("")
    lines.append(t("renderer_menu.relic_section", rarity=t("renderer_menu.rarity_curse")))
    lines.extend(curses)
    lines.append(t("renderer_menu.separator"))
    return "\n".join(lines)

def render_deck(run: GameRun) -> str:
    if not run or not run.player:
        return t("renderer_menu.deck_empty")
    lines = [
        t("renderer_menu.separator"),
        t("renderer_menu.deck_title", count=len(run.player.deck)),
        ""
    ]
    from ..models.state import ensure_card_state
    counts = {}
    for cid in run.player.deck:
        c_state = ensure_card_state(cid)
        counts[c_state] = counts.get(c_state, 0) + 1
    idx = 1
    def get_sort_key(item):
        return (item[0].id, 1 if item[0].upgraded else 0, tuple(item[0].gems or []), item[0].exhaust_used, item[0].fleeting_used)
    for cid, count in sorted(counts.items(), key=get_sort_key):
        card = ALL_CARDS.get(cid)
        if card:
            color_type = "⚫" if card.color == "curse" else ("🔴" if card.color == "warrior" else ("🔵" if card.color == "wizard" else ("🟣" if card.color == "mercenary" else "⚪")))
            rarity_map = {
                "common": t("renderer_menu.rarity_common"),
                "rare": t("renderer_menu.rarity_rare"),
                "epic": t("renderer_menu.rarity_epic"),
                "legendary": t("renderer_menu.rarity_legendary"),
                "mythic": t("renderer_menu.rarity_mythic"),
                "artifact": t("renderer_menu.rarity_artifact"),
                "curse": t("renderer_menu.rarity_curse")
            }
            rname = rarity_map.get(getattr(card, "rarity", "common"), t("renderer_menu.rarity_common"))
            cost_str = get_card_cost_str(card)
            lines.append(t("renderer_menu.deck_line", idx=idx, color=color_type, name=card.name, rarity=rname, cost=cost_str, count=count, desc=card.desc))
            idx += 1
    lines.append(t("renderer_menu.separator"))
    return "\n".join(lines)

def render_stats(stats: UserStats, include_mode: bool = True) -> str:
    mode_str = t("renderer_menu.mode_on") if getattr(stats, "rogue_mode", False) else t("renderer_menu.mode_off")
    mode_line = [t("renderer_menu.stats_mode_line", mode=mode_str)] if include_mode else []
    lines = [
        t("renderer_menu.separator"),
        t("renderer_menu.stats_title"),
        "",
        t("renderer_menu.stats_damage", damage=stats.total_damage),
        t("renderer_menu.stats_kills", kills=stats.total_kills),
        t("renderer_menu.stats_stages", stages=stats.total_stages),
        *mode_line,
        "",
        t("renderer_menu.stats_footer"),
        t("renderer_menu.separator")
    ]
    return "\n".join(lines)

def strip_markdown(text: str) -> str:
    import re
    text = re.sub(r'^#\s+(.+)$', r'🔮 \1', text, flags=re.MULTILINE)
    text = re.sub(r'^##\s+(.+)$', r'🔹 \1', text, flags=re.MULTILINE)
    text = re.sub(r'^###\s+(.+)$', r'▫️ \1', text, flags=re.MULTILINE)
    text = re.sub(r'^---\s*$', t("renderer_menu.separator"), text, flags=re.MULTILINE)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text = text.replace('**', '').replace('___', '').replace('__', '').replace('*', '')
    text = text.replace('```', '')
    text = text.replace('`', '')
    text = re.sub(r'^>\s*', r'  ', text, flags=re.MULTILINE)
    text = re.sub(r'^-\s+', r'• ', text, flags=re.MULTILINE)
    return text

def render_root_document(filename: str, missing_key: str, read_error_key: str) -> str:
    import os
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = os.path.join(base_dir, filename)
    if not os.path.exists(path):
        return t(missing_key)
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        return strip_markdown(content)
    except Exception:
        return t(read_error_key)

def render_tutorial() -> str:
    return render_root_document("TUTORIAL.md", "renderer_menu.tutorial_missing", "renderer_menu.tutorial_read_error")

def render_changelog() -> str:
    return render_root_document("CHANGELOG.md", "renderer_menu.changelog_missing", "renderer_menu.changelog_read_error")


def render_shop(stats: UserStats) -> str:
    from ..data.shop_data import SHOP_ITEMS
    import random
    gp = getattr(stats, "gp", 0)
    unlocked = getattr(stats, "unlocked_subclasses", [])
    status_time = t("renderer_menu.status_unlocked") if "时序法师" in unlocked else t("renderer_menu.status_locked")
    status_element = t("renderer_menu.status_unlocked") if "塑能法师" in unlocked else t("renderer_menu.status_locked")
    status_key = t("renderer_menu.status_unlocked") if "秘钥学者" in unlocked else t("renderer_menu.status_locked")
    status_gatekey = t("renderer_menu.status_unlocked") if getattr(stats, "unlocked_gatekey", False) else t("renderer_menu.status_locked")
    status_mystery = t("renderer_menu.status_unlocked") if "神秘物品" in unlocked else t("renderer_menu.status_locked")
    
    welcome_quotes = [
        t("renderer_menu.shop_quote_1"),
        t("renderer_menu.shop_quote_2"),
        t("renderer_menu.shop_quote_3"),
        t("renderer_menu.shop_quote_4"),
        t("renderer_menu.shop_quote_5"),
        t("renderer_menu.shop_quote_6")
    ]
    welcome_quote = random.choice(welcome_quotes)

    lines = [
        t("renderer_menu.separator"),
        t("renderer_menu.shop_title"),
        "",
        t("renderer_menu.shop_keeper"),
        t("renderer_menu.shop_quote_line", quote=welcome_quote),
        "",
        t("renderer_menu.shop_gp", gp=gp),
        "",
        t("renderer_menu.shop_shelf_section"),
        t("renderer_menu.shop_item1", price=SHOP_ITEMS['时序法师']['price'], status=status_time),
        t("renderer_menu.shop_item_desc", desc=SHOP_ITEMS['时序法师']['desc']),
        t("renderer_menu.shop_item2", price=SHOP_ITEMS['塑能法师']['price'], status=status_element),
        t("renderer_menu.shop_item_desc", desc=SHOP_ITEMS['塑能法师']['desc']),
        t("renderer_menu.shop_item3", price=SHOP_ITEMS['秘钥学者']['price'], status=status_key),
        t("renderer_menu.shop_item_desc", desc=SHOP_ITEMS['秘钥学者']['desc']),
        t("renderer_menu.shop_item4", price=SHOP_ITEMS['门之钥匙']['price'], status=status_gatekey),
        t("renderer_menu.shop_item_desc", desc=SHOP_ITEMS['门之钥匙']['desc']),
        t("renderer_menu.shop_item5", price=SHOP_ITEMS['神秘物品']['price'], status=status_mystery),
        t("renderer_menu.shop_item_desc", desc=SHOP_ITEMS['神秘物品']['desc']),
        "",
        t("renderer_menu.shop_buy_section"),
        t("renderer_menu.shop_buy1"),
        t("renderer_menu.shop_buy2"),
        t("renderer_menu.shop_buy3"),
        t("renderer_menu.shop_buy4"),
        t("renderer_menu.shop_buy5"),
        t("renderer_menu.separator")
    ]
    return "\n".join(lines)
