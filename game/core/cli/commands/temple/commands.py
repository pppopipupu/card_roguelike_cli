from typing import Generator

from ...base import CommandHandler


class TempleEnterCommand(CommandHandler, names=["神殿", "temple", "出城"], allowed_states=["town"], help_key="temple_enter"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        stats = router.save_manager.load_stats(user_id)
        yield router.town_engine.temple_engine.enter(user_id, stats)


class TempleChooseCommand(CommandHandler, names=["go", "g", "前往", "抉择", "choose", "ch"], allowed_states=["temple"], help_key="temple_choose"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        stats = router.save_manager.load_stats(user_id)
        token = " ".join(parts[1:]).strip()
        yield router.town_engine.temple_engine.choose(user_id, stats, token)


class TempleLookCommand(CommandHandler, names=["看", "look", "神殿状态", "tstatus"], allowed_states=["temple"], help_key="temple_look"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        stats = router.save_manager.load_stats(user_id)
        yield router.town_engine.temple_engine.render(user_id, stats)


class TempleReadCommand(CommandHandler, names=["翻阅", "阅读", "开卷", "read", "tread"], allowed_states=["temple"], help_key="temple_read"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        stats = router.save_manager.load_stats(user_id)
        yield router.town_engine.temple_engine.read(user_id, stats)


class TempleLeaveCommand(CommandHandler, names=["撤离", "离开神殿", "retreat", "templequit"], allowed_states=["temple"], help_key="temple_leave"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        stats = router.save_manager.load_stats(user_id)
        yield router.town_engine.temple_engine.leave(user_id, stats)
