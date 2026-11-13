from typing import Generator
from ...base import CommandHandler
from .....renderer import GameRenderer

class BagCommand(CommandHandler, names=["背包", "bag", "inventory", "inv"], allowed_states=["menu", "town", "grid_map", "explore", "battle", "dialog", "cafe"], help_key="bag"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        stats = router.save_manager.load_stats(user_id)
        run = router.save_manager.load_save(user_id)
        mode = None
        if len(parts) >= 2:
            arg = parts[1].strip().lower()
            if arg in ("t", "town", "主城"):
                mode = "t"
            elif arg in ("r", "rogue", "肉鸽"):
                mode = "r"
            else:
                from .....data.locale_data import get_locale_text
                yield get_locale_text("i18n_room_interact.bag.invalid_mode")
                return
        yield GameRenderer.render_bag(stats, run=run, mode=mode)
