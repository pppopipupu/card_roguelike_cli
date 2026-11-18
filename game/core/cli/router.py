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
from ..battle.engine import BattleEngine
from ..social.service import SocialService
from ..world.world_social import WorldSocialService
from ..world.presence import set_active_service
from ..telemetry.projection_service import ProjectionService
from ..telemetry.log_service import LogService
from ..text.pipeline import render_text_node
from ...data.locale_data import get_locale_text
from ...data.open_world_config import (
    OPEN_WORLD_COMBAT_FLAG,
    OPEN_WORLD_GHOST_ID_KEY,
    OPEN_WORLD_ORIGIN_KEY,
    OPEN_WORLD_SETTLED_MSG_KEY,
)
from ...data.outer_plane_config import OUTER_PLANE_ACTIVE_FLAG, OUTER_PLANE_COMBAT_FLAG, OUTER_PLANE_TRIGGER_FLAG
from ...data.world_social_config import WORLD_PLAYER_DIALOG_EXIT_WORDS
from ..world.open_world.loadout_service import is_open_world_run



class CLIRouter:
    def __init__(self, save_manager, engine):
        self.save_manager = save_manager
        self.engine = engine
        self.action_router = ActionRouter(save_manager, engine)
        self.command_router = CommandRouter(save_manager, engine)
        self.queue_processor = QueueProcessor(save_manager, engine)
        self._action_handlers = ActionHandler.registry
        self._command_handlers = CommandHandler.registry
        self.world_social = WorldSocialService(save_manager)
        set_active_service(self.world_social.presence)
        self.town_engine = TownEngine(save_manager, engine)
        self.town_engine.world_social = self.world_social
        self.engine.map_engine.grid_map_service.world_social = self.world_social
        self.engine.map_engine.town_engine = self.town_engine
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

    def _handle_open_world_combat_settle(self, user_id: str, run: GameRun | None, original_res: str) -> str:
        latest_run = self.save_manager.load_save(user_id)
        plane = self.town_engine.outer_plane_engine
        if latest_run is not None:
            stats = self.save_manager.load_stats(user_id)
            if latest_run.node_data.get(OUTER_PLANE_TRIGGER_FLAG):
                self.save_manager.delete_save(user_id)
                return original_res + "\n\n" + plane.trigger_from_battle(user_id, stats)
            if run is not None and run.node_type == "battle" and latest_run.node_type == "grid_map":
                notice = str(latest_run.node_data.pop("notice", "") or "").strip()
                if notice:
                    self.save_manager.save_save(user_id, latest_run)
                rendered_map = GameRenderer.render_game(latest_run)
                parts_out = [original_res]
                if notice and notice not in original_res:
                    parts_out.append(notice)
                if rendered_map and rendered_map not in original_res:
                    parts_out.append(rendered_map)
                return "\n\n".join(part for part in parts_out if part)
            if latest_run.node_data.get(OUTER_PLANE_COMBAT_FLAG) and not latest_run.node_data.get(OPEN_WORLD_GHOST_ID_KEY):
                is_won = self.engine.is_battle_won(latest_run) or latest_run.node_type in ("reward", "victory")
                is_lost = latest_run.player.hp <= 0
                if not is_won and not is_lost:
                    return original_res
                if is_lost:
                    return original_res + "\n\n" + plane.on_battle_lose(user_id, stats, latest_run)
                self.save_manager.delete_save(user_id)
                return original_res + "\n\n" + plane.on_battle_win(user_id, stats, latest_run)
            return original_res

        stats = self.save_manager.load_stats(user_id)
        settled_msg = run.node_data.get(OPEN_WORLD_SETTLED_MSG_KEY, "") if run is not None else ""
        origin = run.node_data.get(OPEN_WORLD_ORIGIN_KEY, "") if run is not None else ""
        if origin == "outer_plane" and stats.town_flags.get(OUTER_PLANE_ACTIVE_FLAG):
            rendered_room = plane.look(user_id, stats)
            if not settled_msg or settled_msg in original_res:
                return f"{original_res}\n\n{rendered_room}".strip()
            return f"{original_res}\n\n{settled_msg}\n\n{rendered_room}".strip()
        if settled_msg:
            stats.in_town = True
            self.town_engine.record_visited_room(stats)
            self.save_manager.save_stats(user_id, stats)
            rendered_room = self.town_engine.render_current_room(user_id, stats)
            if settled_msg in original_res:
                return f"{original_res}\n\n{rendered_room}".strip()
            return f"{original_res}\n\n{settled_msg}\n\n{rendered_room}".strip()
        if stats.in_town:
            square_title = get_locale_text("rooms.square.name")
            if square_title not in original_res:
                return f"{original_res}\n\n{self.town_engine.render_current_room(user_id, stats)}".strip()
        return original_res

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

    def _drain_unread_logs(self, user_id: str) -> list[str]:
        after_run = self.save_manager.load_save(user_id)
        if after_run is None:
            return self.world_social.pop_pending_logs(user_id)
        battle_engine = getattr(self.engine, "battle_engine", self.engine)
        lines: list[str] = []
        if isinstance(battle_engine, BattleEngine):
            before_logs = list(after_run.node_data.get("battle_logs") or [])
            nodes = battle_engine._take_battle_logs(after_run, user_id)
            after_logs = list(after_run.node_data.get("battle_logs") or [])
            if before_logs != after_logs:
                self.save_manager.save_save(user_id, after_run)
            for node in nodes:
                rendered = render_text_node(node)
                if rendered:
                    lines.append(rendered)
        extra_pending = self.world_social.pop_pending_logs(user_id)
        if extra_pending:
            lines.extend(extra_pending)
        return lines

    def handle_command(self, user_id: str, parts: list[str], project: bool = True) -> Generator[str, None, None]:
        command = " ".join(str(part) for part in parts).strip()
        set_active_service(self.world_social.presence)
        from ..battle.pvp_service import PvpService
        battle_engine = getattr(self.engine, "battle_engine", self.engine)
        rope_notice = PvpService.check_and_advance_rope(
            self.save_manager,
            battle_engine,
            self.town_engine,
            self.world_social,
            user_id,
        )
        self.world_social.refresh(user_id)
        status_refresh = not parts or str(parts[0]).strip().lower() in ("状态", "status", "r", "rogue", "肉鸽")
        if status_refresh:
            invite_popup = PvpService.render_invite_popup(self.save_manager, user_id)
            if invite_popup:
                status_run = self.save_manager.load_save(user_id)
                if status_run is None or status_run.node_type != "battle":
                    yield invite_popup
                    return
        before_run = self.save_manager.load_save(user_id) if command else None
        kind = "battle" if before_run is not None and before_run.node_type == "battle" else "action"
        actor_name = before_run.player.name if before_run is not None and before_run.player else ""
        raw_outputs = [
            format_output_numbers(res)
            for res in self._handle_command_raw(user_id, parts)
            if res is not None and str(res) != ""
        ]
        unread_logs = []
        if rope_notice:
            unread_logs.append(format_output_numbers(rope_notice))
        unread_logs.extend(
            format_output_numbers(log_line)
            for log_line in self._drain_unread_logs(user_id)
            if log_line is not None and str(log_line).strip() != ""
        )
        results = []
        if unread_logs:
            log_block = "\n".join(unread_logs)
            if raw_outputs:
                log_block = f"{log_block}\n{get_locale_text('i18n_grid_map.separator')}"
            results.append(log_block)
            yield log_block
        for formatted in raw_outputs:
            results.append(formatted)
            yield formatted
        after_run = self.save_manager.load_save(user_id)
        if after_run is None or after_run.node_type != "battle":
            pvp_popup = PvpService.render_invite_popup(self.save_manager, user_id)
            if pvp_popup:
                results.append(pvp_popup)
                yield pvp_popup
        self.world_social.refresh(user_id)
        if command:
            from ..progress.achievement_service import AchievementService
            ach = AchievementService(self.save_manager)
            ach.reconcile(user_id)
            pending = ach.pop_pending_notices(user_id)
            if pending:
                notice_text = format_output_numbers(ach.format_notices(pending))
                results.append(notice_text)
                yield notice_text
        mail_notice = self.world_social.notify(user_id)
        if mail_notice:
            results.append(mail_notice)
            yield mail_notice
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

    def _try_pvp_invite_input(self, user_id: str, parts: list[str], stats=None, curr_state: str = "") -> str | None:
        if not parts:
            return None
        pvp = getattr(self.save_manager, "pvp", None)
        if pvp is None:
            return None
        invite = pvp.get_invite(user_id)
        if invite is None:
            return None
        from ..battle.pvp_service import PvpService
        action = PvpService.match_invite_action(parts)
        if action is None:
            return None
        head = parts[0].strip().lower()
        if len(parts) == 1 and head in ("1", "2", "3"):
            if stats is None:
                stats = self.save_manager.load_stats(user_id)
            if (
                curr_state in ("dialog", "battle", "outer_plane", "explore", "cafe")
                or stats.town_flags.get("current_dialog")
                or self.world_social.has_dialog(user_id, stats)
            ):
                return None
        battle_engine = getattr(self.engine, "battle_engine", self.engine)
        _, msg = PvpService.respond_invite(
            self.save_manager, battle_engine, self.world_social, user_id, action
        )
        return msg

    def _try_player_dialog_input(self, user_id: str, parts: list[str], stats=None) -> str | None:
        if not parts:
            return None
        if stats is None:
            stats = self.save_manager.load_stats(user_id)
        if not self.world_social.has_dialog(user_id, stats):
            return None
        head = parts[0].strip().lower()
        choice_token = None
        if len(parts) == 1 and (head.isdigit() or head in WORLD_PLAYER_DIALOG_EXIT_WORDS):
            choice_token = head
        elif head in ("选择", "c") and len(parts) == 2:
            choice_token = parts[1].strip().lower()
        if choice_token is not None:
            return self.world_social.handle_dialog_choice(user_id, choice_token, stats=stats)
        self.world_social.clear_dialog(user_id, stats=stats)
        return None

    def _post_command_settle(self, user_id: str, run: GameRun | None, is_town_combat: bool, is_open_world: bool, text: str) -> str:
        if is_town_combat and run is not None:
            return self._handle_town_combat_settle(user_id, run, text)
        if is_open_world:
            return self._handle_open_world_combat_settle(user_id, run, text)
        return text

    def _handle_command_raw(self, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        set_user_id(user_id)
        run = self.save_manager.load_save(user_id)
        curr_state = self._get_current_state(user_id, run)
        is_open_world = is_open_world_run(run)
        is_town_combat = run is not None and run.node_data.get("is_town_combat", False) and not is_open_world
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
                pvp_res = self._try_pvp_invite_input(user_id, parts, stats=stats, curr_state=curr_state)
                if pvp_res is not None:
                    yield pvp_res
                    return
                player_dialog_res = self._try_player_dialog_input(user_id, parts, stats=stats)
                if player_dialog_res is not None:
                    yield player_dialog_res
                    return
                handler, _ = CommandHandler.resolve(parts[0].lower(), curr_state)
                if handler:
                    yield "\n".join(list(handler.execute(self, user_id, parts)))
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

        pvp_res = self._try_pvp_invite_input(user_id, parts, curr_state=curr_state)
        if pvp_res is not None:
            yield pvp_res
            return
        player_dialog_res = self._try_player_dialog_input(user_id, parts)
        if player_dialog_res is not None:
            yield player_dialog_res
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
            yield self._post_command_settle(user_id, run, is_town_combat, is_open_world, res)
            return
        from ..world.tutorial import finish_tutorial_run, is_tutorial_run
        if is_tutorial_run(run) and sub in ("skip", "跳过"):
            yield finish_tutorial_run(self.save_manager, self.town_engine, user_id, skipped=True)
            return
        handler, exists = CommandHandler.resolve(sub, curr_state)
        if handler:
            res_list = list(handler.execute(self, user_id, parts))
            res_text = "\n".join(res_list)
            yield self._post_command_settle(user_id, run, is_town_combat, is_open_world, res_text)
            return
        normalized = normalize_node_alias(run, parts)
        if normalized != parts:
            norm_handler, _ = CommandHandler.resolve(normalized[0].lower(), curr_state)
            if norm_handler:
                parts = normalized
                res_list = list(norm_handler.execute(self, user_id, parts))
                res_text = "\n".join(res_list)
                yield self._post_command_settle(user_id, run, is_town_combat, is_open_world, res_text)
                return
        if exists:
            yield get_locale_text("i18n_cli_core.err_command_unavailable", cmd=sub)
            return
        res, term, success = self._execute_sub_action(user_id, run, parts)
        yield self._post_command_settle(user_id, run, is_town_combat, is_open_world, res)
