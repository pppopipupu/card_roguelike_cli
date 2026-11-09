from typing import Generator
from ...base import CommandHandler
from .....data.locale_data import get_locale_text

class CafeLookCommand(CommandHandler, names=["look", "look_around", "看", "查"], allowed_states=["cafe"]):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        run = router.save_manager.load_save(user_id)
        if not run:
            return
        from ....cafe_engine import CafeEngine
        cafe = CafeEngine(router.save_manager, router.engine.map_engine)
        yield cafe.render_cafe(run)

class CafeTalkCommand(CommandHandler, names=["交互", "talk", "talk_to", "interact", "inter"], allowed_states=["cafe"]):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        run = router.save_manager.load_save(user_id)
        if not run:
            return
        if len(parts) < 2:
            yield get_locale_text("i18n_cli_commands.cafe_talk_missing_target")
            return
        from ....cafe_engine import CafeEngine
        cafe = CafeEngine(router.save_manager, router.engine.map_engine)
        yield cafe.talk_npc(run, " ".join(parts[1:]))

class CafeLeaveCommand(CommandHandler, names=["离开", "leave", "exit", "quit"], allowed_states=["cafe"]):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        run = router.save_manager.load_save(user_id)
        if not run:
            return
        from ....cafe_engine import CafeEngine
        cafe = CafeEngine(router.save_manager, router.engine.map_engine)
        cafe_data = run.node_data.get("cafe_data", {})
        if cafe_data.get("active_npc") is not None:
            yield cafe.leave_npc(run)
        else:
            yield cafe.leave_cafe(run)

class CafeHelpCommand(CommandHandler, names=["帮助", "help"], allowed_states=["cafe"]):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        yield get_locale_text("i18n_cli_commands.cafe_help")
