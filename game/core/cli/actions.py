from typing import Tuple
from .base import ActionHandler, find_hand_index_by_initials, normalize_initial_query
from ...entities import ALL_CARDS
from ...data.locale_data import get_locale_text

class UseAction(ActionHandler, actions=["使用", "p"]):
    def execute(self, router, user_id: str, run, parts: list[str]) -> Tuple[str, bool, bool]:
        if len(parts) < 2:
            return "❌ 请提供手牌序号或卡牌名称拼音首字母，例如：使用 1 或 使用 ssxs", False, False
        arg = parts[1]
        try:
            idx = int(arg)
        except ValueError:
            query = normalize_initial_query(arg)
            if not query:
                return "❌ 参数必须是手牌序号或卡牌名称的拼音首字母。", False, False
            idx = find_hand_index_by_initials(run.player.hand, query)
            if idx is None:
                return f"❌ 手牌中没有拼音首字母为【{query}】的卡牌。", False, False
        target = " ".join(parts[2:]) if len(parts) > 2 else None
        res = router.engine.play_card(run, idx, target)
        success = "❌" not in res
        if run.player.hp <= 0:
            settle_msg = router.save_manager.settle_game_and_delete(user_id, run, is_victory=False)
            if getattr(run, "coop_id", ""):
                return f"{res}\n💀 你已倒地。\n{settle_msg}", True, success
            return f"{res}\n💀 你被击败了！当前进度已清空。\n{settle_msg}", True, success
        if router.engine.is_battle_won(run):
            router.engine._handle_battle_win(run)
            if run.node_type == "victory":
                settle_msg = router.save_manager.settle_game_and_delete(user_id, run, is_victory=True)
                boss_name = run.node_data.get("boss_name")
                if not boss_name and run.enemies:
                    boss_name = run.enemies[0].name
                if not boss_name:
                    boss_name = "最终BOSS"
                return f"{res}\n🎉 恭喜你击败了{boss_name}，通关成功！\n{settle_msg}", True, success
            else:
                return f"{res}\n🎉 战斗胜利！你击败了敌方所有单位。", True, success
        return res, False, success

class MinionAction(ActionHandler, actions=["随从", "m"]):
    def execute(self, router, user_id: str, run, parts: list[str]) -> Tuple[str, bool, bool]:
        if len(parts) < 3:
            return "❌ 参数不足。用法：随从 <我方格子> 攻击/技能 <目标/序号>", False, False
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
            return f"❌ 找不到我方随从格子 [{my_grid_raw}]。", False, False
        results = []
        for g in grids:
            if run.player.hp <= 0:
                success = not any("❌" in r for r in results) if results else False
                return "\n".join(results) + "\n💀 你被击败了！当前进度已清空。", True, success
            if router.engine.is_battle_won(run):
                router.engine._handle_battle_win(run)
                success = not any("❌" in r for r in results) if results else False
                if run.node_type == "victory":
                    settle_msg = router.save_manager.settle_game_and_delete(user_id, run, is_victory=True)
                    boss_name = run.node_data.get("boss_name")
                    if not boss_name and run.enemies:
                        boss_name = run.enemies[0].name
                    if not boss_name:
                        boss_name = "最终BOSS"
                    return "\n".join(results) + f"\n🎉 恭喜你击败了{boss_name}，通关成功！\n{settle_msg}", True, success
                else:
                    return "\n".join(results) + "\n🎉 战斗胜利！你击败了敌方所有单位。", True, success
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
                return "❌ 未知的随从指令。", False, False
        res_combined = "\n".join(results)
        success = not any("❌" in r for r in results) if results else False
        if run.player.hp <= 0:
            settle_msg = router.save_manager.settle_game_and_delete(user_id, run, is_victory=False)
            if getattr(run, "coop_id", ""):
                return f"{res_combined}\n💀 你已倒地。\n{settle_msg}", True, success
            return f"{res_combined}\n💀 你被击败了！当前进度已清空。\n{settle_msg}", True, success
        if router.engine.is_battle_won(run):
            router.engine._handle_battle_win(run)
            if run.node_type == "victory":
                settle_msg = router.save_manager.settle_game_and_delete(user_id, run, is_victory=True)
                boss_name = run.node_data.get("boss_name")
                if not boss_name and run.enemies:
                    boss_name = run.enemies[0].name
                if not boss_name:
                    boss_name = "最终BOSS"
                return f"{res_combined}\n🎉 恭喜你击败了{boss_name}，通关成功！\n{settle_msg}", True, success
            else:
                return f"{res_combined}\n🎉 战斗胜利！你击败了敌方所有单位。", True, success
        return res_combined, False, success

class ChooseAction(ActionHandler, actions=["选择", "c"]):
    def execute(self, router, user_id: str, run, parts: list[str]) -> Tuple[str, bool, bool]:
        if len(parts) < 2:
            return "❌ 请提供选项序号，例如：选择 1", False, False
        try:
            idx = int(parts[1])
        except ValueError:
            arg = parts[1].lower()
            if arg in ("取消", "cancel", "返回", "quit", "exit", "0", "离开", "退出"):
                if run.node_data.get("pending_remove"):
                    run.node_data["pending_remove"] = False
                    router.save_manager.save_save(user_id, run)
                    return get_locale_text("msg_cancel_remove"), False, True
                if run.node_data.get("pending_upgrade"):
                    run.node_data["pending_upgrade"] = False
                    router.save_manager.save_save(user_id, run)
                    return get_locale_text("msg_cancel_upgrade"), False, True
                if run.node_type == "gem_insert":
                    res = router.engine.gem_insert_cancel(run)
                    return res, False, "❌" not in res
                if run.node_type in ("reward", "treasure", "boss_chest", "rest", "shop"):
                    items = run.node_data.get("items", [])
                    forced_items = [it for it in items if it.get("force") and not it.get("taken")]
                    if forced_items:
                        forced_names = []
                        for it in forced_items:
                            itype = it.get("type")
                            if itype == "card_reward":
                                forced_names.append("卡牌奖励")
                            elif itype == "gold":
                                forced_names.append(f"{it.get('amount')} 金币")
                            elif itype in ("relic", "quest_relic", "boss_relic"):
                                from ....entities import get_relic_name
                                rid = it.get("relic_id") or it.get("id")
                                forced_names.append(f"遗物【{get_relic_name(rid)}】")
                            elif itype == "gem":
                                from ....entities import get_gem_name
                                gid = it.get("gem_id")
                                forced_names.append(f"宝石【{get_gem_name(gid)}】")
                        names_str = "、".join(forced_names)
                        return get_locale_text("err_must_claim_forced", names_str=names_str), False, False
                    if getattr(run, "coop_id", ""):
                        from ..coop_engine import CoopEngine
                        msg = CoopEngine(router.save_manager, router.engine.battle_engine).finish_player_node(run, user_id, get_locale_text("msg_leave_node"))
                        return msg, False, True
                    router.engine.map_engine.enter_next_stage(run)
                    router.save_manager.save_save(run.user_id, run)
                    return get_locale_text("msg_leave_node"), False, True
            if arg in ("wizard", "warrior", "wiz", "war", "法师", "战士", "选择", "时序法师", "塑能法师", "秘钥学者"):
                return "❌ 切换职业请在局外使用 /rogue class 命令。\n💡 选择命令 c 仅用于局内选项选择，无法用于选择职业。", False, False
            return "❌ 序号必须是数字。", False, False
        if run.node_type == "gem_insert":
            res = router.engine.gem_insert_choose(run, idx)
            return res, False, "❌" not in res
        if run.node_data.get("pending_upgrade"):
            res = router.engine.upgrade_card_in_deck(run, idx)
            success = "❌" not in res
            if run.player.hp <= 0:
                settle_msg = router.save_manager.settle_game_and_delete(user_id, run, is_victory=False)
                if getattr(run, "coop_id", ""):
                    return f"{res}\n💀 你已倒地。\n{settle_msg}", True, success
                return f"{res}\n💀 你在荒野的意外中丧生了！当前进度已清空。\n{settle_msg}", True, success
            if getattr(run, "coop_id", ""):
                router.save_manager.save_save(user_id, run)
            return res, False, success
        elif run.node_data.get("pending_remove"):
            res = router.engine.remove_card_from_deck(run, idx)
            if getattr(run, "coop_id", ""):
                router.save_manager.save_save(user_id, run)
            return res, False, "❌" not in res
        else:
            target = parts[2] if len(parts) > 2 else None
            res = router.engine.choose_option(run, idx, target)
            success = "❌" not in res
            if run.player.hp <= 0:
                settle_msg = router.save_manager.settle_game_and_delete(user_id, run, is_victory=False)
                return f"{res}\n💀 你倒下了。\n{settle_msg}", True, success
            if res == "REMOVE_FLOW":
                run.node_data["pending_remove"] = True
                router.save_manager.save_save(user_id, run)
                return "🧹 净化服务已启动。请查看你的卡组，并输入 c <卡牌序号> 来从卡组中移除该牌。可以通过 /rogue deck 查看卡牌序号。", False, True
            elif res == "UPGRADE_FLOW":
                run.node_data["pending_upgrade"] = True
                router.save_manager.save_save(user_id, run)
                return "🔨 卡牌升级强化已启动。请查看你的卡组，并输入 c <卡牌序号> 来使你的卡牌永久升级为带【+】的强力变体。可以通过 /rogue deck 查看卡牌序号。", False, True
            else:
                if getattr(run, "coop_id", ""):
                    router.save_manager.save_save(user_id, run)
                return res, False, success

class SpecialAction(ActionHandler, actions=["特殊", "sa"]):
    def execute(self, router, user_id: str, run, parts: list[str]) -> Tuple[str, bool, bool]:
        if len(parts) < 2:
            return "❌ 请提供手牌序号，例如：sa 1", False, False
        try:
            idx = int(parts[1])
        except ValueError:
            return "❌ 序号必须是数字。", False, False
        target = parts[2] if len(parts) > 2 else None
        res = router.engine.play_special_action(run, idx, target)
        success = "❌" not in res
        if run.player.hp <= 0:
            settle_msg = router.save_manager.settle_game_and_delete(user_id, run, is_victory=False)
            if getattr(run, "coop_id", ""):
                return f"{res}\n💀 你已倒地。\n{settle_msg}", True, success
            return f"{res}\n💀 你被击败了！当前进度已清空。\n{settle_msg}", True, success
        if router.engine.is_battle_won(run):
            router.engine._handle_battle_win(run)
            if run.node_type == "victory":
                settle_msg = router.save_manager.settle_game_and_delete(user_id, run, is_victory=True)
                boss_name = run.node_data.get("boss_name")
                if not boss_name and run.enemies:
                    boss_name = run.enemies[0].name
                if not boss_name:
                    boss_name = "最终BOSS"
                return f"{res}\n🎉 恭喜你击败了{boss_name}，通关成功！\n{settle_msg}", True, success
            else:
                return f"{res}\n🎉 战斗胜利！你击败了敌方所有单位。", True, success
        return res, False, success

class EndTurnAction(ActionHandler, actions=["结束", "e"]):
    def execute(self, router, user_id: str, run, parts: list[str]) -> Tuple[str, bool, bool]:
        res = router.engine.end_turn(run)
        success = "❌" not in res
        if run.node_type == "victory":
            settle_msg = router.save_manager.settle_game_and_delete(user_id, run, is_victory=True)
            boss_name = run.node_data.get("boss_name") or "最终BOSS"
            return f"{res}\n🎉 恭喜你击败了{boss_name}，通关成功！\n{settle_msg}", True, success
        if "冒险结束" in res or "全队阵亡" in res or router.engine.is_battle_won(run):
            return res, True, success
        return res, False, success

class FoldAction(ActionHandler, actions=["折叠", "f", "fold"]):
    def execute(self, router, user_id: str, run, parts: list[str]) -> Tuple[str, bool, bool]:
        run.player.fold_guide = not run.player.fold_guide
        router.save_manager.save_save(user_id, run)
        state_str = "已折叠" if run.player.fold_guide else "已展开"
        return f"🔮 操作指南状态：【{state_str}】。", False, True
