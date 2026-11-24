from typing import Generator
from ...base import CommandHandler
from .....renderer import GameRenderer
from .....renderer.formatters import format_output_numbers
from .....data.text.locale_data import get_locale_text

class ChooseCommand(CommandHandler, names=["选择", "c"], allowed_states=["menu", "explore", "battle", "cafe", "outer_plane"], help_key="choose"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        run = router.save_manager.load_save(user_id)
        state = router._get_current_state(user_id, run)
        if state == "outer_plane":
            stats = router.save_manager.load_stats(user_id)
            token = " ".join(parts[1:]).strip()
            if token.lower() in ("取消", "离开", "返回", "cancel", "leave", "back", "0", "q"):
                yield router.town_engine.outer_plane_engine.leave(user_id, stats)
            elif not token:
                yield get_locale_text("i18n_cli_general_b.err_invalid_option_index")
            else:
                yield router.town_engine.outer_plane_engine.choose(user_id, stats, token)
            return
        run = router.save_manager.load_save(user_id)
        if run is not None and run.node_type == "cafe":
            val = parts[1] if len(parts) > 1 else parts[0]
            if run.node_data.get("pending_upgrade"):
                if val.lower() in ("取消", "离开", "返回", "cancel", "leave", "back", "0", "q"):
                    run.node_data["pending_upgrade"] = False
                    router.save_manager.save_save(user_id, run)
                    yield get_locale_text("i18n_cli_core.msg_cancel_upgrade")
                elif val.isdigit():
                    res = router.engine.upgrade_card_in_deck(run, int(val))
                    router.save_manager.save_save(user_id, run)
                    yield res
                else:
                    yield get_locale_text("i18n_cli_general_b.err_invalid_option_index")
                return
            if val.isdigit():
                from ....world.cafe.engine import CafeEngine
                cafe = CafeEngine(router.save_manager, router.engine.map_engine)
                res = cafe.choose_option(run, int(val))
                if res == "UPGRADE_FLOW":
                    run.node_data["pending_upgrade"] = True
                    router.save_manager.save_save(user_id, run)
                    yield get_locale_text("i18n_cli_core.msg_upgrade_flow_started")
                else:
                    yield res
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
            rendered = GameRenderer.render_game(run)
            res_text = res or ""
            if rendered and rendered.strip() in format_output_numbers(res_text):
                yield res_text
            elif not res_text.strip():
                yield rendered
            else:
                yield res_text + "\n" + rendered
        return success
