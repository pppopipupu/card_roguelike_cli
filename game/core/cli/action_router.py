from typing import Tuple
from ...models.state import set_user_id
from ...entities import ALL_CARDS
from ..cli.base import ActionHandler
from .base.aliases import normalize_node_alias
from ...data.locale_data import get_locale_text

class ActionRouter:
    def __init__(self, save_manager, engine):
        self.save_manager = save_manager
        self.engine = engine
        self._action_handlers = ActionHandler.registry

    def execute_action(self, router, user_id: str, run, parts: list[str]) -> Tuple[str, bool, bool]:
        set_user_id(user_id)
        if not parts:
            return "", False, False
        state_stack = run.node_data.setdefault("state_stack", [])
        if run.node_type == "battle" and run.node_data.get("pending_discard"):
            run.node_data.pop("pending_discard", None)
            run.node_data.pop("pending_discard_source", None)
            state_stack.append({"type": "force_discard", "required_count": 1})
        if state_stack:
            top_state = state_stack[-1]
            stype = top_state.get("type")
            if stype == "cthulhu_puzzle_choice":
                head = parts[0].lower()
                if head in ("取消", "cancel"):
                    state_stack.pop()
                    self.engine.battle_engine.rollback_suspended_card(run)
                    self.save_manager.save_save(user_id, run)
                    return get_locale_text("i18n_cli_core.cthulhu_puzzle_cancelled"), False, False
                if head == "c":
                    if len(parts) > 1:
                        return get_locale_text("i18n_cli_core.err_cthulhu_puzzle_invalid"), False, False
                    state_stack.pop()
                    self.engine.battle_engine.rollback_suspended_card(run)
                    self.save_manager.save_save(user_id, run)
                    return get_locale_text("i18n_cli_core.cthulhu_puzzle_cancelled"), False, False
                answer = ""
                if len(parts) == 1 and head.isdecimal():
                    answer = head
                elif head == "选择" and len(parts) >= 2:
                    answer = parts[1]
                if answer:
                    if not answer.isdecimal():
                        return get_locale_text("i18n_cli_core.err_cthulhu_puzzle_invalid"), False, False
                    idx = int(answer)
                    if idx < 1 or idx > 3:
                        return get_locale_text("i18n_cli_core.err_cthulhu_puzzle_invalid"), False, False
                    from ...entities.enemies.boss.cthulhu_boss import resolve_cthulhu_puzzle
                    res = resolve_cthulhu_puzzle(run, self.engine, idx, run.player)
                    state_stack.pop()
                    self.engine.battle_engine.resolve_suspended_card(run)
                    self.save_manager.save_save(user_id, run)
                    if run.player.hp <= 0:
                        settle_msg = self.save_manager.settle_game_and_delete(user_id, run, is_victory=False)
                        if getattr(run, "coop_id", ""):
                            return get_locale_text("i18n_cli_core.battle_downed_coop", res=res, settle_msg=settle_msg), True, True
                        return get_locale_text("i18n_cli_core.battle_defeated", res=res, settle_msg=settle_msg), True, True
                    if self.engine.is_battle_won(run):
                        self.engine._handle_battle_win(run)
                        if run.node_type == "victory":
                            settle_msg = self.save_manager.settle_game_and_delete(user_id, run, is_victory=True)
                            boss_name = run.node_data.get("boss_name")
                            if not boss_name and run.enemies:
                                boss_name = run.enemies[0].name
                            if not boss_name:
                                boss_name = get_locale_text("i18n_cli_core.final_boss_default")
                            return self.engine.battle_engine._append_logs_to_res(run, get_locale_text("i18n_cli_core.battle_victory_full", res=res, boss_name=boss_name, settle_msg=settle_msg)), True, True
                        return self.engine.battle_engine._append_logs_to_res(run, get_locale_text("i18n_cli_core.battle_won", res=res)), True, True
                    return self.engine.battle_engine._append_logs_to_res(run, res), False, True
                if head == "选择":
                    return get_locale_text("i18n_cli_core.err_cthulhu_puzzle_invalid"), False, False
                if head not in self._action_handlers:
                    return get_locale_text("i18n_cli_core.err_cthulhu_puzzle_invalid"), False, False
            elif stype == "force_discard":
                sub = parts[0]
                if sub.isdigit():
                    parts = ["选择"] + parts
                    sub = "选择"
                if sub not in ("选择", "c"):
                    return get_locale_text("i18n_cli_core.err_force_discard_required"), False, False
                if len(parts) < 2:
                    return get_locale_text("i18n_cli_core.err_need_hand_index"), False, False
                try:
                    idx = int(parts[1])
                except ValueError:
                    return get_locale_text("i18n_cli_core.err_index_numeric"), False, False
                p = run.player
                if idx < 1 or idx > len(p.hand):
                    return get_locale_text("i18n_cli_core.err_invalid_hand_index", count=len(p.hand)), False, False
                cid = p.hand.pop(idx - 1)
                card_name = ALL_CARDS[cid].name if cid in ALL_CARDS else get_locale_text("i18n_cli_core.unknown_card")
                req_count = top_state.get("required_count", 1)
                discarded = top_state.setdefault("discarded", [])
                discarded.append(cid)
                agile_msg = self.engine._discard_card(run, cid)
                if len(discarded) >= req_count:
                    state_stack.pop()
                    self.engine.battle_engine.resolve_suspended_card(run)
                else:
                    top_state["required_count"] = req_count - len(discarded)
                    top_state["discarded"] = []
                self.save_manager.save_save(user_id, run)
                res = get_locale_text("i18n_cli_core.discard_result", card_name=card_name)
                if agile_msg:
                    res += f"\n{agile_msg}"
                if self.engine.is_battle_won(run):
                    self.engine._handle_battle_win(run)
                    if run.node_type == "victory":
                        settle_msg = self.save_manager.settle_game_and_delete(user_id, run, is_victory=True)
                        boss_name = run.node_data.get("boss_name")
                        if not boss_name and run.enemies:
                            boss_name = run.enemies[0].name
                        if not boss_name:
                            boss_name = get_locale_text("i18n_cli_core.final_boss_default")
                        return self.engine.battle_engine._append_logs_to_res(run, get_locale_text("i18n_cli_core.battle_victory_full", res=res, boss_name=boss_name, settle_msg=settle_msg)), True, True
                    else:
                        return self.engine.battle_engine._append_logs_to_res(run, get_locale_text("i18n_cli_core.battle_won", res=res)), True, True
                return self.engine.battle_engine._append_logs_to_res(run, res), False, True
            elif stype == "awaiting_target":
                if parts and parts[0] in self._action_handlers:
                    state_stack.pop()
                    self.save_manager.save_save(user_id, run)
                else:
                    input_str = " ".join(parts).strip()
                    if input_str in ("取消", "cancel", "abandon", "放弃", "exit", "quit"):
                        state_stack.pop()
                        self.save_manager.save_save(user_id, run)
                        return get_locale_text("i18n_cli_core.err_cancel_use"), False, False
                    def is_valid_target_format(text: str) -> bool:
                        text = text.strip().lower()
                        if not text:
                            return False
                        if text.isdigit():
                            return True
                        if text.startswith("p") and text[1:].isdigit():
                            return True
                        if text.startswith("e") and text[1:].isdigit():
                            return True
                        return False
                    if is_valid_target_format(input_str):
                        target = input_str
                        action_info = top_state.get("action")
                        if action_info == "play_card":
                            hand_idx = top_state.get("hand_idx")
                            state_stack.pop()
                            res = self.engine.play_card(run, hand_idx, target)
                            success = "❌" not in res
                            if run.player.hp <= 0:
                                settle_msg = self.save_manager.settle_game_and_delete(user_id, run, is_victory=False)
                                if getattr(run, "coop_id", ""):
                                    return get_locale_text("i18n_cli_core.battle_downed_coop", res=res, settle_msg=settle_msg), True, success
                                return get_locale_text("i18n_cli_core.battle_defeated", res=res, settle_msg=settle_msg), True, success
                            if self.engine.is_battle_won(run):
                                self.engine._handle_battle_win(run)
                                if run.node_type == "victory":
                                    settle_msg = self.save_manager.settle_game_and_delete(user_id, run, is_victory=True)
                                    boss_name = run.node_data.get("boss_name")
                                    if not boss_name and run.enemies:
                                        boss_name = run.enemies[0].name
                                    if not boss_name:
                                        boss_name = get_locale_text("i18n_cli_core.final_boss_default")
                                    return get_locale_text("i18n_cli_core.battle_victory_full", res=res, boss_name=boss_name, settle_msg=settle_msg), True, success
                                else:
                                    return get_locale_text("i18n_cli_core.battle_won", res=res), True, success
                            return res, False, success
                        elif action_info == "minion_skill":
                            my_grid = top_state.get("my_grid")
                            skill_idx = top_state.get("skill_idx")
                            state_stack.pop()
                            res = self.engine.minion_skill(run, my_grid, skill_idx, target)
                            success = "❌" not in res
                            if run.player.hp <= 0:
                                settle_msg = self.save_manager.settle_game_and_delete(user_id, run, is_victory=False)
                                if getattr(run, "coop_id", ""):
                                    return get_locale_text("i18n_cli_core.battle_downed_coop", res=res, settle_msg=settle_msg), True, success
                                return get_locale_text("i18n_cli_core.battle_defeated", res=res, settle_msg=settle_msg), True, success
                            if self.engine.is_battle_won(run):
                                self.engine._handle_battle_win(run)
                                if run.node_type == "victory":
                                    settle_msg = self.save_manager.settle_game_and_delete(user_id, run, is_victory=True)
                                    boss_name = run.node_data.get("boss_name")
                                    if not boss_name and run.enemies:
                                        boss_name = run.enemies[0].name
                                    if not boss_name:
                                        boss_name = get_locale_text("i18n_cli_core.final_boss_default")
                                    return get_locale_text("i18n_cli_core.battle_victory_full", res=res, boss_name=boss_name, settle_msg=settle_msg), True, success
                                else:
                                    return get_locale_text("i18n_cli_core.battle_won", res=res), True, success
                            return res, False, success
                    else:
                        state_stack.pop()
                        self.save_manager.save_save(user_id, run)
                        return get_locale_text("i18n_cli_core.err_cancel_use"), False, False
            elif stype == "discover_selection":
                input_str = " ".join(parts).strip()
                if input_str in ("取消", "cancel", "abandon", "放弃", "exit", "quit"):
                    state_stack.pop()
                    self.engine.battle_engine.rollback_suspended_card(run)
                    self.save_manager.save_save(user_id, run)
                    return self.engine.battle_engine._append_logs_to_res(run, get_locale_text("i18n_cli_core.err_cancel_discover")), False, False
                sub = parts[0]
                if sub.isdigit():
                    parts = ["选择"] + parts
                    sub = "选择"
                if sub not in ("选择", "c"):
                    return get_locale_text("i18n_cli_core.err_force_discover_required"), False, False
                if len(parts) < 2:
                    return get_locale_text("i18n_cli_core.err_need_card_index"), False, False
                try:
                    idx = int(parts[1])
                except ValueError:
                    return get_locale_text("i18n_cli_core.err_index_numeric"), False, False
                p = run.player
                valid_exhaust = [c for c in p.exhaust_pile if c.id != "discover"]
                if idx < 1 or idx > len(valid_exhaust):
                    return get_locale_text("i18n_cli_core.err_invalid_exhaust_index", count=len(valid_exhaust)), False, False
                target_card = valid_exhaust[idx - 1]
                real_idx = p.exhaust_pile.index(target_card)
                cid = p.exhaust_pile.pop(real_idx)
                p.hand.append(cid)
                card_name = ALL_CARDS[cid].name if cid in ALL_CARDS else get_locale_text("i18n_cli_core.unknown_card")
                top_state.setdefault("selected", []).append(cid)
                req_count = top_state.get("count", 1)
                valid_exhaust_after = [c for c in p.exhaust_pile if c.id != "discover"]
                if len(top_state["selected"]) < req_count and valid_exhaust_after:
                    self.save_manager.save_save(user_id, run)
                    exhaust_list = "\n".join(f"{i+1}. {ALL_CARDS[c].name}" for i, c in enumerate(valid_exhaust_after))
                    return get_locale_text("i18n_cli_core.discover_continue", card_name=card_name, next_index=len(top_state['selected']) + 1, exhaust_list=exhaust_list), False, True
                else:
                    state_stack.pop()
                    self.engine.battle_engine.resolve_suspended_card(run)
                    self.save_manager.save_save(user_id, run)
                    selected_cards_str = "，".join(ALL_CARDS[c].name for c in top_state["selected"])
                    res = get_locale_text("i18n_cli_core.discover_complete", selected_cards_str=selected_cards_str)
                    return self.engine.battle_engine._append_logs_to_res(run, res), False, True
            elif stype == "overload_star_select":
                input_str = " ".join(parts).strip()
                if input_str in ("取消", "cancel", "abandon", "放弃", "exit", "quit"):
                    state_stack.pop()
                    self.engine.battle_engine.rollback_suspended_card(run)
                    self.save_manager.save_save(user_id, run)
                    return self.engine.battle_engine._append_logs_to_res(run, get_locale_text("i18n_cli_core.err_cancel_overload")), False, False
                sub = parts[0]
                if sub.isdigit():
                    parts = ["选择"] + parts
                    sub = "选择"
                if sub not in ("选择", "c"):
                    return get_locale_text("i18n_cli_core.err_overload_required"), False, False
                if len(parts) < 2:
                    return get_locale_text("i18n_cli_core.err_need_hand_index"), False, False
                try:
                    idx = int(parts[1])
                except ValueError:
                    return get_locale_text("i18n_cli_core.err_index_numeric"), False, False
                p = run.player
                if idx < 1 or idx > len(p.hand):
                    return get_locale_text("i18n_cli_core.err_invalid_hand_index", count=len(p.hand)), False, False
                state_stack.pop()
                upgraded = top_state.get("upgraded", False)
                res = self.engine.execute_emperor_eye_resolve(run, idx - 1, upgraded)
                success = "❌" not in res
                if run.player.hp <= 0:
                    settle_msg = self.save_manager.settle_game_and_delete(user_id, run, is_victory=False)
                    if getattr(run, "coop_id", ""):
                        return get_locale_text("i18n_cli_core.battle_downed_coop", res=res, settle_msg=settle_msg), True, success
                    return get_locale_text("i18n_cli_core.battle_defeated", res=res, settle_msg=settle_msg), True, success
                if self.engine.is_battle_won(run):
                    self.engine._handle_battle_win(run)
                    if run.node_type == "victory":
                        settle_msg = self.save_manager.settle_game_and_delete(user_id, run, is_victory=True)
                        boss_name = run.node_data.get("boss_name")
                        if not boss_name and run.enemies:
                            boss_name = run.enemies[0].name
                        if not boss_name:
                            boss_name = get_locale_text("i18n_cli_core.final_boss_default")
                        return get_locale_text("i18n_cli_core.battle_victory_full", res=res, boss_name=boss_name, settle_msg=settle_msg), True, success
                    else:
                        return get_locale_text("i18n_cli_core.battle_won", res=res), True, success
                return res, False, success
        parts = normalize_node_alias(run, parts)
        sub = parts[0]
        handler = self._action_handlers.get(sub)
        if handler:
            return handler.execute(router, user_id, run, parts)
        return get_locale_text("i18n_cli_core.unknown_action", parts=parts), False, False
