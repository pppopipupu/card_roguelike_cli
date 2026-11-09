from typing import Generator
from ...base import CommandHandler

class AbandonCommand(CommandHandler, names=["放弃", "abandon"], allowed_states=["explore", "battle"]):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        run = router.save_manager.load_save(user_id)
        if not run:
            yield "❌ 你当前没有正在进行的游戏。"
            return
        if len(parts) > 1 and parts[1] in ("确认", "confirm"):
            if getattr(run, "coop_id", ""):
                settle_msg = router.save_manager.settle_coop_game_and_delete(user_id, run, is_victory=False, create_corpse=False, force=True)
                yield f"已放弃当前联机牌局，全队进度已结算。\n{settle_msg}"
                return
            settle_msg = router.save_manager.settle_game_and_delete(user_id, run, is_victory=False, create_corpse=False)
            yield f"已放弃当前局内游戏，当前进度已清空。\n{settle_msg}"
        else:
            yield "⚠️ 确认放弃当前游戏？放弃后进度将无法恢复。确认请输入：\n/rogue abandon confirm"
