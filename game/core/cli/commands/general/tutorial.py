from typing import Generator
from ...base import CommandHandler
from .....renderer import GameRenderer
from .....data.text.locale_data import get_locale_text
from ....world.tutorial import finish_tutorial_run, is_tutorial_run, start_tutorial_run


class TutorialCommand(CommandHandler, names=["教程", "tutorial"], help_key="tutorial"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        sub = parts[1].strip().lower() if len(parts) > 1 else ""
        if sub in ("play", "start", "replay", "开始", "重玩", "演练"):
            yield from NewbieTutorialCommand().execute(router, user_id, parts)
            return
        if sub in ("skip", "跳过"):
            yield from SkipTutorialCommand().execute(router, user_id, parts)
            return
        yield GameRenderer.render_tutorial()


class NewbieTutorialCommand(
    CommandHandler,
    names=["新手教程", "重玩教程", "newbie", "tutorial_play"],
    allowed_states=["menu", "town", "dialog"],
    help_key="newbie_tutorial",
):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        run = router.save_manager.load_save(user_id)
        if run is not None:
            if is_tutorial_run(run):
                yield GameRenderer.render_game(run)
                return
            yield get_locale_text("i18n_tutorial.flow.cannot_start_active")
            return
        stats = router.save_manager.load_stats(user_id)
        return_to_town = bool(getattr(stats, "in_town", False))
        _, text = start_tutorial_run(
            router.save_manager,
            router.engine,
            user_id,
            return_to_town=return_to_town,
        )
        yield text


class SkipTutorialCommand(
    CommandHandler,
    names=["跳过教程", "跳过新手教程", "skip_tutorial", "skiptut"],
    allowed_states=["grid_map", "explore", "battle", "cafe", "dialog"],
    help_key="skip_tutorial",
):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        run = router.save_manager.load_save(user_id)
        if not is_tutorial_run(run):
            yield get_locale_text("i18n_tutorial.flow.not_in_tutorial")
            return
        yield finish_tutorial_run(router.save_manager, router.town_engine, user_id, skipped=True)
