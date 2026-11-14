from typing import Tuple, Generator
from ...models.state import set_user_id, UserStats, GameRun
from ...renderer import GameRenderer, format_output_numbers
from .state_resolver import resolve_game_state
from .base import ActionHandler, CommandHandler
from .action_router import ActionRouter
from .command_router import CommandRouter
from .queue_processor import QueueProcessor
from .base.aliases import normalize_node_alias, STATE_STACK_CANCEL_ALIASES
from ..world.town.engine import TownEngine
from ..progress.checkin_service import CheckinService
from ..social.service import SocialService
from ..telemetry.projection_service import ProjectionService
from ..telemetry.log_service import LogService
from ...data.locale_data import get_locale_text
from ...data.temple_config import TEMPLE_COMBAT_FLAG
from ...data.outer_plane_config import OUTER_PLANE_COMBAT_FLAG, OUTER_PLANE_TRIGGER_FLAG



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
        self.checkin_service = CheckinService(save_manager)
        self.social_service = SocialService(save_manager, engine)
        self.projection_service = ProjectionService(save_manager)
        self.log_service = LogService(save_manager)

    def _execute_sub_action(self, user_id: str, run, parts: list[str]) -> Tuple[str, bool, bool]:
        return self.action_router.execute_action(self, user_id, run, parts)

    def _execute_queue(self, user_id: str, run, queue_content: str, results: list[str], interrupt_on_fail: bool = False) -> bool:
        return self.queue_processor.execute_queue(self, user_id, run, queue_content, results, interrupt_on_fail)

    def _handle_town_combat_settle(self, user_id: str, run: GameRun, original_res: str) -> str:
        latest_run = self.save_manager.load_save(user_id)
        if run.node_data.get(TEMPLE_COMBAT_FLAG):
            return self._handle_temple_combat_settle(user_id, run, latest_run, original_res)
        if run.node_data.get(OUTER_PLANE_COMBAT_FLAG):
            return self._handle_outer_plane_combat_settle(user_id, run, latest_run, original_res)
        if not latest_run:
            stats = self.save_manager.load_stats(user_id)
            stats.in_town = True
            stats.town_pos = "range"
            self.town_engine.record_visited_room(stats)
            self.save_manager.save_stats(user_id, stats)
            return original_res + "\n\n" + get_locale_text("i18n_cli_core.combat_quit") + "\n\n" + self.town_engine.render_current_room(user_id, stats)
        p = latest_run.player
        is_won = self.engine.is_battle_won(latest_run) or latest_run.node_type in ("reward", "victory")
        is_lost = p.hp <= 0
        if is_won or is_lost:
            self.save_manager.delete_save(user_id)
            stats = self.save_manager.load_stats(user_id)
            stats.in_town = True
            if is_lost:
                self.save_manager.save_stats(user_id, stats)
                return f"{original_res}\n\n" + get_locale_text("i18n_cli_core.combat_lost") + "\n\n" + self.town_engine.render_current_room(user_id, stats)
            npc_name = run.node_data.get("npc_name", "") or latest_run.node_data.get("npc_name", "")
            if npc_name == "NoobSlayer99" and stats.town_flags.get("quest_hammer_state") == "started":
                stats.town_flags["noob_coerced_hammer"] = True
            gp_gained = 0
            msg_bonus = ""
            if npc_name == get_locale_text("i18n_cli_core.npc_training_dummy"):
                msg_bonus = get_locale_text("i18n_cli_core.combat_won_dummy")
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
                    msg_bonus = get_locale_text("i18n_cli_core.combat_won_first", name=npc_name, gp=gp_gained)
                else:
                    msg_bonus = get_locale_text("i18n_cli_core.combat_won_repeat", name=npc_name)
            self.save_manager.save_stats(user_id, stats)
            return f"{original_res}\n\n" + get_locale_text("i18n_cli_core.combat_won_banner", bonus=msg_bonus) + "\n\n" + self.town_engine.render_current_room(user_id, stats)
        return original_res

    def _handle_temple_combat_settle(self, user_id: str, run: GameRun, latest_run, original_res: str) -> str:
        if latest_run is None:
            return original_res
        is_won = self.engine.is_battle_won(latest_run) or latest_run.node_type in ("reward", "victory")
        is_lost = latest_run.player.hp <= 0
        if not is_won and not is_lost:
            return original_res
        self.save_manager.delete_save(user_id)
        stats = self.save_manager.load_stats(user_id)
        temple = self.town_engine.temple_engine
        if is_lost:
            return original_res + "\n\n" + temple.on_battle_lose(user_id, stats, latest_run)
        return original_res + "\n\n" + temple.on_battle_win(user_id, stats, latest_run)

    def _handle_outer_plane_combat_settle(self, user_id: str, run: GameRun, latest_run, original_res: str) -> str:
        if latest_run is None:
            return original_res
        stats = self.save_manager.load_stats(user_id)
        plane = self.town_engine.outer_plane_engine
        if latest_run.node_data.get(OUTER_PLANE_TRIGGER_FLAG):
            self.save_manager.delete_save(user_id)
            return original_res + "\n\n" + plane.trigger_from_battle(user_id, stats)
        is_won = self.engine.is_battle_won(latest_run) or latest_run.node_type in ("reward", "victory")
        is_lost = latest_run.player.hp <= 0
        if not is_won and not is_lost:
            return original_res
        self.save_manager.delete_save(user_id)
        if is_lost:
            return original_res + "\n\n" + plane.on_battle_lose(user_id, stats, latest_run)
        return original_res + "\n\n" + plane.on_battle_win(user_id, stats, latest_run)

    def _projection_result(self, user_id: str, result: str) -> str:
        run = self.save_manager.load_save(user_id)
        if run is None:
            return result
        rendered = GameRenderer.render_game(run)
        if rendered:
            if result == rendered:
                return ""
            suffix = "\n" + rendered
            if result.endswith(suffix):
                return result[:-len(suffix)].rstrip()
        return result

    def handle_command(self, user_id: str, parts: list[str], project: bool = True) -> Generator[str, None, None]:
        command = " ".join(str(part) for part in parts).strip()
        before_run = self.save_manager.load_save(user_id) if command else None
        kind = "battle" if before_run is not None and before_run.node_type == "battle" else "action"
        actor_name = before_run.player.name if before_run is not None and before_run.player else ""
        results = []
        for res in self._handle_command_raw(user_id, parts):
            formatted = format_output_numbers(res)
            results.append(formatted)
            yield formatted
        if command:
            from ..progress.achievement_service import AchievementService
            ach = AchievementService(self.save_manager)
            ach.reconcile(user_id)
            pending = ach.pop_pending_notices(user_id)
            if pending:
                notice_text = format_output_numbers(ach.format_notices(pending))
                results.append(notice_text)
                yield notice_text
        if not command:
            return
        publish = project and self.projection_service.should_publish(command)
        record = self.log_service.should_record(command, before_run, user_id=user_id)
        if not publish and not record:
            return
        result = self._projection_result(user_id, "\n".join(results))
        if publish:
            self.projection_service.publish(user_id, command, result)
        if record:
            self.log_service.record(user_id, command, result, kind, before_run, actor_name)

    def _get_current_state(self, user_id: str, run) -> str:
        stats = None
        if run is None:
            stats = self.save_manager.load_stats(user_id)
        return resolve_game_state(run, stats)

    def _handle_command_raw(self, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        set_user_id(user_id)
        run = self.save_manager.load_save(user_id)
        curr_state = self._get_current_state(user_id, run)
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
        if run is None:
            stats = self.save_manager.load_stats(user_id)
            if stats.in_town:
                handler, _ = CommandHandler.resolve(parts[0].lower(), curr_state)
                if handler:
                    yield "\n".join(list(handler.execute(self, user_id, parts)))
                    return
                if curr_state == "temple" and parts[0].strip().isdigit():
                    yield self.town_engine.temple_engine.choose(user_id, stats, parts[0].strip())
                    return
                if curr_state == "outer_plane" and parts[0].strip().isdigit():
                    yield self.town_engine.outer_plane_engine.choose(user_id, stats, parts[0].strip())
                    return
                if stats.town_flags.get("current_dialog"):
                    yield self.town_engine.handle_dialog_input(user_id, " ".join(parts).strip())
                    return
                yield get_locale_text("i18n_cli_core.town_help_prompt")
                return
            parts = normalize_node_alias(run, parts)
            handler, exists = CommandHandler.resolve(parts[0].lower(), curr_state)
            if handler:
                yield "\n".join(list(handler.execute(self, user_id, parts)))
                return
            if exists:
                yield get_locale_text("i18n_cli_core.err_command_unavailable", cmd=parts[0].lower())
                return
            yield get_locale_text("i18n_cli_core.unknown_subcommand")
            return

        from ..party.mercenary import handle_merc_dialog_input, is_in_merc_dialog, render_merc_dialog
        sub = parts[0].lower()
        if is_in_merc_dialog(run, user_id):
            if sub in ("离开", "leave", "exit", "quit", "取消", "cancel") or parts[0].lstrip("-").isdigit():
                res = handle_merc_dialog_input(run, user_id, " ".join(parts))
                self.save_manager.save_save(user_id, run)
                yield res
                return
            if sub in ("status", "r", "状态"):
                yield format_output_numbers(render_merc_dialog(run, user_id))
                return
            dialog_handler, _ = CommandHandler.resolve(sub, curr_state)
            if dialog_handler and sub not in ("对话", "交谈", "talk", "talk_to", "interact", "inter"):
                res_list = list(dialog_handler.execute(self, user_id, parts))
                yield "\n".join(res_list)
                return
            res = handle_merc_dialog_input(run, user_id, " ".join(parts))
            self.save_manager.save_save(user_id, run)
            yield res
            return
        if run.node_data.get("state_stack"):
            res, term, success = self._execute_sub_action(user_id, run, parts)
            if is_town_combat:
                yield self._handle_town_combat_settle(user_id, run, res)
            else:
                yield res
            return
        handler, exists = CommandHandler.resolve(sub, curr_state)
        if handler:
            res_list = list(handler.execute(self, user_id, parts))
            res_text = "\n".join(res_list)
            if is_town_combat:
                yield self._handle_town_combat_settle(user_id, run, res_text)
            else:
                yield res_text
            return
        normalized = normalize_node_alias(run, parts)
        if normalized != parts:
            norm_handler, _ = CommandHandler.resolve(normalized[0].lower(), curr_state)
            if norm_handler:
                parts = normalized
                res_list = list(norm_handler.execute(self, user_id, parts))
                res_text = "\n".join(res_list)
                if is_town_combat:
                    yield self._handle_town_combat_settle(user_id, run, res_text)
                else:
                    yield res_text
                return
        if exists:
            yield get_locale_text("i18n_cli_core.err_command_unavailable", cmd=sub)
            return
        res, term, success = self._execute_sub_action(user_id, run, parts)
        if is_town_combat:
            yield self._handle_town_combat_settle(user_id, run, res)
        else:
            yield res
