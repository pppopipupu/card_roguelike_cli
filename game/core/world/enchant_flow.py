import random
from ...data.enchantment_data import (
    ENCHANTMENT_CONFIG,
    FORCED_EVENT_ENCHANT_POOL,
    REST_ENCHANT_OFFER_COUNT,
    SHOP_ENCHANT_OFFER_COUNT,
)
from ...data.locale_data import get_locale_text
from ...entities import ALL_CARDS
from ...models.coop_view import strip_shared
from ...models.state import GameRun, ensure_card_state
from ..inventory.deck_service import DeckService
from ..inventory.enchantment_service import (
    get_enchantment_desc,
    get_enchantment_name,
    get_enchantment_rarity_label,
    is_card_enchantable,
    preview_enchant_card,
    roll_enchantments,
)
from ..party.coordinator import begin_party_gem, end_party_gem, finish_player_node


def _sorted_enchantable_deck(player) -> list:
    counts = {}
    for c in player.deck:
        st = ensure_card_state(c)
        if not is_card_enchantable(st):
            continue
        counts[st] = counts.get(st, 0) + 1

    def _key(item):
        st = item[0]
        return (st.id, 1 if st.upgraded else 0, tuple(st.gems or []), tuple(st.enchantments or []))

    return sorted(counts.items(), key=_key)


def start_enchant_flow(
    explore_engine,
    run: GameRun,
    source: str,
    next_node_type: str,
    next_node_data: dict,
    price: int = 0,
    offers: list[str] | None = None,
) -> str:
    sorted_items = _sorted_enchantable_deck(run.player)
    if not sorted_items:
        return get_locale_text("i18n_enchantment.ui.enchant_no_cards")
    offer_count = SHOP_ENCHANT_OFFER_COUNT if source == "shop" else REST_ENCHANT_OFFER_COUNT
    rolled = list(offers) if offers else roll_enchantments(offer_count)
    previous = run.node_data
    clean_next = strip_shared(next_node_data)
    run.node_type = "enchant_card"
    run.node_data = {
        "stage": "choose_enchant",
        "source": source,
        "price": int(price),
        "offers": rolled,
        "selected_enchant": "",
        "selected_card_idx": 0,
        "preview": None,
        "next_node_type": next_node_type,
        "next_node_data": clean_next,
    }
    begin_party_gem(run, previous)
    explore_engine.save_manager.save_save(run.user_id, run)
    return render_enchant_card(run)


def enchant_cancel(explore_engine, run: GameRun) -> str:
    data = run.node_data
    next_type = data.get("next_node_type", "grid_map")
    next_data = data.get("next_node_data", {})
    end_party_gem(run, data, next_type, next_data)
    explore_engine.save_manager.save_save(run.user_id, run)
    return get_locale_text("i18n_enchantment.ui.enchant_cancelled")


def enchant_choose(explore_engine, run: GameRun, option_idx: int) -> str:
    data = run.node_data
    stage = data.get("stage", "choose_enchant")

    if stage == "choose_enchant":
        if option_idx == 0:
            return enchant_cancel(explore_engine, run)
        offers = list(data.get("offers") or [])
        if option_idx < 1 or option_idx > len(offers):
            return get_locale_text("err_invalid_option_idx")
        data["selected_enchant"] = offers[option_idx - 1]
        data["stage"] = "choose_card"
        explore_engine.save_manager.save_save(run.user_id, run)
        return render_enchant_card(run)

    if stage == "choose_card":
        if option_idx == 0:
            data["stage"] = "choose_enchant"
            data["selected_enchant"] = ""
            explore_engine.save_manager.save_save(run.user_id, run)
            return render_enchant_card(run)
        sorted_items = _sorted_enchantable_deck(run.player)
        if option_idx < 1 or option_idx > len(sorted_items):
            return get_locale_text("err_invalid_card_idx")
        c_state = sorted_items[option_idx - 1][0]
        eid = str(data.get("selected_enchant") or "")
        if eid not in ENCHANTMENT_CONFIG:
            return get_locale_text("err_invalid_option_idx")
        data["selected_card_idx"] = option_idx
        data["preview"] = preview_enchant_card(c_state, eid)
        data["stage"] = "confirm_preview"
        explore_engine.save_manager.save_save(run.user_id, run)
        return render_enchant_card(run)

    if stage == "confirm_preview":
        if option_idx in (0, 3):
            return enchant_cancel(explore_engine, run)
        if option_idx == 2:
            data["stage"] = "choose_card"
            data["preview"] = None
            explore_engine.save_manager.save_save(run.user_id, run)
            return render_enchant_card(run)
        if option_idx != 1:
            return get_locale_text("err_invalid_option_idx")

        p = run.player
        source = data.get("source", "rest")
        price = int(data.get("price", 0) or 0)
        if source == "shop" and p.gold < price:
            return get_locale_text("i18n_explore_core.err_not_enough_gold", price=price, gold=p.gold)
        sorted_items = _sorted_enchantable_deck(p)
        card_idx = int(data.get("selected_card_idx", 0) or 0)
        if card_idx < 1 or card_idx > len(sorted_items):
            return get_locale_text("err_invalid_card_idx")
        eid = str(data.get("selected_enchant") or "")
        if eid not in ENCHANTMENT_CONFIG:
            return get_locale_text("err_invalid_option_idx")

        target_state = sorted_items[card_idx - 1][0]
        before_name = ALL_CARDS[target_state].name
        new_state = DeckService.clone_state(target_state)
        new_state.enchantments = list(new_state.enchantments or []) + [eid]
        p.deck.remove(target_state)
        p.deck.append(new_state)
        after_name = ALL_CARDS[new_state].name
        enchant_name = get_enchantment_name(eid)

        next_type = data.get("next_node_type", "grid_map")
        next_data = data.get("next_node_data", {})
        if source == "shop":
            p.gold -= price
            for item in next_data.get("items", []):
                if item.get("type") == "enchant":
                    item["sold"] = True
            end_party_gem(run, data, next_type, next_data)
            explore_engine.save_manager.save_save(run.user_id, run)
            return get_locale_text(
                "i18n_enchantment.ui.enchant_success",
                before_name=before_name,
                enchant_name=enchant_name,
                after_name=after_name,
            )

        end_party_gem(run, data, next_type, next_data)
        for it in run.node_data.get("items", []):
            it["taken"] = True
        msg = get_locale_text(
            "i18n_enchantment.ui.enchant_success",
            before_name=before_name,
            enchant_name=enchant_name,
            after_name=after_name,
        )
        return finish_player_node(explore_engine.save_manager, explore_engine.map_engine, run, run.user_id, msg)

    return get_locale_text("err_invalid_option_idx")


def render_enchant_card(run: GameRun) -> str:
    from ...renderer.menu import get_card_cost_str
    from ...entities.cards.base import get_card_color_icon
    data = run.node_data
    stage = data.get("stage", "choose_enchant")
    sep = get_locale_text("renderer_explore.separator")
    lines = [sep]

    if stage == "choose_enchant":
        lines.append(get_locale_text("i18n_enchantment.ui.choose_enchant_title"))
        for idx, eid in enumerate(data.get("offers") or [], 1):
            lines.append(
                get_locale_text(
                    "i18n_enchantment.ui.choose_enchant_item",
                    idx=idx,
                    name=get_enchantment_name(eid),
                    rarity=get_enchantment_rarity_label(eid),
                    desc=get_enchantment_desc(eid),
                )
            )
        lines.append(sep)
        lines.append(get_locale_text("i18n_enchantment.ui.choose_enchant_hint"))
        lines.append(sep)
        return "\n".join(lines)

    if stage == "choose_card":
        eid = str(data.get("selected_enchant") or "")
        lines.append(
            get_locale_text(
                "i18n_enchantment.ui.choose_card_title",
                enchant_name=get_enchantment_name(eid),
            )
        )
        lines.append(
            get_locale_text(
                "i18n_enchantment.ui.choose_card_desc",
                enchant_desc=get_enchantment_desc(eid),
            )
        )
        sorted_items = _sorted_enchantable_deck(run.player)
        for idx, (st, cnt) in enumerate(sorted_items, 1):
            card = ALL_CARDS[st]
            icon = get_card_color_icon(card)
            cost_str = get_card_cost_str(card)
            qty = f" x{cnt}" if cnt > 1 else ""
            lines.append(f"  [{idx}] {icon}[{cost_str}] {card.name}{qty} - {card.desc}")
        lines.append(sep)
        lines.append(get_locale_text("i18n_enchantment.ui.choose_card_hint"))
        lines.append(sep)
        return "\n".join(lines)

    eid = str(data.get("selected_enchant") or "")
    preview = data.get("preview") or {}
    lines.append(get_locale_text("i18n_enchantment.ui.preview_title"))
    lines.append(
        get_locale_text(
            "i18n_enchantment.ui.preview_enchant_line",
            enchant_name=get_enchantment_name(eid),
            rarity=get_enchantment_rarity_label(eid),
            desc=get_enchantment_desc(eid),
        )
    )
    if preview.get("name_changed"):
        lines.append(
            get_locale_text(
                "i18n_enchantment.ui.preview_name_changed",
                before_name=preview.get("before_name", ""),
                after_name=preview.get("after_name", ""),
            )
        )
    else:
        lines.append(
            get_locale_text(
                "i18n_enchantment.ui.preview_name_same",
                after_name=preview.get("after_name", ""),
            )
        )
    lines.append(
        get_locale_text(
            "i18n_enchantment.ui.preview_before",
            before_cost=preview.get("before_cost", ""),
            before_name=preview.get("before_name", ""),
            before_desc=preview.get("before_desc", ""),
        )
    )
    lines.append(
        get_locale_text(
            "i18n_enchantment.ui.preview_after",
            after_cost=preview.get("after_cost", ""),
            after_name=preview.get("after_name", ""),
            after_desc=preview.get("after_desc", ""),
        )
    )
    if data.get("source") == "shop":
        lines.append(
            get_locale_text(
                "i18n_enchantment.ui.preview_cost_gold",
                price=int(data.get("price", 0) or 0),
                gold=run.player.gold,
            )
        )
    lines.append("")
    lines.append(get_locale_text("i18n_enchantment.ui.preview_opt_confirm"))
    lines.append(get_locale_text("i18n_enchantment.ui.preview_opt_reselect"))
    lines.append(get_locale_text("i18n_enchantment.ui.preview_opt_cancel"))
    lines.append(sep)
    lines.append(get_locale_text("i18n_enchantment.ui.preview_prompt"))
    lines.append(sep)
    return "\n".join(lines)


def apply_forced_event_enchant(run: GameRun, enchantment_id: str = "") -> tuple[str, str, str] | None:
    p = run.player
    eligible = [c for c in p.deck if is_card_enchantable(c)]
    if not eligible:
        return None
    target_state = random.choice(eligible)
    eid = enchantment_id if enchantment_id in ENCHANTMENT_CONFIG else roll_enchantments(1, FORCED_EVENT_ENCHANT_POOL)[0]
    before_name = ALL_CARDS[target_state].name
    new_state = DeckService.clone_state(target_state)
    new_state.enchantments = list(new_state.enchantments or []) + [eid]
    p.deck.remove(target_state)
    p.deck.append(new_state)
    after_name = ALL_CARDS[new_state].name
    return before_name, after_name, get_enchantment_name(eid)
