from typing import Generator
from ...base import CommandHandler
from .....data.locale_data import get_locale_text
from .....renderer import GameRenderer
from ....inventory.bag_service import drop_bag_item, use_bag_item
from ....world.landmark_system import open_room_talk
from ....party.mercenary import find_mercenary_uid, open_merc_dialog
from ....world.rooms.npc_dialog import attack_in_room, talk_room_npc
from ....world.rooms.interact import take_in_room, touch_in_room


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


class GridMapViewCommand(CommandHandler, names=["地图", "map", "look", "l", "看", "查看"], allowed_states=["grid_map"], help_key="grid_map"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        run = router.save_manager.load_save(user_id)
        if not run:
            yield get_locale_text("i18n_cli_general_b.err_no_active_game")
            return
        yield GameRenderer.render_game(run)


class GridTalkCommand(CommandHandler, names=["对话", "交谈", "talk", "talk_to", "interact", "inter"], allowed_states=["grid_map"], help_key="grid_talk"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        run = router.save_manager.load_save(user_id)
        if not run:
            yield get_locale_text("i18n_cli_general_b.err_no_active_game")
            return
        query = " ".join(parts[1:]).strip() if len(parts) > 1 else ""
        if query:
            merc_uid, _ = find_mercenary_uid(run, query, user_id)
            if merc_uid:
                res = open_merc_dialog(run, user_id, merc_uid)
                router.save_manager.save_save(user_id, run)
                yield res
                return
            npc_res = talk_room_npc(router.save_manager, run, query)
            if npc_res:
                yield npc_res
                return
            yield get_locale_text("i18n_room_interact.dialog.talk_not_found", target=query)
            return
        err = open_room_talk(router.save_manager, run, user_id)
        if not err:
            yield GameRenderer.render_game(run)
            return
        npc_res = talk_room_npc(router.save_manager, run, "")
        if npc_res:
            yield npc_res
            return
        merc_uid, _ = find_mercenary_uid(run, "", user_id)
        if merc_uid:
            res = open_merc_dialog(run, user_id, merc_uid)
            router.save_manager.save_save(user_id, run)
            yield res
            return
        yield err


class GridAttackCommand(CommandHandler, names=["攻击", "attack", "atk", "打"], allowed_states=["grid_map", "explore", "cafe"], help_key="grid_attack"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        run = router.save_manager.load_save(user_id)
        if not run:
            yield get_locale_text("i18n_cli_general_b.err_no_active_game")
            return
        query = " ".join(parts[1:]).strip() if len(parts) > 1 else ""
        yield attack_in_room(router.engine.map_engine, run, query)


class GridTouchCommand(CommandHandler, names=["触摸", "touch", "摸", "调查", "inspect"], allowed_states=["grid_map", "explore", "cafe"], help_key="grid_touch"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        run = router.save_manager.load_save(user_id)
        if not run:
            yield get_locale_text("i18n_cli_general_b.err_no_active_game")
            return
        query = " ".join(parts[1:]).strip() if len(parts) > 1 else ""
        yield touch_in_room(router.save_manager, run, query)


class GridTakeCommand(CommandHandler, names=["拿取", "捡起", "take", "pick"], allowed_states=["grid_map", "explore", "cafe"], help_key="grid_take"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        run = router.save_manager.load_save(user_id)
        if not run:
            yield get_locale_text("i18n_cli_general_b.err_no_active_game")
            return
        query = " ".join(parts[1:]).strip() if len(parts) > 1 else ""
        yield take_in_room(router.save_manager, run, query)


class GridUseCommand(CommandHandler, names=["使用", "use"], allowed_states=["grid_map", "explore", "cafe"], help_key="grid_use"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        run = router.save_manager.load_save(user_id)
        if not run:
            yield get_locale_text("i18n_cli_general_b.err_no_active_game")
            return
        query = " ".join(parts[1:]).strip() if len(parts) > 1 else ""
        msg = use_bag_item(router.engine, run, query)
        router.save_manager.save_save(user_id, run)
        yield msg


class DropItemCommand(CommandHandler, names=["丢弃物品", "扔掉", "drop_item"], allowed_states=["grid_map", "explore", "cafe"], help_key="drop_item"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        run = router.save_manager.load_save(user_id)
        if not run:
            yield get_locale_text("i18n_cli_general_b.err_no_active_game")
            return
        query = " ".join(parts[1:]).strip() if len(parts) > 1 else ""
        msg = drop_bag_item(run, query)
        router.save_manager.save_save(user_id, run)
        yield msg
