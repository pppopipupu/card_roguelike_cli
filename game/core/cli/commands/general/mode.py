from typing import Generator
from ...base import CommandHandler

class ModeCommand(CommandHandler, names=["mode", "模式"], allowed_states=["menu", "town", "dialog", "explore", "battle"]):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        stats = router.save_manager.load_stats(user_id)
        stats.rogue_mode = not stats.rogue_mode
        if stats.rogue_mode:
            stats.duel_mode = False
        router.save_manager.save_stats(user_id, stats)
        status_str = "开启" if stats.rogue_mode else "关闭"
        yield f"✨ 免前缀肉鸽模式已{status_str}！此设置仅对你个人生效。"
