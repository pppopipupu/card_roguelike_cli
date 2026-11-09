from typing import Generator
from ...base import CommandHandler
from .....renderer import GameRenderer

class StartCommand(CommandHandler, names=["开启", "start"], allowed_states=["menu", "town", "explore", "battle"]):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        run = router.save_manager.load_save(user_id)
        if run:
            if len(parts) > 1 and parts[1] in ("确认", "confirm"):
                new_run = router.engine.start_new_game(user_id)
                if not new_run:
                    yield "❌ 你当前处于联机队伍或联机牌局中，无法开启单人冒险。组队阶段可输入 team leave，联机牌局可输入 abandon confirm。"
                    return
                yield "已重新开始新的一局游戏。\n" + GameRenderer.render_game(new_run)
            else:
                yield "⚠️ 你当前已有一局正在进行中的游戏。若要强制重新开始并覆盖存档，请输入：\n/rogue start confirm"
        else:
            new_run = router.engine.start_new_game(user_id)
            if not new_run:
                yield "❌ 你当前处于联机队伍或联机牌局中，无法开启单人冒险。组队阶段可输入 team leave，联机牌局可输入 abandon confirm。"
                return
            yield GameRenderer.render_game(new_run)
