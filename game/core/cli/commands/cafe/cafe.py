from typing import Generator
from ...base import CommandHandler
from .....data.locale_data import get_locale_text

class CafeLookCommand(CommandHandler, names=["look", "look_around", "看", "查"], allowed_states=["cafe"], help_key="cafe_look"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        run = router.save_manager.load_save(user_id)
        if not run:
            return
        from ....world.cafe.engine import CafeEngine
        cafe = CafeEngine(router.save_manager, router.engine.map_engine)
        yield cafe.render_cafe(run)

class CafeTalkCommand(CommandHandler, names=["对话", "交谈", "talk", "talk_to", "interact", "inter"], allowed_states=["cafe"], help_key="cafe_talk"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        run = router.save_manager.load_save(user_id)
        if not run:
            return
        if len(parts) < 2:
            yield get_locale_text("i18n_cli_commands.cafe_talk_missing_target")
            return
        target = " ".join(parts[1:])
        from ....prism.card_talk import strip_card_talk_prefix, try_card_talk
        _, has_card_prefix = strip_card_talk_prefix(target)
        if has_card_prefix:
            card_res = try_card_talk(router.save_manager, router.engine, user_id, target, run=run, explicit=True)
            if card_res is not None:
                yield card_res
                return
        player_res = router.world_social.try_talk(user_id, target, run=run)
        if player_res is not None:
            yield player_res
            return
        from ....party.mercenary import find_mercenary_uid, open_merc_dialog
        from ....world.cafe.engine import CafeEngine
        cafe = CafeEngine(router.save_manager, router.engine.map_engine)
        merc_uid, _ = find_mercenary_uid(run, target, user_id)
        if merc_uid and not cafe._find_npc(run, target):
            res = open_merc_dialog(run, user_id, merc_uid)
            router.save_manager.save_save(user_id, run)
            yield res
            return
        if not cafe._find_npc(run, target):
            card_res = try_card_talk(router.save_manager, router.engine, user_id, target, run=run, explicit=False)
            if card_res is not None:
                yield card_res
                return
        yield cafe.talk_npc(run, target)

class CafeLeaveCommand(CommandHandler, names=["离开", "leave", "exit", "quit"], allowed_states=["cafe"], help_key="cafe_leave"):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        run = router.save_manager.load_save(user_id)
        if not run:
            return
        from ....world.cafe.engine import CafeEngine
        cafe = CafeEngine(router.save_manager, router.engine.map_engine)
        cafe_data = run.node_data.get("cafe_data", {})
        if cafe_data.get("active_npc") is not None:
            yield cafe.leave_npc(run)
        else:
            yield cafe.leave_cafe(run)
