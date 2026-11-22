from typing import Generator
from ...base import CommandHandler
from .....data.text.locale_data import get_locale_text
from .....renderer import GameRenderer
from ....inventory.bag_service import drop_bag_item, use_bag_item
from ....world.landmark_system import open_room_talk
from ....world.persistent_buffs import break_map_invisibility
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


class GridDigCommand(CommandHandler, names=["破障", "挖掘", "dig", "dg"], allowed_states=["grid_map"], help_key="grid_dig"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        run = router.save_manager.load_save(user_id)
        if not run:
            yield get_locale_text("i18n_cli_general_b.err_no_active_game")
            return
        if len(parts) < 2:
            yield get_locale_text("i18n_grid_map.err_invalid_direction")
            return
        yield router.engine.map_engine.dig(run, parts[1].lower())


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


class GridMapViewCommand(CommandHandler, names=["地图", "map", "m", "look", "l", "看", "查看"], allowed_states=["grid_map"], help_key="grid_map"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        run = router.save_manager.load_save(user_id)
        if not run:
            yield get_locale_text("i18n_cli_general_b.err_no_active_game")
            return
        yield GameRenderer.render_game(run)


class GridTalkCommand(CommandHandler, names=["talk", "talk_to", "interact", "inter", "对话", "交谈"], allowed_states=["grid_map"], help_key="grid_talk"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        run = router.save_manager.load_save(user_id)
        if not run:
            yield get_locale_text("i18n_cli_general_b.err_no_active_game")
            return
        query = " ".join(parts[1:]).strip() if len(parts) > 1 else ""
        if query == ".":
            query = ""
        if query:
            from ....prism.card_talk import strip_card_talk_prefix, try_card_talk
            _, has_card_prefix = strip_card_talk_prefix(query)
            if has_card_prefix:
                card_res = try_card_talk(router.save_manager, router.engine, user_id, query, run=run, explicit=True)
                if card_res is not None:
                    yield card_res
                    return
            player_res = router.world_social.try_talk(user_id, query, run=run)
            if player_res is not None:
                yield player_res
                return
            merc_uid, _ = find_mercenary_uid(run, query, user_id)
            if merc_uid:
                broken_msg = break_map_invisibility(run, reason="interact")
                res = open_merc_dialog(run, user_id, merc_uid)
                router.save_manager.save_save(user_id, run)
                yield f"{broken_msg}\n\n{res}" if broken_msg else res
                return
            npc_res = talk_room_npc(router.save_manager, run, query)
            if npc_res:
                yield npc_res
                return
            card_res = try_card_talk(router.save_manager, router.engine, user_id, query, run=run, explicit=False)
            if card_res is not None:
                yield card_res
                return
            yield get_locale_text("i18n_room_interact.dialog.talk_not_found", target=query)
            return
        err = open_room_talk(router.save_manager, run, user_id)
        if not err:
            broken_msg = break_map_invisibility(run, reason="interact")
            if broken_msg:
                router.save_manager.save_save(user_id, run)
            rendered = GameRenderer.render_game(run)
            yield f"{broken_msg}\n\n{rendered}" if broken_msg else rendered
            return
        npc_res = talk_room_npc(router.save_manager, run, "")
        if npc_res:
            yield npc_res
            return
        merc_uid, _ = find_mercenary_uid(run, "", user_id)
        if merc_uid:
            broken_msg = break_map_invisibility(run, reason="interact")
            res = open_merc_dialog(run, user_id, merc_uid)
            router.save_manager.save_save(user_id, run)
            yield f"{broken_msg}\n\n{res}" if broken_msg else res
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


class GridTouchCommand(CommandHandler, names=["touch", "tch", "摸", "触摸", "调查", "inspect", "打开", "open"], allowed_states=["grid_map", "explore", "cafe", "battle"], help_key="grid_touch"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        run = router.save_manager.load_save(user_id)
        if not run:
            yield get_locale_text("i18n_cli_general_b.err_no_active_game")
            return
        query = " ".join(parts[1:]).strip() if len(parts) > 1 else ""
        if run.node_type == "battle":
            if not query:
                yield get_locale_text("i18n_trade.status_need_target")
                return
            from ....social.player_inspect import touch_player_status
            status = touch_player_status(router.save_manager, user_id, query, run=run)
            if status is not None:
                yield status
                return
            yield get_locale_text("i18n_trade.err_target_not_here", query=query)
            return
        yield touch_in_room(router.save_manager, run, query, map_engine=router.engine.map_engine)


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


class BattleBagUseCommand(CommandHandler, names=["use"], allowed_states=["battle"], help_key="grid_use"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        from .....renderer import GameRenderer

        run = router.save_manager.load_save(user_id)
        if not run:
            yield get_locale_text("i18n_cli_general_b.err_no_active_game")
            return
        query = " ".join(parts[1:]).strip() if len(parts) > 1 else ""
        msg = use_bag_item(router.engine, run, query)
        if run.node_type == "battle":
            msg = router.engine.battle_engine._append_logs_to_res(run, msg)
        router.save_manager.save_save(user_id, run)
        yield msg + "\n" + GameRenderer.render_game(run)


class DropItemCommand(CommandHandler, names=["丢弃物品", "扔掉", "drop_item", "di"], allowed_states=["grid_map", "explore", "cafe", "town", "outer_plane"], help_key="drop_item"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        query = " ".join(parts[1:]).strip() if len(parts) > 1 else ""
        run = router.save_manager.load_save(user_id)
        if run:
            msg = drop_bag_item(run, query)
            router.save_manager.save_save(user_id, run)
            yield msg
            return
        stats = router.save_manager.load_stats(user_id)
        from ....world.open_world.loadout_service import OpenWorldLoadoutService
        msg = OpenWorldLoadoutService.drop_bag_item_from_stats(stats, query)
        router.save_manager.save_stats(user_id, stats)
        yield msg
