from typing import Tuple
from .base import ActionHandler, find_hand_index_by_initials, normalize_initial_query
from ...entities import ALL_CARDS
from ...data.text.locale_data import get_locale_text
from ...data.world.open_world_config import OPEN_WORLD_SETTLED_MSG_KEY
from ...data.world.pvp_config import PVP_MATCH_KEY
from ..battle.pvp_service import PvpService, is_pvp_run
from ..world.open_world.loadout_service import is_open_world_run


def finalize_defeat(
    save_manager,
    user_id: str,
    run,
    res: str,
    success: bool,
    *,
    solo_key: str = "i18n_cli_core.battle_defeated",
    coop_key: str = "i18n_cli_core.battle_downed_coop",
    allow_coop_msg: bool = True,
) -> Tuple[str, bool, bool]:
    settle_msg = save_manager.settle_game_and_delete(user_id, run, is_victory=False)
    if is_open_world_run(run) and save_manager.load_save(user_id) is None:
        merged = (res.rstrip() + "\n\n" + settle_msg).strip() if res and res.strip() else settle_msg
        return merged, True, success
    from ..world.tutorial import is_tutorial_run
    if is_tutorial_run(run):
        merged = (res.rstrip() + "\n\n" + settle_msg).strip() if res and res.strip() else settle_msg
        return merged, True, True
    if allow_coop_msg and len(run.all_human_uids()) > 1:
        return get_locale_text(coop_key, res=res, settle_msg=settle_msg), True, success
    return get_locale_text(solo_key, res=res, settle_msg=settle_msg), True, success


def finalize_victory(
    save_manager,
    engine,
    user_id: str,
    run,
    res: str,
    success: bool,
    *,
    append_logs: bool = False,
) -> Tuple[str, bool, bool]:
    engine._handle_battle_win(run)
    settled_msg = run.node_data.get(OPEN_WORLD_SETTLED_MSG_KEY)
    if settled_msg:
        msg = (res.rstrip() + "\n\n" + settled_msg).strip() if res and res.strip() else settled_msg
        return msg, True, success
    if run.node_type == "room_dialog":
        from ..world.rooms.npc_dialog import render_room_dialog
        rendered = render_room_dialog(run, save_manager=save_manager)
        out = (res.rstrip() + "\n\n" + rendered).strip() if res and res.strip() else rendered
        return out, True, success
    if run.node_type == "victory":
        settle_msg = save_manager.settle_game_and_delete(user_id, run, is_victory=True)
        boss_name = run.node_data.get("boss_name")
        if not boss_name and run.enemies:
            boss_name = run.enemies[0].name
        if not boss_name:
            boss_name = get_locale_text("i18n_cli_core.final_boss_default")
        out = get_locale_text("i18n_cli_core.battle_victory_full", res=res, boss_name=boss_name, settle_msg=settle_msg)
    else:
        out = get_locale_text("i18n_cli_core.battle_won", res=res)
    if append_logs:
        out = engine.battle_engine._append_logs_to_res(run, out)
    return out, True, success


def check_battle_outcome(router, user_id, run, res, success):
    if is_pvp_run(run):
        from ...data.world.pvp_config import PVP_ESCAPE_KEY
        if run.node_data.pop(PVP_ESCAPE_KEY, False):
            match = router.save_manager.pvp.get_match(run.node_data.get(PVP_MATCH_KEY))
            parts = [res.strip()] if res and res.strip() else []
            if match is not None:
                p1_uid = str(match.get("p1_uid", ""))
                p2_uid = str(match.get("p2_uid", ""))
                opp_uid = p2_uid if str(user_id) == p1_uid else p1_uid
                _, lose_msg = PvpService.settle_pvp_match(
                    router.save_manager,
                    router.town_engine,
                    router.world_social,
                    match["id"],
                    opp_uid,
                    user_id,
                    reason="escape",
                    actor_uid=user_id,
                )
                parts.append(lose_msg)
            else:
                router.save_manager.delete_save(user_id)
            stats = router.save_manager.load_stats(user_id)
            parts.append(router.town_engine.render_current_room(user_id, stats))
            return "\n\n".join(part for part in parts if part), True, success
        match = router.save_manager.pvp.get_match(run.node_data.get(PVP_MATCH_KEY))
        if match is None:
            if router.save_manager.load_save(user_id) is None:
                return res, True, success
            router.save_manager.delete_save(user_id)
            stats = router.save_manager.load_stats(user_id)
            stats.in_town = True
            stats.town_pos = "square"
            router.save_manager.save_stats(user_id, stats)
            parts = [res.strip()] if res and res.strip() else []
            parts.append(router.town_engine.render_current_room(user_id, stats))
            return "\n\n".join(part for part in parts if part), True, success
        PvpService.sync_opponent_from_enemies(run)
        router.save_manager.save_save(user_id, run)
        p1_uid = str(match.get("p1_uid", ""))
        p2_uid = str(match.get("p2_uid", ""))
        opp_uid = p2_uid if str(user_id) == p1_uid else p1_uid
        if run.player.hp <= 0:
            _, lose_msg = PvpService.settle_pvp_match(
                router.save_manager,
                router.town_engine,
                router.world_social,
                match["id"],
                opp_uid,
                user_id,
                actor_uid=user_id,
            )
            merged = (res.rstrip() + "\n\n" + lose_msg).strip() if res and res.strip() else lose_msg
            return merged, True, success
        if (
            not run.enemies
            or (run.player2 is not None and run.player2.hp <= 0)
            or (run.enemies and run.enemies[0].hp <= 0)
        ):
            win_msg, _ = PvpService.settle_pvp_match(
                router.save_manager,
                router.town_engine,
                router.world_social,
                match["id"],
                user_id,
                opp_uid,
                actor_uid=user_id,
            )
            merged = (res.rstrip() + "\n\n" + win_msg).strip() if res and res.strip() else win_msg
            return merged, True, success
        return res, False, success
    if run.player.hp <= 0:
        return finalize_defeat(router.save_manager, user_id, run, res, success)
    if router.engine.is_battle_won(run):
        return finalize_victory(router.save_manager, router.engine, user_id, run, res, success)
    return res, False, success

class UseAction(ActionHandler, actions=["使用", "p"]):
    def execute(self, router, user_id: str, run, parts: list[str]) -> Tuple[str, bool, bool]:
        if is_pvp_run(run):
            ok, wait_msg = PvpService.check_turn_owner(router.save_manager, user_id, run)
            if not ok:
                return wait_msg, False, False
            PvpService.sync_enemies_from_opponent(run)
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
        if is_pvp_run(run):
            ok, wait_msg = PvpService.check_turn_owner(router.save_manager, user_id, run)
            if not ok:
                return wait_msg, False, False
            PvpService.sync_enemies_from_opponent(run)
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
                    if run.node_data.get("upgrade_source") == "room_dialog":
                        from ..world.rooms.npc_dialog import resume_room_dialog_after_flow
                        res = resume_room_dialog_after_flow(router.save_manager, run, get_locale_text("i18n_cli_core.msg_cancel_upgrade"), committed=False)
                        return res, True, True
                    router.save_manager.save_save(user_id, run)
                    return get_locale_text("i18n_cli_core.msg_cancel_upgrade"), False, True
                if run.node_type == "gem_insert":
                    res = router.engine.gem_insert_cancel(run)
                    return res, run.node_type == "room_dialog", "❌" not in res
                if run.node_type == "enchant_card":
                    res = router.engine.enchant_cancel(run)
                    return res, False, "❌" not in res
                if run.node_type == "ally_summon_select":
                    from ..world.ally_summon import handle_summon_select_choose
                    res = handle_summon_select_choose(router.engine.map_engine.grid_map_service, run, 0)
                    return res, False, "❌" not in res
                if run.node_type == "ally_summon_confirm":
                    from ..world.ally_summon import handle_summon_confirm_choose
                    res = handle_summon_confirm_choose(router.engine.map_engine.grid_map_service, run, 0)
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
                                from ...entities import get_relic_name
                                rid = it.get("relic_id") or it.get("id")
                                forced_names.append(get_locale_text("i18n_cli_core.reward_relic_name", name=get_relic_name(rid)))
                            elif itype == "gem":
                                from ...entities import get_gem_name
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
                if run.node_type in ("landmark", "downstairs"):
                    fm = getattr(run, "floor_map", None)
                    if fm is not None:
                        if run.node_type == "downstairs" and isinstance(fm.floor_flags.get("downstairs_ready"), dict):
                            fm.floor_flags["downstairs_ready"].pop(user_id, None)
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
            return res, run.node_type == "room_dialog", "❌" not in res
        if run.node_type == "enchant_card":
            res = router.engine.enchant_choose(run, idx)
            return res, False, "❌" not in res
        if run.node_type == "ally_summon_select":
            from ..world.ally_summon import handle_summon_select_choose
            res = handle_summon_select_choose(router.engine.map_engine.grid_map_service, run, idx)
            return res, False, "❌" not in res
        if run.node_type == "ally_summon_confirm":
            from ..world.ally_summon import handle_summon_confirm_choose
            res = handle_summon_confirm_choose(router.engine.map_engine.grid_map_service, run, idx)
            return res, False, "❌" not in res
        if run.node_data.get("pending_upgrade"):
            res = router.engine.upgrade_card_in_deck(run, idx)
            success = "❌" not in res
            if run.player.hp <= 0 and not run.player.downed:
                return finalize_defeat(
                    router.save_manager,
                    user_id,
                    run,
                    res,
                    success,
                    solo_key="i18n_cli_core.death_wilderness",
                )
            router.save_manager.save_save(user_id, run)
            return res, run.node_type == "room_dialog", success
        elif run.node_data.get("pending_remove"):
            res = router.engine.remove_card_from_deck(run, idx)
            router.save_manager.save_save(user_id, run)
            return res, False, "❌" not in res
        else:
            target = parts[2] if len(parts) > 2 else None
            res = router.engine.choose_option(run, idx, target)
            success = "❌" not in res
            if run.node_data.get("yog_finished") or run.node_data.get("tutorial_finished"):
                return res, True, success
            if run.player.hp <= 0 and not run.player.downed:
                return finalize_defeat(
                    router.save_manager,
                    user_id,
                    run,
                    res,
                    success,
                    solo_key="i18n_cli_core.death_down",
                    allow_coop_msg=False,
                )
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
        if is_pvp_run(run):
            ok, wait_msg = PvpService.check_turn_owner(router.save_manager, user_id, run)
            if not ok:
                return wait_msg, False, False
            PvpService.sync_enemies_from_opponent(run)
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
        if is_pvp_run(run):
            ok, wait_msg = PvpService.check_turn_owner(router.save_manager, user_id, run)
            if not ok:
                return wait_msg, False, False
            msg = PvpService.advance_pvp_turn(
                router.save_manager,
                getattr(router.engine, "battle_engine", router.engine),
                router.town_engine,
                router.world_social,
                run,
                user_id,
            )
            return msg, True, True
        res = router.engine.end_turn(run)
        success = "❌" not in res
        if run.node_type == "room_dialog":
            from ..world.rooms.npc_dialog import render_room_dialog
            rendered = render_room_dialog(run, save_manager=router.save_manager)
            out = (res.rstrip() + "\n\n" + rendered).strip() if res and res.strip() else rendered
            return out, True, success
        if run.node_type == "victory":
            settle_msg = router.save_manager.settle_game_and_delete(user_id, run, is_victory=True)
            boss_name = run.node_data.get("boss_name") or get_locale_text("i18n_cli_core.final_boss_default")
            return get_locale_text("i18n_cli_core.battle_victory_full", res=res, boss_name=boss_name, settle_msg=settle_msg), True, success
        if (
            get_locale_text("i18n_cli_core.marker_adventure_over") in res
            or get_locale_text("i18n_cli_core.marker_party_wiped") in res
            or router.engine.is_battle_won(run)
            or (is_open_world_run(run) and run.node_type == "grid_map")
            or (run.node_type == "grid_map" and bool(run.floor_map and run.floor_map.floor_flags.get("tutorial_zone")))
            or router.save_manager.load_save(user_id) is None
        ):
            settled_msg = run.node_data.get(OPEN_WORLD_SETTLED_MSG_KEY)
            if settled_msg and settled_msg not in res:
                res = (res.rstrip() + "\n\n" + settled_msg).strip() if res and res.strip() else settled_msg
            return res, True, success
        return res, False, success

class FoldAction(ActionHandler, actions=["折叠", "f", "fold"]):
    def execute(self, router, user_id: str, run, parts: list[str]) -> Tuple[str, bool, bool]:
        run.player.fold_guide = not run.player.fold_guide
        router.save_manager.save_save(user_id, run)
        state_str = get_locale_text("i18n_cli_core.fold_collapsed") if run.player.fold_guide else get_locale_text("i18n_cli_core.fold_expanded")
        return get_locale_text("i18n_cli_core.fold_status", state_str=state_str), False, True
