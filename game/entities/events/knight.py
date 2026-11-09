from .base import EventOption
from ...data.event_data import EVENT_CONFIG
from ...core.deck_service import DeckService
from ...data.locale_data import get_locale_text

class HelpKnightOption(EventOption, action="help_knight", text=get_locale_text("i18n_events_b.option_help_knight")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        has_aid = False
        for idx, cid in enumerate(p.deck):
            if cid == "first_aid":
                p.deck.pop(idx)
                has_aid = True
                break
        if not has_aid:
            return get_locale_text("i18n_events_b.err_no_first_aid")
        DeckService.add_card_to_deck(p, "shield_guard")
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_events_b.msg_help_knight")

class RobKnightOption(EventOption, action="rob_knight", text=get_locale_text("i18n_events_b.option_rob_knight")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        cfg = EVENT_CONFIG.get("knight", {})
        p.gold += cfg.get("rob_gold", 25)
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_events_b.msg_rob_knight")

class AskKnightOption(EventOption, action="ask_knight", text=get_locale_text("i18n_events_b.option_ask_knight")):
    def _run_effect(self, run, engine) -> str:
        cfg = EVENT_CONFIG["knight_story"]
        run.node_data["event_id"] = "knight_story"
        run.node_data["description"] = cfg["description"]
        run.node_data["options"] = [{"text": o["text"], "action": o["action"]} for o in cfg["options"]]
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_events_b.msg_ask_knight")

class CaveQuestOption(EventOption, action="cave_quest", text=get_locale_text("i18n_events_b.option_cave_quest")):
    def _run_effect(self, run, engine) -> str:
        cfg = EVENT_CONFIG["knight_cave"]
        run.node_data["event_id"] = "knight_cave"
        run.node_data["description"] = cfg["description"]
        run.node_data["options"] = [{"text": o["text"], "action": o["action"]} for o in cfg["options"]]
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_events_b.msg_cave_quest")

class CaveFightOption(EventOption, action="cave_fight", text=get_locale_text("i18n_events_b.option_cave_fight")):
    def _run_effect(self, run, engine) -> str:
        run.node_data["quest"] = "knight_cave"
        engine.battle_engine._init_battle_node(run, "normal")
        run.node_type = "battle"
        if run.enemies:
            cfg = EVENT_CONFIG.get("knight_cave", {})
            enemy_hp = cfg.get("enemy_hp", 15)
            run.enemies[0].name = get_locale_text("i18n_events_b.enemy_magic_servant")
            run.enemies[0].hp = enemy_hp
            run.enemies[0].max_hp = enemy_hp
        engine.save_manager.save_save(run.user_id, run)
        return engine.battle_engine._append_logs_to_res(run, get_locale_text("i18n_events_b.msg_cave_fight"))
