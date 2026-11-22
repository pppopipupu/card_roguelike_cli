from typing import Generator
from ...base import CommandHandler
from .....renderer import GameRenderer
from .....data.text.locale_data import get_locale_text
from .....models.state import GameRun
from ....world.open_world.loadout_service import OpenWorldLoadoutService


class DeckCommand(CommandHandler, names=["牌组", "deck"], allowed_states=["menu", "town", "grid_map", "explore", "battle", "outer_plane"], help_key="deck"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        run = router.save_manager.load_save(user_id)
        if run:
            yield GameRenderer.render_deck(run)
            return
        stats = router.save_manager.load_stats(user_id)
        if stats.in_town:
            player = OpenWorldLoadoutService.build_player_state(user_id, stats)
            router.save_manager.save_stats(user_id, stats)
            tmp_run = GameRun(user_id=user_id, node_type="town", player=player)
            yield GameRenderer.render_deck(tmp_run)
            return
        yield get_locale_text("i18n_cli_general_b.err_deck_no_game")
