import random
from ....data.locale_data import get_locale_text
from ....data.room_interact_data import ROOM_NPCS, ROOM_PROPS, SHOP_DIALOG_CONFIG
from ....entities import ALL_CARDS, get_relic_desc, get_relic_name
from ...inventory.bag_service import get_bag_max_weight, get_bag_weight, get_item_display_name
from .npc_dialog import start_npc_combat
from .interact import _reveal_any_special, format_room_env_with_props, get_current_room

def apply_shop_price_multiplier(items: list, mult: float) -> None:
    for item in items:
        if item.get("type") == "leave" or item.get("sold"):
            continue
        base = item.get("base_price")
        if base is None:
            base = int(item.get("price", 0))
            item["base_price"] = base
        item["price"] = max(1, int(round(base * mult)))


def init_shop_view_flags(run, view_data: dict, enter_lobby: bool) -> None:
    room, _ = get_current_room(run)
    merchant_dead = bool(room.shared_payload.get("merchant_defeated")) if room is not None else False
    view_data["entered_via_lobby"] = bool(enter_lobby or merchant_dead)
    view_data["merchant_defeated"] = merchant_dead
    if enter_lobby or merchant_dead:
        view_data["shop_mode"] = "lobby"
    else:
        view_data["shop_mode"] = "wares"
    view_data["dialog_state"] = "start"
    view_data["haggled"] = False
    view_data["discount_mult"] = 1.0


def open_shop_dialog(explore_engine, run) -> str:
    if run.node_data.get("merchant_defeated"):
        return get_locale_text("i18n_room_interact.shop.lobby_merchant_dead")
    run.node_data["shop_mode"] = "dialog"
    run.node_data["dialog_state"] = "start"
    explore_engine.save_manager.save_save(run.user_id, run)
    return render_shop_view(run)


def render_shop_view(run) -> str:
    from ....renderer.explore import render_shop_wares
    mode = run.node_data.get("shop_mode", "wares")
    if mode == "wares":
        return render_shop_wares(run)
    p = run.player
    room, coord = get_current_room(run)
    merchant_dead = bool(run.node_data.get("merchant_defeated")) or (room is not None and bool(room.shared_payload.get("merchant_defeated")))
    from ....renderer.formatters import format_persistent_buff_bar
    lines = [
        get_locale_text("renderer_explore.separator"),
        get_locale_text("i18n_room_interact.shop.lobby_title", stage=p.stage) if mode == "lobby" else get_locale_text("i18n_room_interact.shop.dialog_title"),
        get_locale_text("renderer_explore.status_line", name=p.name, hp=p.hp, max_hp=p.max_hp, gold=p.gold) + format_persistent_buff_bar(p),
        "",
    ]
    if mode == "lobby":
        if room is not None:
            lines.append(format_room_env_with_props(room, include_cleared_suffix=False))
            if room.items:
                inames = [f"【{get_item_display_name(it)}】" for it in room.items]
                lines.append(get_locale_text("i18n_room_interact.room_ui.items_line", items="、".join(inames)))
        lines.append("")
        if merchant_dead:
            lines.append(get_locale_text("i18n_room_interact.shop.lobby_merchant_dead"))
            lines.append("")
            lines.append(f" [1] {get_locale_text('i18n_room_interact.shop.lobby_opt_leave')}")
        else:
            lines.append(get_locale_text("i18n_room_interact.shop.lobby_merchant_alive"))
            lines.append("")
            lines.append(f" [1] {get_locale_text('i18n_room_interact.shop.lobby_opt_talk')}")
            lines.append(f" [2] {get_locale_text('i18n_room_interact.shop.lobby_opt_attack')}")
            lines.append(f" [3] {get_locale_text('i18n_room_interact.shop.lobby_opt_leave')}")
        lines.append("")
        lines.append(get_locale_text("renderer_explore.guide_folded") if p.fold_guide else get_locale_text("i18n_room_interact.room_ui.interact_hints"))
        lines.append(get_locale_text("renderer_explore.separator"))
        return "\n".join(lines)

    lines.append(get_locale_text("i18n_room_interact.shop.dialog_greeting"))
    lines.append("")
    lines.append(f" [1] {get_locale_text('i18n_room_interact.shop.dialog_opt_wares')}")
    lines.append(f" [2] {get_locale_text('i18n_room_interact.shop.dialog_opt_haggle')}")
    lines.append(f" [3] {get_locale_text('i18n_room_interact.shop.dialog_opt_pawn', gold=SHOP_DIALOG_CONFIG['pawn_item_gold'])}")
    lines.append(f" [4] {get_locale_text('i18n_room_interact.shop.dialog_opt_intel', cost=SHOP_DIALOG_CONFIG['intel_cost'])}")
    lines.append(f" [5] {get_locale_text('i18n_room_interact.shop.dialog_opt_extort')}")
    lines.append(f" [6] {get_locale_text('i18n_room_interact.shop.dialog_opt_back')}")
    lines.append("")
    lines.append(get_locale_text("renderer_explore.guide_folded") if p.fold_guide else get_locale_text("i18n_room_interact.shop.dialog_footer"))
    lines.append(get_locale_text("renderer_explore.separator"))
    return "\n".join(lines)

def handle_shop_lobby_or_dialog_choice(explore_engine, run, option_idx: int) -> str | None:
    from ...party.coordinator import finish_player_node
    mode = run.node_data.get("shop_mode", "wares")
    if mode == "wares":
        return None
    room, _ = get_current_room(run)
    merchant_dead = bool(run.node_data.get("merchant_defeated")) or (room is not None and bool(room.shared_payload.get("merchant_defeated")))
    if mode == "lobby":
        if merchant_dead:
            if option_idx == 1:
                msg = get_locale_text("i18n_explore_core.shop_leave_next")
                return finish_player_node(explore_engine.save_manager, explore_engine.map_engine, run, run.user_id, msg)
            return get_locale_text("err_invalid_option_idx")
        if option_idx == 1:
            return open_shop_dialog(explore_engine, run)
        if option_idx == 2:
            return start_npc_combat(explore_engine.map_engine, run, "shop_merchant", npc_source="shop")
        if option_idx == 3:
            msg = get_locale_text("i18n_explore_core.shop_leave_next")
            return finish_player_node(explore_engine.save_manager, explore_engine.map_engine, run, run.user_id, msg)
        return get_locale_text("err_invalid_option_idx")

    p = run.player
    if option_idx == 1:
        run.node_data["shop_mode"] = "wares"
        explore_engine.save_manager.save_save(run.user_id, run)
        return render_shop_view(run)
    if option_idx == 2:
        if run.node_data.get("haggled"):
            return get_locale_text("i18n_room_interact.shop.haggle_already")
        run.node_data["haggled"] = True
        if random.random() < SHOP_DIALOG_CONFIG["haggle_success_chance"]:
            mult = SHOP_DIALOG_CONFIG["haggle_discount"]
            run.node_data["discount_mult"] = mult
            apply_shop_price_multiplier(run.node_data.get("items", []), mult)
            explore_engine.save_manager.save_save(run.user_id, run)
            return get_locale_text("i18n_room_interact.shop.haggle_success")
        mult = SHOP_DIALOG_CONFIG["haggle_penalty"]
        run.node_data["discount_mult"] = mult
        apply_shop_price_multiplier(run.node_data.get("items", []), mult)
        explore_engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_room_interact.shop.haggle_fail")
    if option_idx == 3:
        bag_items = getattr(p, "bag_items", None) or []
        if not bag_items:
            return get_locale_text("i18n_room_interact.shop.pawn_empty")
        sold_id = bag_items.pop(0)
        gain = SHOP_DIALOG_CONFIG["pawn_item_gold"]
        p.gold += gain
        explore_engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_room_interact.shop.pawn_success", item=get_item_display_name(sold_id), gold=gain)
    if option_idx == 4:
        cost = SHOP_DIALOG_CONFIG["intel_cost"]
        if p.gold < cost:
            return get_locale_text("i18n_room_interact.dialog.err_gold", cost=cost)
        fm = getattr(run, "floor_map", None)
        revealed = _reveal_any_special(fm, 2) if fm is not None else []
        if not revealed:
            return get_locale_text("i18n_room_interact.shop.intel_none")
        p.gold -= cost
        explore_engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_room_interact.shop.intel_success", coords="、".join(revealed))
    if option_idx == 5:
        if random.random() < SHOP_DIALOG_CONFIG["extort_success_chance"]:
            p.gold += 40
            apply_shop_price_multiplier(run.node_data.get("items", []), 0.75)
            run.node_data["haggled"] = True
            explore_engine.save_manager.save_save(run.user_id, run)
            return get_locale_text("i18n_room_interact.shop.extort_success", gold=40)
        msg = get_locale_text("i18n_room_interact.shop.extort_fail")
        battle_res = start_npc_combat(explore_engine.map_engine, run, "shop_merchant", npc_source="shop")
        return f"{msg}\n{battle_res}"
    if option_idx == 6:
        run.node_data["shop_mode"] = "lobby"
        explore_engine.save_manager.save_save(run.user_id, run)
        return render_shop_view(run)
    return get_locale_text("err_invalid_option_idx")
