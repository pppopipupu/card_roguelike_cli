from typing import Generator

from ....achievement_service import AchievementService
from .....data.locale_data import get_locale_text
from .....renderer.menu import render_reader_page
from ...base import CommandHandler

RARITY_ALIASES = {
    "common": "common",
    "普通": "common",
    "rare": "rare",
    "稀有": "rare",
    "epic": "epic",
    "珍奇": "epic",
    "legendary": "legendary",
    "传奇": "legendary",
}

ALL_VIEW_ALIASES = ("全览", "reveal", "unlock", "all", "开启全览")
CONFIRM_ALIASES = ("confirm", "确认", "yes", "y")
UNLOCKED_ALIASES = ("已解锁", "unlocked")


class AchievementCommand(
    CommandHandler,
    names=["成就", "achievement", "achi", "ach", "成就列表"],
    allowed_states=["menu", "town", "explore", "battle", "dialog", "cafe"],
    help_key="achievement",
):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        service = AchievementService(router.save_manager)
        stats = router.save_manager.load_stats(user_id)
        service.reconcile(user_id, stats=stats, save=True)
        pending = service.pop_pending_notices(user_id)
        notice_prefix = (service.format_notices(pending) + "\n\n") if pending else ""

        args = [str(p).strip().lower() for p in parts[1:] if str(p).strip()]
        if args and args[0] in ALL_VIEW_ALIASES:
            confirmed = len(args) > 1 and args[1] in CONFIRM_ALIASES
            _, msg = service.purchase_all_view(user_id, confirmed=confirmed)
            yield notice_prefix + msg
            return

        rarity_filter = None
        only_unlocked = False
        page = 1

        for arg in args:
            if arg.isdigit():
                page = max(1, int(arg))
            elif arg in RARITY_ALIASES:
                rarity_filter = RARITY_ALIASES[arg]
            elif arg in UNLOCKED_ALIASES:
                only_unlocked = True
            else:
                yield notice_prefix + get_locale_text("i18n_achievement.err_invalid_filter")
                return

        stats = router.save_manager.load_stats(user_id)
        title, items = service.build_reader_data(
            stats,
            rarity_filter=rarity_filter,
            only_unlocked=only_unlocked,
        )
        total_pages = max(1, (len(items) + 9) // 10)
        stats.reader_title = title
        stats.reader_items = items
        stats.reader_page = min(page, total_pages)
        stats.reader_active = True
        stats.reader_mode = "achievement"
        router.save_manager.save_stats(user_id, stats)
        yield notice_prefix + render_reader_page(stats)
