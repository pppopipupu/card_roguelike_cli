from typing import Generator
from ...base import CommandHandler
from .....renderer import GameRenderer
from .....data.locale_data import get_locale_text

class ChooseCommand(CommandHandler, names=["选择", "c"], allowed_states=["menu", "explore", "battle", "cafe"], help_key="choose"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        run = router.save_manager.load_save(user_id)
        if run is not None and run.node_type == "cafe":
            val = parts[1] if len(parts) > 1 else parts[0]
            if val.isdigit():
                from ....cafe_engine import CafeEngine
                cafe = CafeEngine(router.save_manager, router.engine.map_engine)
                yield cafe.choose_option(run, int(val))
            else:
                yield get_locale_text("i18n_cli_general_b.err_invalid_option_index")
            return
        if not run:
            if len(parts) > 1:
                arg = parts[1].lower()
                if arg in ("wizard", "warrior", "wiz", "war", "法师", "战士", "1", "2", "3", "0", "选择", "时序法师", "塑能法师", "秘钥学者"):
                    yield get_locale_text("i18n_cli_general_b.err_no_game_class_hint")
                    return
            yield get_locale_text("i18n_cli_general_b.err_no_active_game")
            return
        res, term, success = router._execute_sub_action(user_id, run, parts)
        if term or (run and run.node_data.get("in_queue")):
            yield res
        else:
            yield res + "\n" + GameRenderer.render_game(run)
        return success
