from typing import Generator

from ...base import CommandHandler


class OuterPlaneLookCommand(CommandHandler, names=["看", "look", "位面状态", "ostatus"], allowed_states=["outer_plane"], help_key="outer_plane_look"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        stats = router.save_manager.load_stats(user_id)
        yield router.town_engine.outer_plane_engine.look(user_id, stats)
