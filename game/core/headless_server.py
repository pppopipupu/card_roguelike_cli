import asyncio
from typing import Optional, List, Dict
from ..models.manager import SaveManager
from ..models.state import set_user_id
from ..engine import GameEngine
from .cli_router import CLIRouter
from .state_resolver import resolve_game_state
from .cli.base import CommandHandler
from .cli.base.aliases import (
    NODE_EXIT_ALIASES, NODE_CANCEL_ALIASES,
    STATE_STACK_CANCEL_ALIASES, has_pending_node_cancel,
)
from ..renderer.menu import render_reader_page
from ..renderer import GameRenderer
from ..cards import resolve_card_id, ALL_CARDS
from ..data.locale_data import get_locale_text

class HeadlessGameServer:
    def __init__(self, data_dir: Optional[str] = None):
        self.save_manager = SaveManager(data_dir)
        self.engine = GameEngine(self.save_manager)
        self.cli_router = CLIRouter(self.save_manager, self.engine)
        self.user_locks = {}

    def _get_user_lock(self, user_id: str) -> asyncio.Lock:
        resolve_key = getattr(self.save_manager, "resolve_lock_key", None)
        key = resolve_key(user_id) if callable(resolve_key) else f"user:{user_id}"
        lock = self.user_locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self.user_locks[key] = lock
        return lock

    def _sync_player_name(self, user_id: str, sender_name: str):
        stats = self.save_manager.load_stats(user_id)
        default_name = get_locale_text("i18n_cli_core.default_player_name")
        if stats:
            if sender_name != default_name and getattr(stats, "player_name", default_name) != sender_name:
                stats.player_name = sender_name
                self.save_manager.save_stats(user_id, stats)
        run = self.save_manager.load_save(user_id)
        if run and run.player:
            current_name = getattr(stats, "player_name", default_name) if stats else sender_name
            if run.player.name != current_name:
                run.player.name = current_name
                self.save_manager.save_save(user_id, run)

    def _get_current_state(self, user_id: str, run, stats) -> str:
        return resolve_game_state(run, stats)

    async def handle_rogue_message(self, user_id: str, sender_name: str, message: str, shortcut_prefix: list[str] = None, enable_shortcut: bool = True, force_execute: bool = False) -> Optional[str]:
        set_user_id(user_id)
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
                        return get_locale_text("i18n_cli_core.reader_exited")
                    elif cmd in ("下一页", "n", "next"):
                        total_items = len(stats.reader_items)
                        total_pages = (total_items + 9) // 10
                        if stats.reader_page >= total_pages:
                            return get_locale_text("i18n_cli_core.reader_last_page")
                        stats.reader_page += 1
                        self.save_manager.save_stats(user_id, stats)
                        return render_reader_page(stats)
                    elif cmd in ("上一页", "b", "back", "prev"):
                        if stats.reader_page <= 1:
                            return get_locale_text("i18n_cli_core.reader_first_page")
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
        _, exists = CommandHandler.resolve(first_word, curr_state)
        if exists:
            is_game_cmd = True
        if curr_state == "dialog":
            if first_word.isdigit() or first_word in ("离开", "退出", "返回", "exit", "quit"):
                is_game_cmd = True
        elif curr_state == "cafe":
            cafe_data = run.node_data.get("cafe_data", {}) if run else {}
            if cafe_data.get("active_npc") is not None:
                if first_word.isdigit() or first_word in ("选择", "c") or exists:
                    is_game_cmd = True
            elif exists:
                is_game_cmd = True
        else:
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
        set_user_id(user_id)
        parts = message.strip().split()
        if len(parts) > 0 and parts[0].lower() in ("rogueadmin", "/rogueadmin"):
            parts = parts[1:]

        if not parts:
            return get_locale_text("i18n_cli_core.admin_help")

        cmd = parts[0].lower()
        if cmd == "boss":
            if len(parts) == 1:
                cfg = self.save_manager.load_admin_config()
                boss = cfg.get("final_boss", "random")
                boss_zh = get_locale_text("i18n_cli_core.random_rotation") if boss == "random" else boss
                return get_locale_text("i18n_cli_core.admin_boss_current", boss=boss_zh)
            elif len(parts) >= 3 and parts[1].lower() == "set":
                target_boss = parts[2]
                if target_boss.lower() in ("random", "随机", "轮换"):
                    self.save_manager.save_admin_config({"final_boss": "random"})
                    return get_locale_text("i18n_cli_core.admin_boss_set_random")
                elif target_boss in ("腐化之心", "Icerainboww"):
                    self.save_manager.save_admin_config({"final_boss": target_boss})
                    return get_locale_text("i18n_cli_core.admin_boss_set_fixed", boss=target_boss)
                else:
                    return get_locale_text("i18n_cli_core.err_admin_invalid_boss")
            else:
                return get_locale_text("i18n_cli_core.err_admin_boss_usage")
        elif cmd == "icerainboww":
            if len(parts) == 1:
                cfg = self.save_manager.load_admin_config()
                status = cfg.get("icerainboww_enabled", True)
                status_zh = get_locale_text("i18n_cli_core.status_enabled") if status else get_locale_text("i18n_cli_core.status_disabled")
                return get_locale_text("i18n_cli_core.admin_icerainboww_current", status=status_zh)
            elif len(parts) >= 2:
                target_status = parts[1].lower()
                cfg = self.save_manager.load_admin_config()
                if target_status in ("on", "开启", "enable", "true"):
                    cfg["icerainboww_enabled"] = True
                    self.save_manager.save_admin_config(cfg)
                    return get_locale_text("i18n_cli_core.admin_icerainboww_enabled")
                elif target_status in ("off", "关闭", "disable", "false"):
                    cfg["icerainboww_enabled"] = False
                    self.save_manager.save_admin_config(cfg)
                    return get_locale_text("i18n_cli_core.admin_icerainboww_disabled")
                else:
                    return get_locale_text("i18n_cli_core.err_admin_icerainboww_param")
            else:
                return get_locale_text("i18n_cli_core.err_admin_icerainboww_usage")
        elif cmd == "jump":
            if len(parts) == 2:
                target_user_id = user_id
                stage_str = parts[1]
            elif len(parts) >= 3:
                target_user_id = parts[1]
                stage_str = parts[2]
            else:
                return get_locale_text("i18n_cli_core.err_admin_jump_usage")
            try:
                target_stage = int(stage_str)
            except ValueError:
                return get_locale_text("i18n_cli_core.err_admin_jump_int")
            if not (1 <= target_stage <= 32):
                return get_locale_text("i18n_cli_core.err_admin_jump_range")
            lock = self._get_user_lock(target_user_id)
            async with lock:
                run = self.save_manager.load_save(target_user_id)
                if not run:
                    return get_locale_text("i18n_cli_core.err_admin_no_save")
                msg = self.engine.jump_to_stage(run, target_stage)
                return get_locale_text("i18n_cli_core.admin_action_result", msg=msg, rendered=GameRenderer.render_game(run))
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
                return get_locale_text("i18n_cli_core.err_admin_add_card_usage")
            
            upgraded = card_input.endswith("+")
            card_id = resolve_card_id(card_input)
            if not card_id:
                return get_locale_text("i18n_cli_core.err_admin_card_not_found", card_input=card_input)
            
            lock = self._get_user_lock(target_user_id)
            async with lock:
                run = self.save_manager.load_save(target_user_id)
                if not run:
                    return get_locale_text("i18n_cli_core.err_admin_no_save")
                
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
                    msg = get_locale_text("i18n_cli_core.admin_card_added_battle", card_name=card_name, target_user_id=target_user_id)
                else:
                    msg = get_locale_text("i18n_cli_core.admin_card_added", card_name=card_name, target_user_id=target_user_id)
                    
                return get_locale_text("i18n_cli_core.admin_action_result", msg=msg, rendered=GameRenderer.render_game(run))
        else:
            return get_locale_text("i18n_cli_core.err_admin_unknown")
