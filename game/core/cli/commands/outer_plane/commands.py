from typing import Generator

from ...base import CommandHandler


class OuterPlaneChooseCommand(CommandHandler, names=["go", "g", "前往", "抉择", "choose", "ch"], allowed_states=["outer_plane"], help_key="outer_plane_choose"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        stats = router.save_manager.load_stats(user_id)
        yield router.town_engine.outer_plane_engine.choose(user_id, stats, " ".join(parts[1:]).strip())


class OuterPlaneLookCommand(CommandHandler, names=["看", "look", "位面状态", "ostatus"], allowed_states=["outer_plane"], help_key="outer_plane_look"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        stats = router.save_manager.load_stats(user_id)
        yield router.town_engine.outer_plane_engine.look(user_id, stats)


class OuterPlaneLeaveCommand(CommandHandler, names=["撤离", "离开位面", "retreat", "opquit"], allowed_states=["outer_plane"], help_key="outer_plane_leave"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        stats = router.save_manager.load_stats(user_id)
        yield router.town_engine.outer_plane_engine.leave(user_id, stats)
