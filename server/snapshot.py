import re
from typing import Any, Optional

from game.cards import ALL_CARDS
from game.data.gem_data import GEM_CONFIG
from game.data.locale_data import get_locale_text
from game.data.potion_data import get_potion_desc, get_potion_name
from game.entities import get_relic_desc, get_relic_name
from game.models.state import CardState, GameRun, UserStats, ensure_card_state
from game.renderer.menu import get_card_cost_str


NODE_LABELS = {
    "battle": "遭遇战",
    "elite": "精英战",
    "event": "神秘事件",
    "shop": "奇妙商店",
    "rest": "篝火营地",
    "treasure": "古老宝箱",
    "boss": "首领战",
    "corpse": "尸体",
}

SCREEN_LABELS = {
    "map_select": "地图",
    "start_ancient": "先古契约",
    "ancient": "先古赐福",
    "battle": "战斗",
    "event": "随机事件",
    "shop": "奇妙商店",
    "rest": "篝火营地",
    "reward": "战利品",
    "treasure": "古老宝箱",
    "card_select": "卡牌选择",
    "boss_chest": "神话宝箱",
    "corpse_reward": "搜刮尸体",
    "gem_insert": "宝石镶嵌",
    "cafe": "咖啡馆",
    "victory": "胜利",
}


def _card_json(value: Any) -> dict:
    state = ensure_card_state(value)
    card = ALL_CARDS.get(state)
    if card is None:
        return {
            "id": state.id,
            "name": state.id,
            "desc": "",
            "cost": "",
            "upgraded": state.upgraded,
            "gems": list(state.gems),
        }
    return {
        "id": card.id,
        "name": card.name,
        "desc": card.desc,
        "cost": get_card_cost_str(card),
        "cost_a": card.cost_a,
        "cost_ba": card.cost_ba,
        "type": card.type,
        "color": card.color,
        "rarity": card.rarity,
        "damage_type": getattr(card, "damage_type", "effect"),
        "upgraded": state.upgraded,
        "gems": list(state.gems),
        "exhaust": bool(getattr(card, "exhaust", False)),
        "retain": bool(getattr(card, "retain", False)),
        "agile": bool(getattr(card, "agile", False)),
        "countdown": getattr(card, "countdown", 0),
        "tags": [tag.name for tag in getattr(card, "tags", [])],
    }


def _buff_json(buff) -> dict:
    return {
        "id": getattr(buff, "id", ""),
        "name": getattr(buff, "name", ""),
        "stacks": getattr(buff, "stacks", 0),
        "desc": getattr(buff, "desc", ""),
    }


def _player_json(run: Optional[GameRun]) -> Optional[dict]:
    if run is None or run.player is None:
        return None
    p = run.player
    return {
        "name": p.name,
        "hp": p.hp,
        "max_hp": p.max_hp,
        "shield": p.shield,
        "gold": p.gold,
        "stage": p.stage,
        "actions": p.actions,
        "bonus_actions": p.bonus_actions,
        "selected_class": getattr(p, "selected_class", ""),
        "subclass": getattr(p, "subclass", ""),
        "downed": bool(getattr(p, "downed", False)),
        "relics": [
            {"id": rid, "name": get_relic_name(rid), "desc": get_relic_desc(rid)}
            for rid in p.relics
        ],
        "buffs": [_buff_json(b) for b in p.buffs],
        "potions": [
            {
                "index": index,
                "id": pid,
                "name": get_potion_name(pid),
                "desc": get_potion_desc(pid),
            }
            for index, pid in enumerate(p.potions, 1)
        ],
    }


def _party_json(run: Optional[GameRun]) -> list[dict]:
    if run is None or not getattr(run, "coop_id", ""):
        return []
    data = run.node_data or {}
    stage_ready = data.get("stage_ready", {}) or {}
    turn_ready = data.get("turn_ready", {}) or {}
    result = []
    for slot, uid in enumerate(getattr(run, "party_order", []) or [], 1):
        member = (getattr(run, "players", {}) or {}).get(uid)
        if member is None:
            continue
        result.append({
            "slot": slot,
            "user_id": uid,
            "name": member.name,
            "hp": member.hp,
            "max_hp": member.max_hp,
            "shield": member.shield,
            "gold": member.gold,
            "downed": bool(member.downed or member.hp <= 0),
            "is_self": uid == run.user_id,
            "selected_class": getattr(member, "selected_class", ""),
            "subclass": getattr(member, "subclass", ""),
            "stage_ready": bool(stage_ready.get(uid, False)),
            "turn_ready": bool(turn_ready.get(uid, False)),
        })
    return result


def _enemies_json(run: Optional[GameRun]) -> list[dict]:
    if run is None:
        return []
    result = []
    for index, enemy in enumerate(run.enemies, 1):
        intents = []
        for intent in getattr(enemy, "intents", []) or []:
            intents.append(
                {
                    "type": getattr(intent, "type", ""),
                    "value": getattr(intent, "val", 0),
                    "desc": getattr(intent, "desc", ""),
                    "cost_a": getattr(intent, "cost_a", 0),
                    "cost_ba": getattr(intent, "cost_ba", 0),
                    "cancelled": bool(getattr(intent, "cancelled", False)),
                    "cancelled_desc": getattr(intent, "cancelled_desc", ""),
                }
            )
        result.append(
            {
                "index": index,
                "target": f"e{index}",
                "name": enemy.name,
                "hp": enemy.hp,
                "max_hp": enemy.max_hp,
                "shield": enemy.shield,
                "actions": enemy.actions,
                "bonus_actions": enemy.bonus_actions,
                "is_summon": bool(enemy.is_summon),
                "attack_target": (run.node_data.get("enemy_targets", {}) or {}).get(str(index), ""),
                "buffs": [_buff_json(b) for b in enemy.buffs],
                "intents": intents,
                "intent_a": {
                    "type": enemy.intent_a_type,
                    "value": enemy.intent_a_val,
                    "desc": enemy.intent_a_desc,
                },
                "intent_ba": {
                    "type": enemy.intent_ba_type,
                    "value": enemy.intent_ba_val,
                    "desc": enemy.intent_ba_desc,
                },
            }
        )
    return result


def _minions_json(run: Optional[GameRun]) -> list[dict]:
    if run is None or run.player is None:
        return []
    result = []
    for grid in sorted(run.player.minions, key=lambda value: int(value)):
        minion = run.player.minions[grid]
        result.append(
            {
                "grid": str(grid),
                "target": f"p{grid}",
                "name": minion.name,
                "hp": minion.hp,
                "max_hp": minion.max_hp,
                "atk": minion.atk,
                "actions": minion.actions,
                "bonus_actions": minion.bonus_actions,
                "attack_actions": minion.attack_actions,
                "buffs": [_buff_json(b) for b in minion.buffs],
            }
        )
    return result


def _amulets_json(run: Optional[GameRun]) -> list[dict]:
    if run is None or run.player is None:
        return []
    result = []
    for grid in sorted(run.player.amulets, key=lambda value: int(value)):
        amulet = run.player.amulets[grid]
        result.append(
            {
                "grid": str(grid),
                "name": amulet.name,
                "countdown": amulet.countdown,
                "desc": amulet.desc,
            }
        )
    return result


def _hand_json(run: Optional[GameRun]) -> list[dict]:
    if run is None or run.player is None:
        return []
    hand = []
    for index, value in enumerate(run.player.hand, 1):
        card = _card_json(value)
        card["index"] = index
        hand.append(card)
    return hand


def _deck_json(run: Optional[GameRun]) -> list[dict]:
    if run is None or run.player is None:
        return []
    counts: dict[CardState, int] = {}
    for value in run.player.deck:
        state = ensure_card_state(value)
        counts[state] = counts.get(state, 0) + 1
    ordered = sorted(
        counts.items(),
        key=lambda item: (
            item[0].id,
            1 if item[0].upgraded else 0,
            tuple(item[0].gems or []),
        ),
    )
    return [
        {"index": index, "count": count, "card": _card_json(state)}
        for index, (state, count) in enumerate(ordered, 1)
    ]


def _piles_json(run: Optional[GameRun]) -> dict:
    if run is None or run.player is None:
        return {"draw": 0, "discard": 0, "exhaust": 0, "graveyard": 0}
    p = run.player
    return {
        "draw": len(p.draw_pile),
        "discard": len(p.discard_pile),
        "exhaust": len(p.exhaust_pile),
        "graveyard": len(p.graveyard),
    }


def _map_json(run: Optional[GameRun]) -> Optional[dict]:
    if run is None:
        return None
    nodes = []
    for stage_str, layer in (run.map_data.get("nodes") or {}).items():
        for node in layer:
            nodes.append(
                {
                    "id": node.get("id"),
                    "stage": int(stage_str),
                    "type": node.get("type"),
                    "label": NODE_LABELS.get(node.get("type"), node.get("type")),
                    "next": list(node.get("next", [])),
                }
            )
    for option in (run.node_data or {}).get("options", []):
        if option.get("node_type") != "corpse":
            continue
        nodes.append(
            {
                "id": option.get("node_id"),
                "stage": run.player.stage if run.player else 0,
                "type": "corpse",
                "label": NODE_LABELS["corpse"],
                "next": [],
            }
        )
    reachable = set()
    if run.node_type == "map_select":
        for option in run.node_data.get("options", []):
            node_id = option.get("node_id")
            if node_id:
                reachable.add(node_id)
    return {
        "current": run.map_data.get("current_node_id"),
        "stage": run.player.stage if run.player else 0,
        "nodes": nodes,
        "reachable": sorted(reachable),
        "total_treasures": run.map_data.get("total_treasures"),
    }


def _item_label(item: dict) -> str:
    itype = item.get("type")
    if itype == "gold":
        return f"🪙 {item.get('amount')} 金币"
    if itype == "card_reward":
        return "🃏 卡牌奖励"
    if itype in ("relic", "quest_relic", "boss_relic"):
        rid = item.get("relic_id") or item.get("id")
        return f"🎒 {get_relic_name(rid)}"
    if itype == "gem":
        gid = item.get("gem_id")
        return f"💎 {GEM_CONFIG.get(gid, {}).get('name', gid)}"
    if itype == "potion":
        pid = item.get("potion_id")
        return f"🧪 {get_potion_name(pid)}"
    if itype in ("quest_card", "boss_card"):
        cid = item.get("card_id") or item.get("id")
        card = ALL_CARDS.get(cid)
        return f"🃏 {card.name if card else cid}"
    if itype == "sacrifice":
        return "🧹 献祭卡牌"
    if itype == "remove":
        return "🧹 净化服务"
    if itype == "upgrade":
        return "🔨 强化服务"
    if itype == "leave":
        return "🚪 离开"
    if itype == "card":
        card = ALL_CARDS.get(item.get("card_id"))
        return f"🃏 {card.name if card else item.get('card_id')}"
    if itype == "rest_heal":
        return get_locale_text("render_rest_heal")
    if itype == "rest_meditate":
        return get_locale_text("render_rest_meditate")
    if itype == "rest_upgrade":
        return get_locale_text("render_rest_upgrade")
    if itype == "rest_mend":
        return "🩹 救治队友（恢复 30% 最大生命并净化 1 层负面状态）"
    if itype == "shared_relic":
        rid = item.get("relic_id")
        return f"🎒 共享遗物【{get_relic_name(rid)}】"
    return str(itype or "选项")


def _item_desc(item: dict) -> str:
    itype = item.get("type")
    if itype == "card":
        card = ALL_CARDS.get(item.get("card_id"))
        return card.desc if card else ""
    if itype in ("relic", "quest_relic", "boss_relic"):
        rid = item.get("relic_id") or item.get("id")
        return get_relic_desc(rid)
    if itype == "gem":
        gid = item.get("gem_id")
        return GEM_CONFIG.get(gid, {}).get("desc", "")
    if itype == "potion":
        return get_potion_desc(item.get("potion_id"))
    if itype in ("quest_card", "boss_card"):
        cid = item.get("card_id") or item.get("id")
        card = ALL_CARDS.get(cid)
        return card.desc if card else ""
    if itype == "shared_relic":
        return "全队争夺；多名玩家选择同一遗物时以石头剪刀布裁决，未获得者得到 25 金币补偿。"
    if itype == "rest_mend":
        return "指定一名队友，恢复其 30% 最大生命值并净化 1 层负面状态。"
    return ""


def _option(index: int, kind: str, label: str, **extra) -> dict:
    data = {"index": index, "kind": kind, "label": label}
    data.update(extra)
    return data


def _items_options(items: list[dict], include_taken: bool = False) -> list[dict]:
    options = []
    source = (
        list(enumerate(items, 1))
        if include_taken
        else list(enumerate([item for item in items if not item.get("taken")], 1))
    )
    for index, item in source:
        taken = bool(item.get("taken"))
        sold = bool(item.get("sold"))
        prefix = ""
        if item.get("force"):
            prefix += get_locale_text("label_forced")
        if item.get("group_id"):
            prefix += get_locale_text("label_multi_choice")
        if item.get("bind_group"):
            prefix += get_locale_text("label_bundle")
        options.append(
            _option(
                index,
                item.get("type") or "item",
                prefix + _item_label(item),
                desc=_item_desc(item),
                price=item.get("price"),
                sold=sold,
                taken=taken,
                disabled=sold or taken,
                force=bool(item.get("force")),
            )
        )
    return options


def _options_json(run: Optional[GameRun]) -> list[dict]:
    if run is None:
        return []
    node_type = run.node_type
    data = run.node_data or {}
    if data.get("coop_done"):
        return []
    if data.get("pending_cards") is not None:
        cards = data.get("pending_cards", [])
        options = []
        for index, cid in enumerate(cards, 1):
            card = _card_json(CardState(id=cid, upgraded=bool(data.get("pending_card_upgraded"))))
            options.append(
                _option(
                    index,
                    "card",
                    f"🃏 {card['name']}",
                    desc=card["desc"],
                    cost=card["cost"],
                    card_id=cid,
                )
            )
        if data.get("pending_card_can_skip", True):
            options.append(_option(len(cards) + 1, "skip", "跳过本次选卡"))
        return options
    if node_type == "map_select":
        options = []
        for index, option in enumerate(data.get("options", []), 1):
            label = NODE_LABELS.get(
                option.get("node_type"), option.get("node_type", "")
            )
            description = str(option.get("desc", ""))
            while description.startswith(label + " ("):
                description = description[len(label) + 2 : -1]
            if description.startswith(label + " "):
                description = description[len(label) + 1 :]
            options.append(
                _option(
                    index,
                    "node",
                    label,
                    desc=description,
                    node_type=option.get("node_type"),
                    node_id=option.get("node_id"),
                )
            )
        return options
    if node_type in ("start_ancient", "ancient"):
        options = []
        for index, option in enumerate(data.get("options", []), 1):
            relic_id = option.get("relic")
            card_id = option.get("card")
            relic_name = get_relic_name(relic_id) if relic_id else ""
            card_name = ALL_CARDS[card_id].name if card_id in ALL_CARDS else card_id
            if option.get("type") == "double":
                label = f"⚖️ 遗物【{relic_name}】"
                desc = get_relic_desc(relic_id) if relic_id else ""
            else:
                prefix = "🕸️ 契约" if node_type == "start_ancient" else "🎁 赐福包"
                label = f"{prefix}【{relic_name}】 + 卡牌【{card_name}】"
                desc = (
                    f"{get_relic_desc(relic_id)}；{ALL_CARDS[card_id].desc}"
                    if relic_id and card_id in ALL_CARDS
                    else ""
                )
            options.append(
                _option(
                    index,
                    "blessing" if option.get("type") != "double" else "relic",
                    label,
                    desc=desc,
                    relic_id=relic_id,
                    card_id=card_id,
                )
            )
        return options
    if node_type == "event":
        return [
            _option(index, "event", option.get("text", ""), action=option.get("action"))
            for index, option in enumerate(data.get("options", []), 1)
        ]
    if node_type == "shop":
        return _items_options(data.get("items", []), include_taken=True)
    if node_type == "rest":
        if data.get("pending_upgrade"):
            return []
        items = data.get("items", [])
        if not items:
            return [
                _option(1, "rest_heal", get_locale_text("render_rest_heal")),
                _option(2, "rest_meditate", get_locale_text("render_rest_meditate")),
                _option(3, "rest_upgrade", get_locale_text("render_rest_upgrade")),
            ]
        return _items_options(items, include_taken=True)
    if node_type in ("reward", "treasure", "boss_chest"):
        if node_type == "treasure" and data.get("state", "pending_remove") == "pending_remove":
            return []
        return _items_options(data.get("items", []))
    if node_type == "corpse_reward":
        cards = data.get("cards", [])
        options = []
        for index, value in enumerate(cards, 1):
            state = ensure_card_state(value)
            card = _card_json(state)
            label = f"🃏 {card['name']}"
            if state.upgraded:
                label += " [已升级]"
            if state.gems:
                label += f" [宝石:{','.join(state.gems)}]"
            options.append(
                _option(
                    index,
                    "card",
                    label,
                    desc=card["desc"],
                    cost=card["cost"],
                    card_id=state.id,
                )
            )
        options.append(
            _option(len(cards) + 1, "skip", "跳过本次选卡")
        )
        return options
    if node_type == "card_select":
        cards = data.get("cards", [])
        options = []
        for index, cid in enumerate(cards, 1):
            card = _card_json(CardState(id=cid, upgraded=bool(data.get("force_upgraded"))))
            options.append(
                _option(
                    index,
                    "card",
                    f"🃏 {card['name']}",
                    desc=card["desc"],
                    cost=card["cost"],
                    card_id=cid,
                )
            )
        if data.get("can_skip", True):
            skip_label = get_locale_text(
                "render_card_select_skip", skip_idx=len(cards) + 1
            )
            skip_label = re.sub(r"^\s*\[\d+\]\s*", "", skip_label)
            options.append(_option(len(cards) + 1, "skip", skip_label))
        return options
    return []


def _pending_action(run: Optional[GameRun]) -> Optional[str]:
    if run is None:
        return None
    data = run.node_data or {}
    stack = data.get("state_stack") or []
    if stack:
        return stack[-1].get("type")
    if data.get("pending_cards") is not None:
        return "card_reward"
    if data.get("pending_upgrade"):
        return "upgrade_card"
    if data.get("pending_remove"):
        return "remove_card"
    if run.node_type == "gem_insert":
        return "gem_card"
    if run.node_type == "treasure" and data.get("state", "pending_remove") == "pending_remove":
        return "sacrifice_card"
    return None


def _screen(run: Optional[GameRun], stats: UserStats) -> str:
    if run is not None:
        if run.node_type == "cafe":
            return "cafe"
        return run.node_type
    if stats is not None and getattr(stats, "in_town", False):
        if stats.town_flags.get("current_dialog"):
            return "dialog"
        return "town"
    return "menu"


def build_snapshot(run: Optional[GameRun], stats: Optional[UserStats], text: str = "") -> dict:
    stats = stats or UserStats()
    screen = _screen(run, stats)
    return {
        "v": 1,
        "screen": screen,
        "screen_label": SCREEN_LABELS.get(screen, screen),
        "text": text,
        "player": _player_json(run),
        "party": _party_json(run),
        "coop": bool(getattr(run, "coop_id", "")) if run is not None else False,
        "enemies": _enemies_json(run),
        "minions": _minions_json(run),
        "amulets": _amulets_json(run),
        "hand": _hand_json(run),
        "deck": _deck_json(run),
        "piles": _piles_json(run),
        "map": _map_json(run),
        "options": _options_json(run),
        "pending_action": _pending_action(run),
        "stats": {
            "gp": stats.gp,
            "total_damage": stats.total_damage,
            "total_kills": stats.total_kills,
            "total_stages": stats.total_stages,
            "rogue_mode": bool(stats.rogue_mode),
            "in_town": bool(stats.in_town),
            "selected_class": stats.selected_class,
            "selected_subclass": stats.selected_subclass,
        },
    }
