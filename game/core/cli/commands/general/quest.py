from typing import Generator
from ...base import CommandHandler

class QuestListCommand(CommandHandler, names=["任务", "quest", "quests"], help_key="quest_list"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        stats = router.save_manager.load_stats(user_id)
        from ....town.quest_manager import QuestManager
        yield QuestManager.render_quests(stats)
