from typing import Tuple, Generator
from ..models.state import set_user_id, UserStats, GameRun
from ..renderer import GameRenderer
from .state_resolver import resolve_game_state
from .cli.base import ActionHandler, CommandHandler
from .cli.action_router import ActionRouter
from .cli.command_router import CommandRouter
from .cli.queue_processor import QueueProcessor
from .cli.base.aliases import normalize_node_alias, STATE_STACK_CANCEL_ALIASES
from .town_engine import TownEngine
from .checkin_service import CheckinService
from .social_service import SocialService
from ..data.locale_data import get_locale_text


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

    def _record_coop_action(self, user_id: str, parts: list[str]) -> None:
        command = " ".join(str(part) for part in parts).strip()
        if not command:
            return
        run = self.save_manager.load_save(user_id)
        if run is None or not getattr(run, "coop_id", ""):
            return
        name = run.player.name if run.player and run.player.name else get_locale_text("i18n_cli_core.default_player_name")
        history = run.node_data.setdefault("coop_action_history", [])
        history.append(f"[{name}] {command}")
        if len(history) > 60:
            del history[:-60]
        self.save_manager.save_coop_save(user_id, run)

    def handle_command(self, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        self._record_coop_action(user_id, parts)
        for res in self._handle_command_raw(user_id, parts):
            yield res

    def _get_current_state(self, user_id: str, run) -> str:
        stats = None
        if run is None:
            stats = self.save_manager.load_stats(user_id)
        return resolve_game_state(run, stats)

    def _handle_command_raw(self, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        set_user_id(user_id)
        run = self.save_manager.load_save(user_id)
        if run is not None and run.node_type == "map_select":
            if self.engine.map_engine.sync_corpse_options(run):
                self.save_manager.save_save(user_id, run)
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

        if run.node_data.get("state_stack"):
            res, term, success = self._execute_sub_action(user_id, run, parts)
            if is_town_combat:
                yield self._handle_town_combat_settle(user_id, run, res)
            else:
                yield res
            return
        sub = parts[0].lower()
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
