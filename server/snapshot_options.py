import re
from typing import Optional

from game.cards import ALL_CARDS
from game.data.gem_data import GEM_CONFIG
from game.data.locale_data import get_locale_text, t
from game.data.potion_data import get_potion_desc, get_potion_name
from game.entities import get_relic_desc, get_relic_name
from game.models.state import CardState, GameRun, ensure_card_state


def _item_label(item: dict) -> str:
    itype = item.get("type")
    if itype == "gold":
        return t("snapshot.item_gold", amount=item.get("amount"))
    if itype == "card_reward":
        return t("snapshot.item_card_reward")
    if itype in ("relic", "quest_relic", "boss_relic"):
        rid = item.get("relic_id") or item.get("id")
        return t("snapshot.item_relic", name=get_relic_name(rid))
    if itype == "gem":
        gid = item.get("gem_id")
        return t("snapshot.item_gem", name=GEM_CONFIG.get(gid, {}).get("name", gid))
    if itype == "potion":
        pid = item.get("potion_id")
        return t("snapshot.item_potion", name=get_potion_name(pid))
    if itype in ("quest_card", "boss_card"):
        cid = item.get("card_id") or item.get("id")
        card = ALL_CARDS.get(cid)
        return t("snapshot.card_label", name=card.name if card else cid)
    if itype == "sacrifice":
        return t("snapshot.item_sacrifice")
    if itype == "remove":
        return t("snapshot.item_remove")
    if itype == "upgrade":
        return t("snapshot.item_upgrade")
    if itype == "leave":
        return t("snapshot.item_leave")
    if itype == "card":
        card = ALL_CARDS.get(item.get("card_id"))
        return t("snapshot.card_label", name=card.name if card else item.get("card_id"))
    if itype == "rest_heal":
        return get_locale_text("render_rest_heal")
    if itype == "rest_meditate":
        return get_locale_text("render_rest_meditate")
    if itype == "rest_upgrade":
        return get_locale_text("render_rest_upgrade")
    if itype == "rest_mend":
        return t("snapshot.item_rest_mend")
    if itype == "shared_relic":
        rid = item.get("relic_id")
        return t("snapshot.item_shared_relic", name=get_relic_name(rid))
    return str(itype or t("snapshot.item_default"))


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
        return t("snapshot.desc_shared_relic")
    if itype == "rest_mend":
        return t("snapshot.desc_rest_mend")
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
    from .snapshot import NODE_LABELS, _card_json

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
                    t("snapshot.card_label", name=card["name"]),
                    desc=card["desc"],
                    cost=card["cost"],
                    card_id=cid,
                )
            )
        if data.get("pending_card_can_skip", True):
            options.append(_option(len(cards) + 1, "skip", t("snapshot.option_skip")))
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
                label = t("snapshot.option_double_relic", name=relic_name)
                desc = get_relic_desc(relic_id) if relic_id else ""
            else:
                prefix = (
                    t("snapshot.blessing_contract")
                    if node_type == "start_ancient"
                    else t("snapshot.blessing_pack")
                )
                label = t(
                    "snapshot.option_blessing",
                    prefix=prefix,
                    relic=relic_name,
                    card=card_name,
                )
                desc = (
                    t(
                        "snapshot.blessing_desc",
                        relic_desc=get_relic_desc(relic_id),
                        card_desc=ALL_CARDS[card_id].desc,
                    )
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
            label = t("snapshot.card_label", name=card["name"])
            if state.upgraded:
                label += t("snapshot.card_upgraded")
            if state.gems:
                label += t("snapshot.card_gems", gems=",".join(state.gems))
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
            _option(len(cards) + 1, "skip", t("snapshot.option_skip"))
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
                    t("snapshot.card_label", name=card["name"]),
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
