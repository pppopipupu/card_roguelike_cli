from typing import Generator
from ...base import CommandHandler
from ...queue_processor import count_queue_commands
from ...state_resolver import resolve_game_state
from .....renderer import GameRenderer
from .....renderer.formatters import format_output_numbers
from .....data.progression.balance_config import QUEUE_MAX_COMMANDS
from .....data.text.locale_data import get_locale_text


def _merge_logs_and_state(log_block: str, rendered: str) -> str:
    log_text = (log_block or "").strip()
    state_text = (rendered or "").strip()
    if not state_text:
        return log_text
    if not log_text:
        return state_text
    if state_text in format_output_numbers(log_text):
        return log_text
    return f"{log_text}\n\n{state_text}"


class QueueCommand(CommandHandler, names=["队列", "q", "queue", "qi", "queue_interrupt", "中断队列"], allowed_states=["menu", "town", "grid_map", "explore", "battle", "dialog", "cafe", "outer_plane"], help_key="queue"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        if len(parts) < 2:
            yield get_locale_text("i18n_cli_commands.battle_queue_missing_arg")
            return
        is_qi = parts[0].lower() in ("qi", "queue_interrupt", "中断队列")
        full_arg = " ".join(parts[1:]).strip()
        run = router.save_manager.load_save(user_id)
        if run:
            results = []
            router._execute_queue(user_id, run, full_arg, results, interrupt_on_fail=is_qi)
            run = router.save_manager.load_save(user_id)
            log_block = "\n".join(r.strip() for r in results if r and r.strip())
            if not run or run.player.hp <= 0:
                yield log_block
            else:
                yield _merge_logs_and_state(log_block, GameRenderer.render_game(run))
        else:
            if count_queue_commands(full_arg) > QUEUE_MAX_COMMANDS:
                yield get_locale_text("i18n_cli_commands.battle_queue_limit", limit=QUEUE_MAX_COMMANDS)
                return
            content = full_arg
            from ...queue_processor import split_queue_items
            items = split_queue_items(content)
            results = []
            executed_any = False
            from .....models.state import in_queue_ctx
            queue_token = in_queue_ctx.set(True)
            try:
                for item in items:
                    if not item:
                        continue
                    parts_sub = item.split()
                    if not parts_sub:
                        continue
                    executed_any = True
                    first_sub = parts_sub[0].lower()
                    latest_run = router.save_manager.load_save(user_id)
                    if latest_run is not None:
                        router._execute_queue(user_id, latest_run, item, results, interrupt_on_fail=is_qi)
                        continue
                    stats = router.save_manager.load_stats(user_id)
                    curr_state = resolve_game_state(None, stats)
                    cmd_handler, exists = CommandHandler.resolve(first_sub, curr_state)
                    if cmd_handler:
                        gen = cmd_handler.execute(router, user_id, parts_sub)
                        res_list = []
                        success = True
                        try:
                            while True:
                                res_list.append(next(gen))
                        except StopIteration as e:
                            success = e.value if e.value is not None else True
                        res = "\n".join(r.strip() for r in res_list if r and r.strip())
                    elif curr_state == "outer_plane" and first_sub.isdigit():
                        res = router.town_engine.outer_plane_engine.choose(user_id, stats, first_sub)
                        success = "❌" not in res
                    elif curr_state == "dialog" and stats.town_flags.get("current_dialog"):
                        res = router.town_engine.handle_dialog_input(user_id, item)
                        success = "❌" not in res
                    elif exists:
                        res = get_locale_text("i18n_cli_commands.err_command_unavailable", sub=first_sub)
                        success = False
                    else:
                        res = get_locale_text("i18n_cli_commands.err_unknown_command", sub=first_sub)
                        success = False
                    if res and res.strip():
                        results.append(res.strip())
                    if is_qi and not success:
                        break
            finally:
                in_queue_ctx.reset(queue_token)
            if not executed_any:
                yield get_locale_text("i18n_cli_commands.battle_queue_no_valid")
                return
            log_block = "\n".join(r.strip() for r in results if r and r.strip())
            latest_run = router.save_manager.load_save(user_id)
            if latest_run is not None and latest_run.player.hp > 0:
                final_state = GameRenderer.render_game(latest_run)
            else:
                stats = router.save_manager.load_stats(user_id)
                final_state = router.town_engine.render_current_room(user_id, stats) if stats.in_town else GameRenderer.render_menu(stats)
            yield _merge_logs_and_state(log_block, final_state)
