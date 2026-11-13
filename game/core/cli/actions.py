from typing import Tuple
from .base import ActionHandler, find_hand_index_by_initials, normalize_initial_query
from ...entities import ALL_CARDS
from ...data.locale_data import get_locale_text

def check_battle_outcome(router, user_id, run, res, success):
    if run.player.hp <= 0:
        settle_msg = router.save_manager.settle_game_and_delete(user_id, run, is_victory=False)
        if len(run.human_uids()) > 1:
            return get_locale_text("i18n_cli_core.battle_downed_coop", res=res, settle_msg=settle_msg), True, success
        return get_locale_text("i18n_cli_core.battle_defeated", res=res, settle_msg=settle_msg), True, success
    if router.engine.is_battle_won(run):
        router.engine._handle_battle_win(run)
        if run.node_type == "victory":
            settle_msg = router.save_manager.settle_game_and_delete(user_id, run, is_victory=True)
            boss_name = run.node_data.get("boss_name")
            if not boss_name and run.enemies:
                boss_name = run.enemies[0].name
            if not boss_name:
                boss_name = get_locale_text("i18n_cli_core.final_boss_default")
            return get_locale_text("i18n_cli_core.battle_victory_full", res=res, boss_name=boss_name, settle_msg=settle_msg), True, success
        return get_locale_text("i18n_cli_core.battle_won", res=res), True, success
    return res, False, success

class UseAction(ActionHandler, actions=["使用", "p"]):
    def execute(self, router, user_id: str, run, parts: list[str]) -> Tuple[str, bool, bool]:
        if len(parts) < 2:
            return get_locale_text("i18n_cli_core.err_use_usage"), False, False
        arg = parts[1]
        try:
            idx = int(arg)
        except ValueError:
            query = normalize_initial_query(arg)
            if not query:
                return get_locale_text("i18n_cli_core.err_use_arg_type"), False, False
            idx = find_hand_index_by_initials(run.player.hand, query)
            if idx is None:
                return get_locale_text("i18n_cli_core.err_use_initials_not_found", query=query), False, False
        target = " ".join(parts[2:]) if len(parts) > 2 else None
        res = router.engine.play_card(run, idx, target)
        success = "❌" not in res
        return check_battle_outcome(router, user_id, run, res, success)

class MinionAction(ActionHandler, actions=["随从", "m"]):
    def execute(self, router, user_id: str, run, parts: list[str]) -> Tuple[str, bool, bool]:
        if len(parts) < 3:
            return get_locale_text("i18n_cli_core.err_minion_usage"), False, False
        my_grid_raw = parts[1]
        action = parts[2]
        if my_grid_raw in ("all", "所有", "*"):
            grids = sorted(list(run.player.minions.keys()))
        else:
            grids = []
            for p_g in my_grid_raw.split(','):
                g = p_g.strip().replace("p", "")
                if g in run.player.minions:
                    grids.append(g)
        if not grids:
            return get_locale_text("i18n_cli_core.err_minion_grid_not_found", my_grid_raw=my_grid_raw), False, False
        results = []
        for g in grids:
            outcome = check_battle_outcome(router, user_id, run, "\n".join(results), not any("❌" in r for r in results) if results else False)
            if outcome[1]:
                return outcome
            if action in ("攻击", "a", "attack"):
                opp_grid = parts[3] if len(parts) > 3 else None
                res = router.engine.minion_attack(run, g, opp_grid)
                results.append(res)
            elif action in ("技能", "s", "skill"):
                skill_idx = 1
                target = None
                if len(parts) > 3:
                    try:
                        skill_idx = int(parts[3])
                        if len(parts) > 4:
                            target = parts[4]
                    except ValueError:
                        target = parts[3]
                res = router.engine.minion_skill(run, g, skill_idx, target)
                results.append(res)
            else:
                return get_locale_text("i18n_cli_core.err_minion_unknown"), False, False
        res_combined = "\n".join(results)
        success = not any("❌" in r for r in results) if results else False
        return check_battle_outcome(router, user_id, run, res_combined, success)

class ChooseAction(ActionHandler, actions=["选择", "c"]):
    def execute(self, router, user_id: str, run, parts: list[str]) -> Tuple[str, bool, bool]:
        if len(parts) < 2:
            return get_locale_text("i18n_cli_core.err_choose_need_index"), False, False
        try:
            idx = int(parts[1])
        except ValueError:
            arg = parts[1].lower()
            if arg in ("取消", "cancel", "返回", "quit", "exit", "leave", "lv", "0", "离开", "退出"):
                if run.node_data.get("pending_remove"):
                    run.node_data["pending_remove"] = False
                    router.save_manager.save_save(user_id, run)
                    return get_locale_text("i18n_cli_core.msg_cancel_remove"), False, True
                if run.node_data.get("pending_upgrade"):
                    run.node_data["pending_upgrade"] = False
                    router.save_manager.save_save(user_id, run)
                    return get_locale_text("i18n_cli_core.msg_cancel_upgrade"), False, True
                if run.node_type == "gem_insert":
                    res = router.engine.gem_insert_cancel(run)
                    return res, False, "❌" not in res
                if run.node_type == "shop" and (
                    run.node_data.get("shop_mode") == "dialog"
                    or (run.node_data.get("shop_mode") == "wares" and run.node_data.get("entered_via_lobby"))
                ):
                    from ..world.rooms.shop_dialog import render_shop_view
                    run.node_data["shop_mode"] = "lobby"
                    router.save_manager.save_save(user_id, run)
                    return render_shop_view(run), False, True
                if run.node_type in ("reward", "treasure", "boss_chest", "rest", "shop", "life_merchant"):
                    items = run.node_data.get("items", [])
                    forced_items = [it for it in items if it.get("force") and not it.get("taken")]
                    if forced_items:
                        forced_names = []
                        for it in forced_items:
                            itype = it.get("type")
                            if itype == "card_reward":
                                forced_names.append(get_locale_text("i18n_cli_core.reward_card_name"))
                            elif itype == "gold":
                                forced_names.append(get_locale_text("i18n_cli_core.reward_gold_name", amount=it.get('amount')))
                            elif itype in ("relic", "quest_relic", "boss_relic"):
                                from ....entities import get_relic_name
                                rid = it.get("relic_id") or it.get("id")
                                forced_names.append(get_locale_text("i18n_cli_core.reward_relic_name", name=get_relic_name(rid)))
                            elif itype == "gem":
                                from ....entities import get_gem_name
                                gid = it.get("gem_id")
                                forced_names.append(get_locale_text("i18n_cli_core.reward_gem_name", name=get_gem_name(gid)))
                        names_str = get_locale_text("i18n_cli_core.list_separator").join(forced_names)
                        return get_locale_text("i18n_cli_core.err_must_claim_forced", names_str=names_str), False, False
                    from ..party.coordinator import finish_player_node
                    msg = finish_player_node(router.save_manager, router.engine.map_engine, run, user_id, get_locale_text("i18n_cli_core.msg_leave_node"))
                    return msg, False, True
                if run.node_type == "room_dialog":
                    from ..world.rooms.npc_dialog import close_room_dialog
                    return close_room_dialog(router.save_manager, run), False, True
                if run.node_type in ("landmark", "downstairs", "battle_prompt"):
                    fm = getattr(run, "floor_map", None)
                    if fm is not None:
                        sid = fm.player_session_map.get(user_id)
                        if sid:
                            from ..party.session import SessionContextScoper
                            SessionContextScoper.close_session(run, sid, mark_cleared=False)
                    run.node_type = "grid_map"
                    router.save_manager.save_save(user_id, run)
                    return get_locale_text("i18n_cli_core.msg_leave_node"), False, True
            if arg in ("wizard", "warrior", "wiz", "war", "法师", "战士", "选择", "时序法师", "塑能法师", "秘钥学者"):
                return get_locale_text("i18n_cli_core.err_class_switch"), False, False
            return get_locale_text("i18n_cli_core.err_index_numeric"), False, False
        if run.node_type == "gem_insert":
            res = router.engine.gem_insert_choose(run, idx)
            return res, False, "❌" not in res
        if run.node_data.get("pending_upgrade"):
            res = router.engine.upgrade_card_in_deck(run, idx)
            success = "❌" not in res
            if run.player.hp <= 0:
                settle_msg = router.save_manager.settle_game_and_delete(user_id, run, is_victory=False)
                if len(run.human_uids()) > 1:
                    return get_locale_text("i18n_cli_core.battle_downed_coop", res=res, settle_msg=settle_msg), True, success
                return get_locale_text("i18n_cli_core.death_wilderness", res=res, settle_msg=settle_msg), True, success
            router.save_manager.save_save(user_id, run)
            return res, False, success
        elif run.node_data.get("pending_remove"):
            res = router.engine.remove_card_from_deck(run, idx)
            router.save_manager.save_save(user_id, run)
            return res, False, "❌" not in res
        else:
            target = parts[2] if len(parts) > 2 else None
            res = router.engine.choose_option(run, idx, target)
            success = "❌" not in res
            if run.player.hp <= 0:
                settle_msg = router.save_manager.settle_game_and_delete(user_id, run, is_victory=False)
                return get_locale_text("i18n_cli_core.death_down", res=res, settle_msg=settle_msg), True, success
            if res == "REMOVE_FLOW":
                run.node_data["pending_remove"] = True
                router.save_manager.save_save(user_id, run)
                return get_locale_text("i18n_cli_core.msg_remove_flow_started"), False, True
            elif res == "UPGRADE_FLOW":
                run.node_data["pending_upgrade"] = True
                router.save_manager.save_save(user_id, run)
                return get_locale_text("i18n_cli_core.msg_upgrade_flow_started"), False, True
            else:
                router.save_manager.save_save(user_id, run)
                return res, False, success

class SpecialAction(ActionHandler, actions=["特殊", "sa"]):
    def execute(self, router, user_id: str, run, parts: list[str]) -> Tuple[str, bool, bool]:
        if len(parts) < 2:
            return get_locale_text("i18n_cli_core.err_special_usage"), False, False
        try:
            idx = int(parts[1])
        except ValueError:
            return get_locale_text("i18n_cli_core.err_index_numeric"), False, False
        target = parts[2] if len(parts) > 2 else None
        res = router.engine.play_special_action(run, idx, target)
        success = "❌" not in res
        return check_battle_outcome(router, user_id, run, res, success)

class EndTurnAction(ActionHandler, actions=["结束", "e"]):
    def execute(self, router, user_id: str, run, parts: list[str]) -> Tuple[str, bool, bool]:
        res = router.engine.end_turn(run)
        success = "❌" not in res
        if run.node_type == "victory":
            settle_msg = router.save_manager.settle_game_and_delete(user_id, run, is_victory=True)
            boss_name = run.node_data.get("boss_name") or get_locale_text("i18n_cli_core.final_boss_default")
            return get_locale_text("i18n_cli_core.battle_victory_full", res=res, boss_name=boss_name, settle_msg=settle_msg), True, success
        if get_locale_text("i18n_cli_core.marker_adventure_over") in res or get_locale_text("i18n_cli_core.marker_party_wiped") in res or router.engine.is_battle_won(run):
            return res, True, success
        return res, False, success

class FoldAction(ActionHandler, actions=["折叠", "f", "fold"]):
    def execute(self, router, user_id: str, run, parts: list[str]) -> Tuple[str, bool, bool]:
        run.player.fold_guide = not run.player.fold_guide
        router.save_manager.save_save(user_id, run)
        state_str = get_locale_text("i18n_cli_core.fold_collapsed") if run.player.fold_guide else get_locale_text("i18n_cli_core.fold_expanded")
        return get_locale_text("i18n_cli_core.fold_status", state_str=state_str), False, True
