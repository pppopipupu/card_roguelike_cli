from typing import Generator
from ...base import CommandHandler
from .....renderer import GameRenderer
from .....data.locale_data import get_locale_text

class QueryCommand(CommandHandler, names=["查询", "query", "info", "i"], allowed_states=["menu", "town", "grid_map", "explore", "battle", "dialog", "cafe"], help_key="query"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        run = router.save_manager.load_save(user_id)
        if len(parts) > 1:
            query_str = " ".join(parts[1:]).strip().lower()
            if query_str in ("抽牌堆", "draw", "draw_pile"):
                if not run:
                    yield get_locale_text("i18n_cli_general_b.err_no_active_game")
                elif run.node_type != "battle":
                    yield get_locale_text("i18n_cli_general_b.err_battle_piles_only")
                else:
                    yield GameRenderer.render_draw_pile(run)
            elif query_str in ("弃牌堆", "discard", "discard_pile"):
                if not run:
                    yield get_locale_text("i18n_cli_general_b.err_no_active_game")
                elif run.node_type != "battle":
                    yield get_locale_text("i18n_cli_general_b.err_battle_piles_only")
                else:
                    yield GameRenderer.render_discard_pile(run)
            elif query_str in ("消耗堆", "exhaust", "exhaust_pile"):
                if not run:
                    yield get_locale_text("i18n_cli_general_b.err_no_active_game")
                elif run.node_type != "battle":
                    yield get_locale_text("i18n_cli_general_b.err_battle_piles_only")
                else:
                    yield GameRenderer.render_exhaust_pile(run)
            elif query_str in ("随从墓地", "mg", "minion_graveyard", "minion_grave"):
                if not run:
                    yield get_locale_text("i18n_cli_general_b.err_no_active_game")
                elif run.node_type != "battle":
                    yield get_locale_text("i18n_cli_general_b.err_battle_graveyard_only")
                else:
                    yield GameRenderer.render_minion_graveyard(run)
            elif query_str in ("敌人墓地", "eg", "enemy_graveyard", "enemy_grave"):
                if not run:
                    yield get_locale_text("i18n_cli_general_b.err_no_active_game")
                elif run.node_type != "battle":
                    yield get_locale_text("i18n_cli_general_b.err_battle_graveyard_only")
                else:
                    yield GameRenderer.render_enemy_graveyard(run)
            else:
                yield GameRenderer.render_query_info(" ".join(parts[1:]).strip(), user_id, run)
        else:
            if not run:
                yield get_locale_text("i18n_cli_general_b.query_no_game_hint")
            elif run.node_type != "battle":
                yield get_locale_text("i18n_cli_general_b.query_not_battle_hint")
            else:
                yield GameRenderer.render_detailed_battle(run)
