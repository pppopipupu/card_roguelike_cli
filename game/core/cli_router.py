from typing import Tuple, Generator
from ..models.state import set_user_id, UserStats, GameRun
from ..renderer import GameRenderer
from .cli.base import ActionHandler, CommandHandler
from .cli.action_router import ActionRouter
from .cli.command_router import CommandRouter
from .cli.queue_processor import QueueProcessor
from .cli.base.aliases import normalize_node_alias, STATE_STACK_CANCEL_ALIASES
from .town_engine import TownEngine


class CLIRouter:
    def __init__(self, save_manager, engine):
        self.save_manager = save_manager
        self.engine = engine
        self.action_router = ActionRouter(save_manager, engine)
        self.command_router = CommandRouter(save_manager, engine)
        self.queue_processor = QueueProcessor(save_manager, engine)
        self._action_handlers = ActionHandler.registry
        self._command_handlers = CommandHandler.registry
        self.town_engine = TownEngine(save_manager, engine)

    def _execute_sub_action(self, user_id: str, run, parts: list[str]) -> Tuple[str, bool, bool]:
        return self.action_router.execute_action(self, user_id, run, parts)

    def _execute_queue(self, user_id: str, run, queue_content: str, results: list[str], interrupt_on_fail: bool = False) -> bool:
        return self.queue_processor.execute_queue(self, user_id, run, queue_content, results, interrupt_on_fail)

    def _handle_town_combat_settle(self, user_id: str, run: GameRun, original_res: str) -> str:
        latest_run = self.save_manager.load_save(user_id)
        zh_cn = self.town_engine._load_zh_cn()
        if not latest_run:
            stats = self.save_manager.load_stats(user_id)
            stats.in_town = True
            stats.town_pos = "range"
            self.save_manager.save_stats(user_id, stats)
            return original_res + "\n\n" + zh_cn.get("global", {}).get("combat_quit", "💀 你已退出了切磋，回到了靶场房间。") + "\n\n" + self.town_engine.render_current_room(user_id, stats)
        p = latest_run.player
        is_won = self.engine.is_battle_won(latest_run) or latest_run.node_type in ("reward", "victory")
        is_lost = p.hp <= 0
        if is_won or is_lost:
            self.save_manager.delete_save(user_id)
            stats = self.save_manager.load_stats(user_id)
            stats.in_town = True
            if is_lost:
                self.save_manager.save_stats(user_id, stats)
                return f"{original_res}\n\n" + zh_cn.get("global", {}).get("combat_lost", "💀 你被击败了！不过别担心，在主城的切磋不影响你的局外进度。你已回到了靶场房间。") + "\n\n" + self.town_engine.render_current_room(user_id, stats)
            npc_name = run.node_data.get("npc_name", "") or latest_run.node_data.get("npc_name", "")
            if npc_name == "NoobSlayer99" and stats.town_flags.get("quest_hammer_state") == "started":
                stats.town_flags["noob_coerced_hammer"] = True
            gp_gained = 0
            msg_bonus = ""
            if npc_name == "训练假人":
                msg_bonus = zh_cn.get("global", {}).get("combat_won_dummy", "训练假人已被摧毁！切磋完成。")
            else:
                if npc_name not in stats.defeated_town_npcs:
                    stats.defeated_town_npcs.append(npc_name)
                    if npc_name == "NoobSlayer99":
                        gp_gained = 100
                    elif npc_name == "xXx_SniperElite_xXx":
                        gp_gained = 150
                    elif npc_name == "Gate_Guardian":
                        gp_gained = 500
                    elif npc_name == "pppopipupu":
                        gp_gained = 1000
                    stats.gp += gp_gained
                    msg_bonus = zh_cn.get("global", {}).get("combat_won_first", "").format(name=npc_name, gp=gp_gained)
                else:
                    msg_bonus = zh_cn.get("global", {}).get("combat_won_repeat", "").format(name=npc_name)
            self.save_manager.save_stats(user_id, stats)
            return f"{original_res}\n\n" + zh_cn.get("global", {}).get("combat_won_banner", "🎉 战斗胜利！{bonus}").format(bonus=msg_bonus) + "\n\n" + self.town_engine.render_current_room(user_id, stats)
        return original_res

    def handle_command(self, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        for res in self._handle_command_raw(user_id, parts):
            yield res

    def _get_current_state(self, user_id: str, run) -> str:
        if run is not None:
            if getattr(run, "node_type", "") == "battle":
                return "battle"
            return "explore"
        stats = self.save_manager.load_stats(user_id)
        if stats is not None:
            if getattr(stats, "in_town", False):
                if stats.town_flags.get("current_dialog"):
                    return "dialog"
                return "town"
        return "menu"

    def _handle_command_raw(self, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        set_user_id(user_id)
        run = self.save_manager.load_save(user_id)
        curr_state = self._get_current_state(user_id, run)
        if parts:
            first_cmd = parts[0].lower()
            exempt_cmds = (
                "查询", "query", "info", "i",
                "背包", "bag", "inventory", "inv",
                "任务", "quest", "quests",
                "帮助", "help",
                "状态", "status",
                "统计", "stat", "stats",
                "地图", "map",
                "队列", "queue", "q",
                "qi", "queue_interrupt", "中断队列",
                "药水", "喝药水", "potion", "drink", "use_potion", "丢弃药水", "discard_potion", "drop_potion", "丢药", "dp", "dr", "pot", "投掷", "投", "throw", "t"
            )
            if first_cmd in exempt_cmds:
                handler = self._command_handlers.get(first_cmd)
                if handler:
                    if curr_state in getattr(handler, "allowed_states", []):
                        res_list = list(handler.execute(self, user_id, parts))
                        yield "\n".join(res_list)
                        return
                    else:
                        yield f"❌ 指令【{first_cmd}】在当前状态下不可用。"
                        return
        is_town_combat = run is not None and run.node_data.get("is_town_combat", False)
        if not parts:
            if run:
                yield GameRenderer.render_game(run)
            else:
                stats = self.save_manager.load_stats(user_id)
                if stats.in_town:
                    yield self.town_engine.render_current_room(user_id, stats)
                else:
                    yield GameRenderer.render_menu(stats)
            return
        if not run:
            stats = self.save_manager.load_stats(user_id)
            if stats.in_town:
                active_dialog = stats.town_flags.get("current_dialog")
                zh_cn = self.town_engine._load_zh_cn()
                if active_dialog:
                    input_str = " ".join(parts).strip()
                    yield self.town_engine.handle_dialog_input(user_id, input_str)
                    return
                cmd = parts[0].lower()
                if cmd in ("w", "a", "s", "d", "up", "down", "left", "right"):
                    yield self.town_engine.move(user_id, cmd)
                    return
                elif cmd in ("退出", "quit", "exit"):
                    stats.in_town = False
                    self.save_manager.save_stats(user_id, stats)
                    yield zh_cn.get("global", {}).get("town_exit_success", "👋 你已退出主城，回到主菜单。") + "\n\n" + GameRenderer.render_menu(stats)
                    return
                elif cmd in ("回城", "home"):
                    stats.town_pos = "square"
                    self.save_manager.save_stats(user_id, stats)
                    yield self.town_engine.render_current_room(user_id, stats)
                    return
                elif cmd in ("拿取", "捡起", "take", "pick"):
                    if len(parts) < 2:
                        yield zh_cn.get("global", {}).get("take_missing_param", "❌ 请提供物品名字，例如：take 幸运硬币")
                    else:
                        yield self.town_engine.pick_item(user_id, " ".join(parts[1:]))
                    return
                elif cmd in ("使用", "use"):
                    if len(parts) < 2:
                        yield zh_cn.get("global", {}).get("use_missing_param", "❌ 请指定使用的物品，例如：use 遗失的笔记本")
                    else:
                        yield self.town_engine.use_item(user_id, " ".join(parts[1:]))
                    return
                elif cmd in ("交互", "talk", "interact", "inter", "talk_to"):
                    if len(parts) < 2:
                        yield zh_cn.get("global", {}).get("talk_missing_param", "❌ 请指定交互的目标，例如：talk 向导长老")
                    else:
                        yield self.town_engine.talk_npc(user_id, " ".join(parts[1:]))
                    return
                elif cmd in ("查询", "query", "info", "i", "统计", "stat", "stats", "帮助", "help", "地图", "map"):
                    pass
                else:
                    yield zh_cn.get("global", {}).get("town_help_prompt", "🔮 主城探索中。输入 退出/exit 回到主菜单，或输入 W/A/S/D 进行移动。输入 交互/talk <目标> 开启互动。")
                    return
        if run and run.node_type == "cafe":
            from .cafe_engine import CafeEngine
            cafe = CafeEngine(self.save_manager, self.engine.map_engine)
            cmd = parts[0].lower()
            if cmd in ("look", "look_around", "看", "查"):
                yield cafe.render_cafe(run)
                return
            elif cmd in ("talk", "交互", "talk_to", "interact", "inter"):
                if len(parts) < 2:
                    yield "❌ 请指定交互的目标，例如：talk 向导长老"
                else:
                    yield cafe.talk_npc(run, " ".join(parts[1:]))
                return
            elif cmd in ("离开", "leave", "exit", "quit"):
                cafe_data = run.node_data.get("cafe_data", {})
                if cafe_data.get("active_npc") is not None:
                    yield cafe.leave_npc(run)
                else:
                    yield cafe.leave_cafe(run)
                return
            elif cmd in ("选择", "c") or cmd.isdigit():
                val = parts[1] if (cmd in ("选择", "c") and len(parts) > 1) else cmd
                if val.isdigit():
                    idx = int(val)
                    yield cafe.choose_option(run, idx)
                else:
                    yield "❌ 无效的选项序号。"
                return
            elif cmd in ("帮助", "help"):
                yield "💡 咖啡厅探索中。输入 离开 离开咖啡厅，或输入 talk <NPC名字> 进行交互。输入 看/查/look 重新观察四周。在对话中可直接输入选项数字。"
                return
            else:
                yield "❌ 未知咖啡厅命令。输入 看/查/look 查看四周，talk <NPC> 进行互动，或输入 离开 前往先古赐福。"
                return

        if run and run.node_data.get("state_stack"):
            res, term, success = self._execute_sub_action(user_id, run, parts)
            if is_town_combat:
                yield self._handle_town_combat_settle(user_id, run, res)
            else:
                yield res
            return
        parts = normalize_node_alias(run, parts)
        sub = parts[0]
        handler = self._command_handlers.get(sub)
        if handler:
            if curr_state in getattr(handler, "allowed_states", []):
                res_list = list(handler.execute(self, user_id, parts))
                res_text = "\n".join(res_list)
                if is_town_combat:
                    yield self._handle_town_combat_settle(user_id, run, res_text)
                else:
                    yield res_text
            else:
                yield f"❌ 指令【{sub}】在当前状态下不可用。"
        else:
            yield "🔮 未知子命令。输入 /rogue 帮助 或 /rogue help 获取帮助。"
