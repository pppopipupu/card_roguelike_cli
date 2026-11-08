import asyncio
from typing import Optional, List, Dict
from ..models.manager import SaveManager
from ..engine import GameEngine
from .cli_router import CLIRouter
from .cli.base.aliases import (
    NODE_EXIT_ALIASES, NODE_CANCEL_ALIASES,
    STATE_STACK_CANCEL_ALIASES, has_pending_node_cancel,
)
from ..renderer.menu import render_reader_page
from ..renderer import GameRenderer
from ..cards import resolve_card_id, ALL_CARDS

class HeadlessGameServer:
    def __init__(self, data_dir: Optional[str] = None):
        self.save_manager = SaveManager(data_dir)
        self.engine = GameEngine(self.save_manager)
        self.cli_router = CLIRouter(self.save_manager, self.engine)
        self.user_locks = {}

    def _get_user_lock(self, user_id: str) -> asyncio.Lock:
        if user_id not in self.user_locks:
            self.user_locks[user_id] = asyncio.Lock()
        return self.user_locks[user_id]

    def _sync_player_name(self, user_id: str, sender_name: str):
        stats = self.save_manager.load_stats(user_id)
        if stats:
            if sender_name != "玩家" and getattr(stats, "player_name", "玩家") != sender_name:
                stats.player_name = sender_name
                self.save_manager.save_stats(user_id, stats)
        run = self.save_manager.load_save(user_id)
        if run and run.player:
            current_name = getattr(stats, "player_name", "玩家") if stats else sender_name
            if run.player.name != current_name:
                run.player.name = current_name
                self.save_manager.save_save(user_id, run)

    def _get_current_state(self, user_id: str, run, stats) -> str:
        if run is not None:
            if getattr(run, "node_type", "") == "battle":
                return "battle"
            if getattr(run, "node_type", "") == "cafe":
                return "cafe"
            return "explore"
        if stats is not None:
            if getattr(stats, "in_town", False):
                if stats.town_flags.get("current_dialog"):
                    return "dialog"
                return "town"
        return "menu"

    async def handle_rogue_message(self, user_id: str, sender_name: str, message: str, shortcut_prefix: list[str] = None, enable_shortcut: bool = True, force_execute: bool = False) -> Optional[str]:
        if shortcut_prefix is None:
            shortcut_prefix = [".rogue"]

        self._sync_player_name(user_id, sender_name)
        stats = self.save_manager.load_stats(user_id)
        run = self.save_manager.load_save(user_id)

        if stats and stats.reader_active:
            message_str = message.strip()
            clean_str = message_str
            for p in sorted(shortcut_prefix, key=len, reverse=True):
                if clean_str.lower().startswith(p.lower()):
                    clean_str = clean_str[len(p):].strip()
                    break
            parts = clean_str.split()
            if parts:
                cmd = parts[0].lower()
                if cmd in ("下一页", "n", "next", "上一页", "b", "back", "prev", "退出", "quit", "exit"):
                    if cmd in ("退出", "quit", "exit"):
                        stats.reader_active = False
                        self.save_manager.save_stats(user_id, stats)
                        return "🚪 已退出阅读器。"
                    elif cmd in ("下一页", "n", "next"):
                        total_items = len(stats.reader_items)
                        total_pages = (total_items + 9) // 10
                        if stats.reader_page >= total_pages:
                            return "⚠️ 已经是最后一页了。"
                        stats.reader_page += 1
                        self.save_manager.save_stats(user_id, stats)
                        return render_reader_page(stats)
                    elif cmd in ("上一页", "b", "back", "prev"):
                        if stats.reader_page <= 1:
                            return "⚠️ 已经是第一页了。"
                        stats.reader_page -= 1
                        self.save_manager.save_stats(user_id, stats)
                        return render_reader_page(stats)
                else:
                    stats.reader_active = False
                    self.save_manager.save_stats(user_id, stats)

        message_str = message.strip()

        if force_execute:
            clean_str = message_str
            for p in sorted(shortcut_prefix, key=len, reverse=True):
                if clean_str.lower().startswith(p.lower()):
                    clean_str = clean_str[len(p):].strip()
                    break
            parts = clean_str.split()
            if parts and parts[0].lower() in ("rogue", "/rogue"):
                parts = parts[1:]
            
            lock = self._get_user_lock(user_id)
            async with lock:
                res_list = list(self.cli_router.handle_command(user_id, parts))
                if res_list:
                    return "\n".join(res_list)
                return ""

        matched_p = None
        matched_idx = -1
        for p in sorted(shortcut_prefix, key=len, reverse=True):
            idx = message_str.find(p)
            if idx == -1:
                continue
            cmd_part = message_str[idx:]
            parts = cmd_part.split()
            if parts and parts[0].lower().startswith(p.lower()):
                matched_p = p
                matched_idx = idx
                break

        if matched_p is not None:
            cmd_part = message_str[matched_idx:]
            parts = cmd_part.split()
            parts[0] = parts[0][len(matched_p):]
            if not parts[0]:
                parts = parts[1:]
            
            lock = self._get_user_lock(user_id)
            async with lock:
                res_list = list(self.cli_router.handle_command(user_id, parts))
                if res_list:
                    return "\n".join(res_list)
                return ""

        if not enable_shortcut:
            return None

        rogue_mode = stats.rogue_mode if stats else False
        if not rogue_mode:
            return None

        parts = message_str.split()
        if not parts:
            return None

        first_word = parts[0].lower()
        is_game_cmd = False
        if run and run.node_data.get("state_stack") and first_word in STATE_STACK_CANCEL_ALIASES:
            is_game_cmd = True
        curr_state = self._get_current_state(user_id, run, stats)

        if curr_state == "dialog":
            dialog_valid_cmds = {
                "查询", "query", "info", "i",
                "背包", "bag", "inventory", "inv",
                "任务", "quest", "quests",
                "帮助", "help",
                "状态", "status",
                "统计", "stat", "stats",
                "地图", "map",
                "队列", "queue", "q",
                "锁定", "lock", "锁定管理", "解锁", "unlock",
                "qi", "queue_interrupt", "中断队列"
            }
            if first_word.isdigit() or first_word in ("离开", "退出", "返回", "exit", "quit") or first_word in dialog_valid_cmds:
                is_game_cmd = True
        elif curr_state == "town":
            town_nav_cmds = {
                "w", "a", "s", "d", "up", "down", "left", "right", 
                "退出", "quit", "exit", "回城", "home", 
                "拿取", "捡起", "take", "pick", "使用", "use", 
                "交互", "talk", "interact", "inter", "talk_to"
            }
            if first_word in town_nav_cmds:
                is_game_cmd = True
            elif first_word in self.cli_router._command_handlers:
                handler = self.cli_router._command_handlers[first_word]
                if curr_state in getattr(handler, "allowed_states", []):
                    is_game_cmd = True
        elif curr_state == "cafe":
            cafe_data = run.node_data.get("cafe_data", {})
            active_npc = cafe_data.get("active_npc")
            if active_npc is not None:
                dialog_valid_cmds = {
                    "查询", "query", "info", "i",
                    "背包", "bag", "inventory", "inv",
                    "任务", "quest", "quests",
                    "帮助", "help",
                    "状态", "status",
                    "统计", "stat", "stats",
                    "地图", "map",
                    "队列", "queue", "q",
                    "锁定", "lock", "锁定管理", "解锁", "unlock",
                    "qi", "queue_interrupt", "中断队列"
                }
                if first_word.isdigit() or first_word in ("离开", "退出", "返回", "exit", "quit", "leave") or first_word in dialog_valid_cmds or first_word in ("选择", "c"):
                    is_game_cmd = True
            else:
                cafe_lobby_cmds = {
                    "交互", "talk", "interact", "inter", "talk_to",
                    "离开", "leave", "exit", "quit",
                    "看", "查", "look", "look_around",
                    "帮助", "help",
                    "查询", "query", "info", "i",
                    "背包", "bag", "inventory", "inv",
                    "任务", "quest", "quests",
                    "状态", "status",
                    "统计", "stat", "stats",
                    "地图", "map",
                    "队列", "queue", "q"
                }
                if first_word in cafe_lobby_cmds:
                    is_game_cmd = True
        else:
            if first_word in self.cli_router._command_handlers:
                handler = self.cli_router._command_handlers[first_word]
                if curr_state in getattr(handler, "allowed_states", []):
                    is_game_cmd = True
            if not is_game_cmd and run is not None:
                if first_word.isdigit():
                    is_game_cmd = True
                elif curr_state == "explore" and not run.node_data.get("state_stack"):
                    if first_word in NODE_EXIT_ALIASES:
                        is_game_cmd = True
                    elif first_word in NODE_CANCEL_ALIASES and has_pending_node_cancel(run):
                        is_game_cmd = True

        if is_game_cmd:
            lock = self._get_user_lock(user_id)
            async with lock:
                res_list = list(self.cli_router.handle_command(user_id, parts))
                if res_list:
                    return "\n".join(res_list)
                return ""

        return None

    async def handle_admin_message(self, user_id: str, message: str) -> str:
        parts = message.strip().split()
        if len(parts) > 0 and parts[0].lower() in ("rogueadmin", "/rogueadmin"):
            parts = parts[1:]

        if not parts:
            return (
                "💬 /rogueadmin 管理指令帮助：\n"
                "• 查看当前最终BOSS：/rogueadmin boss\n"
                "• 设置随机轮换：/rogueadmin boss set random\n"
                "• 固定最终BOSS：/rogueadmin boss set 腐化之心 或 Icerainboww\n"
                "• 开启/关闭 Icerainboww：/rogueadmin icerainboww <on/off>\n"
                "• 立即跳到某一层：/rogueadmin jump <层数> 或 /rogueadmin jump <玩家ID> <层数>\n"
                "• 向玩家牌组添加卡牌：/rogueadmin add_card <卡牌名称/ID> [玩家ID]"
            )

        cmd = parts[0].lower()
        if cmd == "boss":
            if len(parts) == 1:
                cfg = self.save_manager.load_admin_config()
                boss = cfg.get("final_boss", "random")
                boss_zh = "随机轮换" if boss == "random" else boss
                return f"⚙️ 当前最终BOSS配置为：【{boss_zh}】"
            elif len(parts) >= 3 and parts[1].lower() == "set":
                target_boss = parts[2]
                if target_boss.lower() in ("random", "随机", "轮换"):
                    self.save_manager.save_admin_config({"final_boss": "random"})
                    return "⚙️ 最终BOSS已成功设置为：【随机轮换】"
                elif target_boss in ("腐化之心", "Icerainboww"):
                    self.save_manager.save_admin_config({"final_boss": target_boss})
                    return f"⚙️ 最终BOSS已成功固定为：【{target_boss}】"
                else:
                    return "❌ 错误：无效的BOSS名称。可选值：random, 腐化之心, Icerainboww"
            else:
                return "❌ 错误：无效指令。请使用 /rogueadmin boss set <random/腐化之心/Icerainboww>"
        elif cmd == "icerainboww":
            if len(parts) == 1:
                cfg = self.save_manager.load_admin_config()
                status = cfg.get("icerainboww_enabled", True)
                status_zh = "开启" if status else "关闭"
                return f"⚙️ 当前 icerainboww 相关内容配置状态为：【{status_zh}】"
            elif len(parts) >= 2:
                target_status = parts[1].lower()
                cfg = self.save_manager.load_admin_config()
                if target_status in ("on", "开启", "enable", "true"):
                    cfg["icerainboww_enabled"] = True
                    self.save_manager.save_admin_config(cfg)
                    return "⚙️ icerainboww 相关内容已成功【开启】！"
                elif target_status in ("off", "关闭", "disable", "false"):
                    cfg["icerainboww_enabled"] = False
                    self.save_manager.save_admin_config(cfg)
                    return "⚙️ icerainboww 相关内容已成功【关闭】！所有 icerainboww 卡牌与 BOSS 已被禁用。"
                else:
                    return "❌ 错误：无效的参数。可选值：on, off, 开启, 关闭"
            else:
                return "❌ 错误：无效指令。请使用 /rogueadmin icerainboww <on/off>"
        elif cmd == "jump":
            if len(parts) == 2:
                target_user_id = user_id
                stage_str = parts[1]
            elif len(parts) >= 3:
                target_user_id = parts[1]
                stage_str = parts[2]
            else:
                return "❌ 错误：无效指令。请使用 /rogueadmin jump <层数> 或 /rogueadmin jump <玩家ID> <层数>"
            try:
                target_stage = int(stage_str)
            except ValueError:
                return "❌ 错误：层数必须是整数"
            if not (1 <= target_stage <= 32):
                return "❌ 错误：层数范围必须在 1 到 32 之间"
            lock = self._get_user_lock(target_user_id)
            async with lock:
                run = self.save_manager.load_save(target_user_id)
                if not run:
                    return "❌ 错误：未找到该玩家的活跃游戏存档。"
                msg = self.engine.jump_to_stage(run, target_stage)
                return f"⚙️ {msg}\n\n{GameRenderer.render_game(run)}"
        elif cmd == "add_card":
            if len(parts) == 2:
                card_input = parts[1]
                target_user_id = user_id
            elif len(parts) >= 3:
                card_input = parts[1]
                target_user_id = parts[2]
                resolved = resolve_card_id(card_input)
                if not resolved:
                    resolved_alt = resolve_card_id(parts[2])
                    if resolved_alt:
                        card_input = parts[2]
                        target_user_id = parts[1]
            else:
                return "❌ 错误：无效指令。请使用 /rogueadmin add_card <卡牌名称/ID> [玩家ID]"
            
            upgraded = card_input.endswith("+")
            card_id = resolve_card_id(card_input)
            if not card_id:
                return f"❌ 错误：未找到卡牌【{card_input}】"
            
            lock = self._get_user_lock(target_user_id)
            async with lock:
                run = self.save_manager.load_save(target_user_id)
                if not run:
                    return "❌ 错误：未找到该玩家的活跃游戏存档。"
                
                card_obj = ALL_CARDS.get(card_id)
                card_name = card_obj.name if card_obj else card_id
                if upgraded:
                    card_name += "+"
                
                from ..models.state import CardState
                card_state = CardState(id=card_id, upgraded=upgraded)
                run.player.deck.append(card_state)
                in_battle = (run.node_type == "battle")
                if in_battle:
                    run.player.hand.append(card_state)
                    
                self.save_manager.save_save(target_user_id, run)
                
                if in_battle:
                    msg = f"已成功将卡牌【{card_name}】添加到玩家【{target_user_id}】的牌组，且由于处于战斗中，该牌已直接加入手牌！"
                else:
                    msg = f"已成功将卡牌【{card_name}】添加到玩家【{target_user_id}】的牌组！"
                    
                return f"⚙️ {msg}\n\n{GameRenderer.render_game(run)}"
        else:
            return "❌ 错误：未知管理命令，请输入 /rogueadmin 查看帮助。"
