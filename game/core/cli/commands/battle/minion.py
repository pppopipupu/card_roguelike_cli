from typing import Generator
from ...base import CommandHandler, split_by_comma_with_brackets
from .....renderer import GameRenderer
from .....data.locale_data import get_locale_text

class MinionCommand(CommandHandler, names=["随从", "m"], allowed_states=["battle"]):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        run = router.save_manager.load_save(user_id)
        if not run:
            yield get_locale_text("i18n_cli_commands.err_no_active_game")
            return
        if len(parts) < 2:
            yield get_locale_text("i18n_cli_commands.battle_minion_missing_arg")
            return
        full_arg = " ".join(parts[1:])
        is_queue = False
        if "," in full_arg:
            sub_parts = split_by_comma_with_brackets(full_arg)
            is_queue = True
            valid_parts_count = 0
            for sp in sub_parts:
                sp_clean = sp.strip()
                if not sp_clean:
                    continue
                valid_parts_count += 1
                words = sp_clean.split()
                if len(words) < 2:
                    is_queue = False
                    break
            if valid_parts_count <= 1:
                is_queue = False
        if is_queue:
            items = split_by_comma_with_brackets(full_arg)
            converted_items = []
            for item in items:
                item_str = item.strip()
                if not item_str:
                    continue
                if item_str.startswith("随从 ") or item_str.startswith("m "):
                    converted_items.append(item_str)
                else:
                    converted_items.append(f"随从 {item_str}")
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
