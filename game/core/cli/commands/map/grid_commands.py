from typing import Generator
from ...base import CommandHandler
from .....data.locale_data import get_locale_text
from .....renderer import GameRenderer
from ....landmark_system import open_room_talk
from ....mercenary import find_mercenary_uid, open_merc_dialog


class GridMoveCommand(CommandHandler, names=["w", "a", "s", "d", "up", "down", "left", "right"], allowed_states=["grid_map"], help_key="grid_move"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        run = router.save_manager.load_save(user_id)
        if not run:
            yield get_locale_text("i18n_cli_general_b.err_no_active_game")
            return
        yield router.engine.map_engine.move(run, parts[0].lower())


class GridTeleportCommand(CommandHandler, names=["传送", "tp", "teleport"], allowed_states=["grid_map"], help_key="grid_tp"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        run = router.save_manager.load_save(user_id)
        if not run:
            yield get_locale_text("i18n_cli_general_b.err_no_active_game")
            return
        if len(parts) < 2:
            yield router.engine.map_engine.grid_map_service.list_teleportable_nodes(run)
            return
        target = " ".join(parts[1:]).strip()
        yield router.engine.map_engine.teleport(run, target)


class GridMapViewCommand(CommandHandler, names=["地图", "map", "look", "l"], allowed_states=["grid_map"], help_key="grid_map"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        run = router.save_manager.load_save(user_id)
        if not run:
            yield get_locale_text("i18n_cli_general_b.err_no_active_game")
            return
        yield GameRenderer.render_game(run)


class GridTalkCommand(CommandHandler, names=["交谈", "talk", "talk_to", "interact", "inter"], allowed_states=["grid_map"], help_key="grid_talk"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        run = router.save_manager.load_save(user_id)
        if not run:
            yield get_locale_text("i18n_cli_general_b.err_no_active_game")
            return
        if len(parts) > 1:
            query = " ".join(parts[1:]).strip()
            merc_uid, _ = find_mercenary_uid(run, query, user_id)
            if merc_uid:
                res = open_merc_dialog(run, user_id, merc_uid)
                router.save_manager.save_save(user_id, run)
                yield res
                return
        err = open_room_talk(router.save_manager, run, user_id)
        if err:
            if len(parts) == 1:
                merc_uid, _ = find_mercenary_uid(run, "", user_id)
                if merc_uid:
                    res = open_merc_dialog(run, user_id, merc_uid)
                    router.save_manager.save_save(user_id, run)
                    yield res
                    return
            yield err
            return
        yield GameRenderer.render_game(run)
