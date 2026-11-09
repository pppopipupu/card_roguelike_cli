from ..models.state import GameRun, UserStats
from ..cards import ALL_CARDS

def render_menu(stats: UserStats = None) -> str:
    subclass_str = "无"
    gp_val = 0
    selected_class = "法师"
    if stats:
        gp_val = getattr(stats, "gp", 0)
        selected_class = getattr(stats, "selected_class", "法师")
        subclass_str = getattr(stats, "selected_subclass", "") or "无"
    title_suffix = " 战士篇" if selected_class == "战士" else " DND 5.5E 法师篇"
    class_info = f"🔴 当前职业：战士" if selected_class == "战士" else f"🧙 当前职业：法师  🔮 子职业：{subclass_str}"
    lines = [
        "━━━━━━━━━━━━━━━━━━━━",
        f"🔮 魔法肉鸽卡牌游戏 ({title_suffix})",
        "",
        f"💰 我的 GP：{gp_val}",
        class_info,
        "",
        "🏰 【肉鸽模式】经典的文字 Roguelike 卡牌冒险。在随机关卡中进行荒野探索、遗物收集、卡组进化，迎击强大怪物并战胜最终 BOSS！",
        "🏙️ 【先古主城】类似文字冒险的主城探索模式。你可以在这里自由移动、寻找彩蛋、接取任务，甚至与 NPC 进行无损切磋！此外，可以在主城商店中解锁子职业与物品。",
        "",
        "游戏核心机制：每回合拥有 2 个动作 (A) 和 1 个附赠动作 (BA)。",
        "召唤随从和护符可帮助战斗。随从拥有独立的动作，需手动指挥！",
        "",
        "【开始游戏】",
        "👉 /rogue start  -- 开始一局新游戏",
        "👉 /rogue town   -- 前往先古主城探索、游玩及购物",
        "",
        "【其他命令】",
        "👉 /rogue class  -- 查看及选择已解锁的子职业",
        "👉 /rogue overview [card/relic] -- 查看全部卡牌或遗物总览信息",
        "👉 /rogue s  -- 查看当前局内状态",
        "👉 /rogue deck  -- 查看当前拥有的卡组",
        "👉 /rogue stat  -- 查看你的生涯统计数据",
        "👉 /rogue 签到  -- 每日签到，领取下一局祝福并盖集换章",
        "👉 /rogue abandon  -- 放弃当前局内游戏",
        "",
        "💡 提示：输入 /rogue help 或 help 可查看指令用法帮助。",
        "━━━━━━━━━━━━━━━━━━━━"
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
    return cost_str.strip() or "免费"

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
    curses = []
    rarity_map = {
        "common": "普通",
        "rare": "稀有",
        "epic": "珍奇",
        "legendary": "传奇",
        "mythic": "神话",
        "artifact": "神器",
        "curse": "诅咒"
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
            type_ch = "法术"
        elif card.type == "amulet":
            type_ch = f"护符(吟唱 {card.countdown})"
        elif card.type == "ability":
            type_ch = "能力"
        elif card.type == "minion":
            type_ch = "随从"
        rname = rarity_map.get(getattr(card, "rarity", "common"), "普通")
        info = f"• {card.name} [{type_ch}] <{rname}> 消耗: {cost_str} - {card.desc}"
        
        up_card = ALL_CARDS.get(cid + "+")
        if up_card:
            up_cost_str = get_card_cost_str(up_card)
            info += f"\n  └─ 🔨 升级版：{up_card.name} | 消耗: {up_cost_str} | {up_card.desc}"
            
        if card.color == "curse":
            curses.append(f"[诅咒] {info}")
        elif card.color == "neutral":
            neutrals.append(f"[中立] {info}")
        elif card.color == "warrior":
            red_cards.append(f"[战士] {info}")
        else:
            blue_spells.append(f"[法师] {info}")
            
    return neutrals + blue_spells + red_cards + curses

def get_rogue_relic_library_items() -> list:
    from ..data.relic_data import RELIC_CONFIG
    items = []
    rarity_map = {
        "common": "普通",
        "rare": "稀有",
        "epic": "珍奇",
        "legendary": "传奇",
        "mythic": "神话",
        "artifact": "神器",
        "curse": "诅咒"
    }
    for rid, cfg in RELIC_CONFIG.items():
        rname = cfg.get("name", rid)
        rarity = cfg.get("rarity", "common")
        rname_rarity = rarity_map.get(rarity, rarity)
        desc = cfg.get("desc", "")
        price = cfg.get("price", 0)
        items.append(f"🎒 {rname} ({rname_rarity}) - {desc} | 售价: {price} 金币")
    return items



def render_reader_page(stats: UserStats) -> str:
    total_items = len(stats.reader_items)
    page_size = 10
    total_pages = (total_items + page_size - 1) // page_size
    page = max(1, min(stats.reader_page, total_pages))
    
    start_idx = (page - 1) * page_size
    end_idx = min(start_idx + page_size, total_items)
    
    lines = [
        "━━━━━━━━━━━━━━━━━━━━",
        f"{stats.reader_title} (第 {page} / {total_pages} 页)",
        ""
    ]
    for i in range(start_idx, end_idx):
        lines.append(f"{i + 1}. {stats.reader_items[i]}")
        
    lines.append("")
    lines.append("💡 输入 n (下一页) | b (上一页) | q (退出)")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)

def render_card_library() -> str:
    from ..models.manager import SaveManager
    boss_cfg = SaveManager().load_admin_config()
    icerainboww_enabled = boss_cfg.get("icerainboww_enabled", True)
    lines = [
        "━━━━━━━━━━━━━━━━━━━━",
        "📜 魔法肉鸽卡牌总览",
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
            type_ch = "法术"
        elif card.type == "amulet":
            type_ch = f"护符(吟唱 {card.countdown})"
        elif card.type == "ability":
            type_ch = "能力"
        elif card.type == "minion":
            type_ch = "随从"
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
        info = f"• {card.name} [{type_ch}] <{rname}> 消耗: {cost_str} - {card.desc}"
        
        up_card = ALL_CARDS.get(cid + "+")
        if up_card:
            up_cost_str = get_card_cost_str(up_card)
            info += f"\n  └─ 🔨 升级版：{up_card.name} | 消耗: {up_cost_str} | {up_card.desc}"
            
        if card.color == "curse":
            curses.append(info)
        elif card.color == "neutral":
            neutrals.append(info)
        elif card.color == "warrior":
            red_cards.append(info)
        else:
            blue_spells.append(info)
    lines.append("【无色卡牌（中立）】")
    lines.extend(neutrals)
    lines.append("")
    lines.append("【蓝色卡牌（法师）】")
    lines.extend(blue_spells)
    lines.append("")
    lines.append("【红色卡牌（战士）】")
    lines.extend(red_cards)
    lines.append("")
    lines.append("【灰色卡牌（诅咒）】")
    lines.extend(curses)
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)

def render_relic_library() -> str:
    from ..data.relic_data import RELIC_CONFIG
    lines = [
        "━━━━━━━━━━━━━━━━━━━━",
        "🎒 魔法肉鸽遗物总览",
        ""
    ]
    rarity_map = {
        "common": "普通",
        "rare": "稀有",
        "epic": "珍奇",
        "legendary": "传奇",
        "mythic": "神话",
        "artifact": "神器",
        "curse": "诅咒"
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
        rname = rarity_map.get(r, "普通")
        name = relic.get("name", rid)
        desc = relic.get("desc", "")
        price = relic.get("price", 0)
        info = f"• {name} <{rname}> 售价: {price}金币 - {desc}"
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
    lines.append("【普通遗物】")
    lines.extend(commons)
    lines.append("")
    lines.append("【稀有遗物】")
    lines.extend(rares)
    lines.append("")
    lines.append("【珍奇遗物】")
    lines.extend(epics)
    lines.append("")
    lines.append("【传奇遗物】")
    lines.extend(legendaries)
    lines.append("")
    lines.append("【神话遗物】")
    lines.extend(mythics)
    lines.append("")
    lines.append("【神器遗物】")
    lines.extend(artifacts)
    lines.append("")
    lines.append("【诅咒遗物】")
    lines.extend(curses)
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)

def render_deck(run: GameRun) -> str:
    if not run or not run.player:
        return "❌ 你当前没有正在进行的游戏。输入 /rogue 开启 开始新游戏。"
    lines = [
        "━━━━━━━━━━━━━━━━━━━━",
        "📜 当前拥有的卡组 (共 %d 张)" % len(run.player.deck),
        ""
    ]
    from ..models.state import ensure_card_state
    counts = {}
    for cid in run.player.deck:
        c_state = ensure_card_state(cid)
        counts[c_state] = counts.get(c_state, 0) + 1
    idx = 1
    def get_sort_key(item):
        return (item[0].id, 1 if item[0].upgraded else 0, tuple(item[0].gems or []))
    for cid, count in sorted(counts.items(), key=get_sort_key):
        card = ALL_CARDS.get(cid)
        if card:
            color_type = "⚫" if card.color == "curse" else ("🔴" if card.color == "warrior" else ("🔵" if card.color == "wizard" else "⚪"))
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
            cost_str = get_card_cost_str(card)
            lines.append(f"{idx}. {color_type} {card.name} <{rname}> (消耗: {cost_str}) x{count} ({card.desc})")
            idx += 1
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)

def render_stats(stats: UserStats, include_mode: bool = True) -> str:
    mode_str = "开启" if getattr(stats, "rogue_mode", False) else "关闭"
    mode_line = [f"🎮 免前缀肉鸽模式：【{mode_str}】"] if include_mode else []
    lines = [
        "━━━━━━━━━━━━━━━━━━━━",
        "📊 魔法肉鸽卡牌生涯统计",
        "",
        f"💥 累计输出伤害：{stats.total_damage} 点",
        f"💀 累计击败怪物：{stats.total_kills} 只",
        f"🧗 累计游玩层数：{stats.total_stages} 层",
        *mode_line,
        "",
        "这些数据属于你的勇士生涯，不会随着放弃游戏而消失。",
        "━━━━━━━━━━━━━━━━━━━━"
    ]
    return "\n".join(lines)

def render_help(include_mode: bool = True) -> str:
    mode_line = ["👉 mode -- 切换个人免前缀快捷指令模式（即时通讯端）"] if include_mode else []
    mode_tip = ["  • 免前缀模式：即时通讯端通过发送 /rogue mode 切换；网页端固定开启。开启后，只要你有活跃游戏存档，所有游戏相关的指令都可以直接发送（例如直接发送“e”、“1”、“p 1”、“bag”、“s”），无须添加前缀。此功能仅限个人生效。"] if include_mode else []
    lines = [
        "━━━━━━━━━━━━━━━━━━━━",
        "🔮 魔法肉鸽卡牌游戏指令帮助",
        "",
        "🏰 【肉鸽模式】经典的文字 Roguelike 卡牌冒险。在随机关卡中进行荒野探索、遗物收集、卡组进化，迎击强大怪物并战胜最终 BOSS！",
        "",
        "输入 /rogue <子命令> 执行对应操作，指令支持中英文别名与简写：",
        "",
        "【基础与非战斗指令】",
        "👉 start -- 开始一局新游戏（若有存档可输入 start confirm 确认）",
        "👉 help -- 显示本帮助指令列表",
        "👉 tutorial -- 查看详细的游戏机制与指令教程",
        "👉 s (status) -- 查看当前的局内游戏界面与属性状态",
        "👉 deck -- 查看当前拥有的全部卡组及卡牌序号",
        "👉 overview [card/relic] -- 查看全部卡牌或遗物总览信息",
        "👉 stat -- 查看勇士生涯累计统计数据",
        "👉 leaderboard -- 查看 GP 排行榜（前 20）",
        "👉 leaderboard online -- 查看最近 5 分钟在线玩家",
        "👉 checkin (签到) [集换卡] -- 每日 UTC+0 签到，领取下一局祝福并给集换卡盖章",
        "👉 class -- 查看及选择子职业",
        "👉 shop -- 访问局外商店，使用 GP 购买子职业或神秘物品",
        "👉 abandon -- 放弃当前战局（需输入 abandon confirm 确认）",
        *mode_line,
        "👉 bag (inv/inventory) -- 查看主城背包与拥有的物品资产",
        "👉 quest (quests) -- 查看当前主城任务列表及进度",
        "👉 lock (unlock) -- 进入开局卡牌锁定构筑管理系统",
        "👉 map -- 在主城切换大地图或局部小地图样式",
        "👉 friend (好友) -- 好友列表、搜索、申请与删改；friend invite 邀请好友组队",
        "👉 team (队伍) -- 创建队伍、邀请队友、准备并开启 2~4 人联机牌局",
        "",
        "【局内与战斗指令】",
        "👉 p <手牌序号|拼音首字母> [目标] -- 使用或打出指定手牌，支持卡牌名称拼音首字母贪婪匹配。例如：p 1 或 p ssxs",
        "👉 m <我方格子> <动作> <目标/序号> -- 指挥我方随从执行动作。例如：m 1 a e1",
        "   └─ 随从格子支持数字，以及 all 或 * 表示所有随从",
        "   └─ 动作支持 a / attack (攻击) 或 s / skill (技能)",
        "👉 c <序号> -- 选择事件分支、契约选项或商店商品（直接输入数字也可）。例如：c 1",
        "👉 sa <手牌序号> [目标] -- 释放对应手牌的特殊行动。例如：sa 1",
        "👉 e -- 结束当前的战斗回合",
        "👉 f -- 切换是否折叠游戏底部的操作指南",
        "👉 q <[指令1...]> -- 顺序执行命令队列（即便失败也会强行继续）。例如：q [p 1, e]",
        "👉 qi <[指令1...]> -- 顺序执行命令队列，一旦任何子指令失败则立刻中断。例如：qi [p 1, e]",
        "👉 i [名称] -- 查询战斗快照，或模糊查询卡牌/随从/遗物/护符/Buff/怪物信息",
        "👉 draw (discard/exhaust) -- 在战斗中直接查询抽牌堆、弃牌堆或消耗堆",
        "👉 mg (eg) -- 在战斗中直接查询我方随从墓地或敌方已击杀墓地",
        "👉 exit (quit/取消) -- 在等待选择目标或发掘卡牌等拦截状态下无损退出",
        "",
        "【主城互动指令】",
        "👉 talk (交互/talk_to) <目标> -- 与场景中的 NPC 开启交谈交互",
        "👉 take (拿取) <物品> -- 拾取房间地面上的可见道具物品",
        "👉 use (使用) <物品> -- 使用主城背包中拥有的相关道具物品",
        "👉 look (看) -- 在主城中环顾四周，查看当前环境与在场人物",
        "👉 leave (离开) -- 结束与 NPC 的对话交谈",
        "",
        "💡 快捷输入与免前缀技巧：",
        "  • 简写支持：战斗和交互指令均支持简写，如 p（出牌）、m（随从）、c（选择）、e（结束）、i（查询）、s（状态）。",
        "  • 选择免指令：在面临事件选择、商店购买或选择打出卡牌的等待输入状态下，直接发送目标数字（如“1”）即可触发对应选项，无须输入 c 前缀。",
        *mode_tip,
        "━━━━━━━━━━━━━━━━━━━━"
    ]
    return "\n".join(lines)


def strip_markdown(text: str) -> str:
    import re
    text = re.sub(r'^#\s+(.+)$', r'🔮 \1', text, flags=re.MULTILINE)
    text = re.sub(r'^##\s+(.+)$', r'🔹 \1', text, flags=re.MULTILINE)
    text = re.sub(r'^###\s+(.+)$', r'▫️ \1', text, flags=re.MULTILINE)
    text = re.sub(r'^---\s*$', r'━━━━━━━━━━━━━━━━━━━━', text, flags=re.MULTILINE)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text = text.replace('**', '').replace('___', '').replace('__', '').replace('*', '')
    text = text.replace('```', '')
    text = text.replace('`', '')
    text = re.sub(r'^>\s*', r'  ', text, flags=re.MULTILINE)
    text = re.sub(r'^-\s+', r'• ', text, flags=re.MULTILINE)
    return text

def render_tutorial() -> str:
    import os
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = os.path.join(base_dir, "TUTORIAL.md")
    if not os.path.exists(path):
        return "❌ 未找到游戏教程文档。"
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        return strip_markdown(content)
    except Exception:
        return "❌ 读取游戏教程文档失败。"


def render_shop(stats: UserStats) -> str:
    from ..data.shop_data import SHOP_ITEMS
    import random
    gp = getattr(stats, "gp", 0)
    unlocked = getattr(stats, "unlocked_subclasses", [])
    status_time = "已解锁" if "时序法师" in unlocked else "未解锁"
    status_element = "已解锁" if "塑能法师" in unlocked else "未解锁"
    status_key = "已解锁" if "秘钥学者" in unlocked else "未解锁"
    status_gatekey = "已解锁" if getattr(stats, "unlocked_gatekey", False) else "未解锁"
    status_mystery = "已解锁" if "神秘物品" in unlocked else "未解锁"
    
    welcome_quotes = [
        "“...嘘，悄悄看，我这儿可都是从无尽时空深处淘来的宝贝。”",
        "“又是你，旅者？只要GP足够，我这里的东西随时都可以归你。”",
        "“想要掌控时间，还是驾驭元素？或者……你对那件‘神秘物品’感兴趣？”",
        "“奥术的轨迹是有限的，但金钱与力量的秘密是无限的。”",
        "“有些东西并不存在于当下的时空，但在这里，一切皆有可能。”",
        "“外面的风暴越来越近了，或许你该准备点真正强力的武器？”"
    ]
    welcome_quote = random.choice(welcome_quotes)
    
    from ..models.manager import SaveManager
    boss_cfg = SaveManager().load_admin_config()
    icerainboww_enabled = boss_cfg.get("icerainboww_enabled", True)
    
    if not icerainboww_enabled:
        item6_title = " [6] 商品已禁用 - 状态：不可用"
        item6_desc = "     └─ 该内容已被管理员禁用。"
    else:
        killed_icerainboww = getattr(stats, "killed_icerainboww", False)
        if killed_icerainboww:
            item6_title = " [6] Icerainboww - 状态：已解锁"
            item6_desc = "     └─ 击败最终BOSS Icerainboww解锁。"
        else:
            item6_title = " [6] ？？？ - 状态：未解锁"
            item6_desc = "     └─ 击败未知的最终BOSS解锁。"

    killed_yog = getattr(stats, "yog_sothoth_kill_count", 0) > 0
    if killed_yog:
        item7_title = " [7] 尤格-索托斯 - 状态：已解锁"
        item7_desc = "     └─ 击败超最终BOSS尤格-索托斯解锁。"
    else:
        item7_title = " [7] ？？？ - 状态：未解锁"
        item7_desc = "     └─ 击败未知的超最终BOSS解锁。"

    lines = [
        "━━━━━━━━━━━━━━━━━━━━",
        "🏪 魔法肉鸽局外成长商店",
        "",
        "🔮 神秘店主说：",
        f"  {welcome_quote}",
        "",
        f"💰 我的 GP：{gp}",
        "",
        "【货架商品】",
        f" [1] 时序法师子职业 - 售价：{SHOP_ITEMS['时序法师']['price']} GP （状态：{status_time}）",
        f"     └─ {SHOP_ITEMS['时序法师']['desc']}",
        f" [2] 塑能法师子职业 - 售价：{SHOP_ITEMS['塑能法师']['price']} GP （状态：{status_element}）",
        f"     └─ {SHOP_ITEMS['塑能法师']['desc']}",
        f" [3] 秘钥学者子职业 - 售价：{SHOP_ITEMS['秘钥学者']['price']} GP （状态：{status_key}）",
        f"     └─ {SHOP_ITEMS['秘钥学者']['desc']}",
        f" [4] 门之钥匙 - 售价：{SHOP_ITEMS['门之钥匙']['price']} GP （状态：{status_gatekey}）",
        f"     └─ {SHOP_ITEMS['门之钥匙']['desc']}",
        f" [5] 神秘物品 - 售价：{SHOP_ITEMS['神秘物品']['price']} GP （状态：{status_mystery}）",
        f"     └─ {SHOP_ITEMS['神秘物品']['desc']}",
        item6_title,
        item6_desc,
        item7_title,
        item7_desc,
        "",
        "【购买指令】",
        "👉 /rogue 商店 购买 1 -- 购买时序法师",
        "👉 /rogue 商店 购买 2 -- 购买塑能法师",
        "👉 /rogue 商店 购买 3 -- 购买秘钥学者",
        "👉 /rogue 商店 购买 4 -- 购买门之钥匙",
        "👉 /rogue 商店 购买 5 -- 购买神秘物品",
        "━━━━━━━━━━━━━━━━━━━━"
    ]
    return "\n".join(lines)
