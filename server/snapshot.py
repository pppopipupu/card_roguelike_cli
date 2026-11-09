from typing import Any, Optional

from game.cards import ALL_CARDS
from game.data.locale_data import t
from game.data.potion_data import get_potion_desc, get_potion_name
from game.entities import get_relic_desc, get_relic_name
from game.models.state import CardState, GameRun, UserStats, ensure_card_state, public_player_id
from game.renderer.formatters import get_effective_max_hp
from game.renderer.menu import get_card_cost_str

from .snapshot_options import _options_json


NODE_LABELS = {
    "battle": t("snapshot.node_battle"),
    "elite": t("snapshot.node_elite"),
    "event": t("snapshot.node_event"),
    "shop": t("snapshot.node_shop"),
    "rest": t("snapshot.node_rest"),
    "treasure": t("snapshot.node_treasure"),
    "boss": t("snapshot.node_boss"),
    "corpse": t("snapshot.node_corpse"),
}

SCREEN_LABELS = {
    "map_select": t("snapshot.screen_map_select"),
    "start_ancient": t("snapshot.screen_start_ancient"),
    "ancient": t("snapshot.screen_ancient"),
    "battle": t("snapshot.screen_battle"),
    "event": t("snapshot.screen_event"),
    "shop": t("snapshot.screen_shop"),
    "rest": t("snapshot.screen_rest"),
    "reward": t("snapshot.screen_reward"),
    "treasure": t("snapshot.screen_treasure"),
    "card_select": t("snapshot.screen_card_select"),
    "boss_chest": t("snapshot.screen_boss_chest"),
    "corpse_reward": t("snapshot.screen_corpse_reward"),
    "gem_insert": t("snapshot.screen_gem_insert"),
    "cafe": t("snapshot.screen_cafe"),
    "victory": t("snapshot.screen_victory"),
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
        "max_hp": get_effective_max_hp(p),
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
            "id": public_player_id(uid),
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
