from typing import Generator

from ...base import CommandHandler


class ButcherAttackCommand(CommandHandler, names=["攻击", "attack", "atk", "打"], allowed_states=["temple", "outer_plane"], help_key="butcher_attack"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        stats = router.save_manager.load_stats(user_id)
        if router.town_engine.temple_engine.is_active(stats):
            yield router.town_engine.temple_engine.attack(user_id, stats)
        else:
            yield router.town_engine.outer_plane_engine.attack(user_id, stats)
