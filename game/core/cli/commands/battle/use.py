from typing import Generator
from ...base import CommandHandler
from .....renderer import GameRenderer
from .....data.locale_data import get_locale_text

class UseCommand(CommandHandler, names=["使用", "p"], allowed_states=["battle"]):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        run = router.save_manager.load_save(user_id)
        if not run:
            yield get_locale_text("i18n_cli_commands.err_no_active_game")
            return
        if len(parts) < 2:
            yield get_locale_text("i18n_cli_commands.battle_use_missing_arg")
            return
        full_arg = " ".join(parts[1:])
        is_queue = False
        if full_arg.startswith("[") or "," in full_arg:
            is_queue = True
        if is_queue:
            clean_arg = full_arg.replace("[", "").replace("]", "").replace(" ", "")
            items = clean_arg.split(",")
            converted_items = []
            for item in items:
                if not item:
                    continue
                if ":" in item:
                    idx_str, target = item.split(":", 1)
                    converted_items.append(f"使用 {idx_str} {target}")
                else:
                    converted_items.append(f"使用 {item}")
            queue_str = "[" + ", ".join(converted_items) + "]"
            results = []
            success = router._execute_queue(user_id, run, queue_str, results)
            run = router.save_manager.load_save(user_id)
            if not run:
                yield "\n".join(results)
            else:
                yield "\n".join(results) + "\n" + GameRenderer.render_game(run)
            return success
        else:
            res, term, success = router._execute_sub_action(user_id, run, parts)
            if term or (run and run.node_data.get("in_queue")):
                yield res
            else:
                yield res + "\n" + GameRenderer.render_game(run)
            return success
