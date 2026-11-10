from typing import Generator
from ...base import CommandHandler
from ...queue_processor import count_queue_commands
from .....renderer import GameRenderer
from .....data.balance_config import QUEUE_MAX_COMMANDS
from .....data.locale_data import get_locale_text

class QueueCommand(CommandHandler, names=["队列", "q", "queue", "qi", "queue_interrupt", "中断队列"], help_key="queue"):
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
            if not run or run.player.hp <= 0:
                yield "\n".join(results)
            else:
                yield "\n".join(results) + "\n" + GameRenderer.render_game(run)
        else:
            if count_queue_commands(full_arg) > QUEUE_MAX_COMMANDS:
                yield get_locale_text("i18n_cli_commands.battle_queue_limit", limit=QUEUE_MAX_COMMANDS)
                return
            content = full_arg
            if content.startswith("[") and content.endswith("]"):
                content = content[1:-1].strip()
            from ...base import split_by_comma_with_brackets
            items = split_by_comma_with_brackets(content)
            results = []
            for item in items:
                if not item:
                    continue
                parts_sub = item.split()
                if not parts_sub:
                    continue
                first_sub = parts_sub[0].lower()
                cmd_handler = router._command_handlers.get(first_sub)
                if cmd_handler:
                    curr_state = "menu"
                    stats = router.save_manager.load_stats(user_id)
                    if stats and stats.in_town:
                        curr_state = "town"
                    if curr_state in getattr(cmd_handler, "allowed_states", []):
                        gen = cmd_handler.execute(router, user_id, parts_sub)
                        res_list = []
                        success = True
                        try:
                            while True:
                                res_list.append(next(gen))
                        except StopIteration as e:
                            success = e.value if e.value is not None else True
                        res = "\n".join(res_list)
                    else:
                        res = get_locale_text("i18n_cli_commands.err_command_unavailable", sub=first_sub)
                        success = False
                else:
                    res = get_locale_text("i18n_cli_commands.err_unknown_command", sub=first_sub)
                    success = False
                results.append(res)
                if is_qi and not success:
                    break
            if results:
                yield "\n\n".join(results)
            else:
                yield get_locale_text("i18n_cli_commands.battle_queue_no_valid")
