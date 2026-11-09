import random
from .base import EventOption
from ...data.event_data import EVENT_CONFIG, EVENT_MIN_MAX_HP
from ...data.relic_data import RELIC_CONFIG
from ..relics import get_relic_name
from ...data.locale_data import get_locale_text

class MazeFireOption(EventOption, action="maze_fire", text=get_locale_text("i18n_events_b.option_maze_fire")):
    def _run_effect(self, run, engine) -> str:
        cfg = EVENT_CONFIG["maze_guard"]
        run.node_data["event_id"] = "maze_guard"
        run.node_data["description"] = cfg["description"]
        run.node_data["options"] = [{"text": o["text"], "action": o["action"]} for o in cfg["options"]]
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_events_b.msg_maze_fire")

class MazeWaterOption(EventOption, action="maze_water", text=get_locale_text("i18n_events_b.option_maze_water")):
    def _run_effect(self, run, engine) -> str:
        cfg = EVENT_CONFIG["maze_pool"]
        run.node_data["event_id"] = "maze_pool"
        run.node_data["description"] = cfg["description"]
        run.node_data["options"] = [{"text": o["text"], "action": o["action"]} for o in cfg["options"]]
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_events_b.msg_maze_water")

class MazeMarkOption(EventOption, action="maze_mark", text=get_locale_text("i18n_events_b.option_maze_mark")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        cfg = EVENT_CONFIG.get("lost_maze", {})
        p.gold += cfg.get("mark_gold", 10)
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_events_b.msg_maze_mark")

class BribeGuardOption(EventOption, action="bribe_guard", text=get_locale_text("i18n_events_b.option_bribe_guard")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        cfg = EVENT_CONFIG.get("maze_guard", {})
        bribe_gold = cfg.get("bribe_gold", 20)
        if p.gold < bribe_gold:
            return get_locale_text("i18n_events_b.err_bribe_gold_not_enough")
        p.gold -= bribe_gold
        relics_pool = ["lucky_coin", "red_bottle", "leather_armor", "whetstone", "ready_pack", "arcane_rune"]
        available_relics = [r for r in relics_pool if r not in p.relics]
        got_relic = ""
        if available_relics:
            got_relic = random.choice(available_relics)
            p.relics.append(got_relic)
            if got_relic == "red_bottle":
                red_bottle_cfg = RELIC_CONFIG.get("red_bottle", {})
                p.max_hp += red_bottle_cfg.get("max_hp_gain", 5)
                p.hp += red_bottle_cfg.get("heal_amount", 5)
        relic_msg = get_locale_text("i18n_events_b.msg_bribe_relic_suffix", relic_name=get_relic_name(got_relic)) if got_relic else ""
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_events_b.msg_bribe_guard", relic_msg=relic_msg)

class FightGuardOption(EventOption, action="fight_guard", text=get_locale_text("i18n_events_b.option_fight_guard")):
    def _run_effect(self, run, engine) -> str:
        run.node_data["quest"] = "maze_fight"
        engine.battle_engine._init_battle_node(run, "elite")
        run.node_type = "battle"
        if run.enemies:
            cfg = EVENT_CONFIG.get("maze_guard", {})
            guard_hp = cfg.get("guard_hp_base", 30) + run.player.stage * cfg.get("guard_hp_per_stage", 2)
            run.enemies[0].name = get_locale_text("i18n_events_b.enemy_fire_guardian")
            run.enemies[0].hp = guard_hp
            run.enemies[0].max_hp = run.enemies[0].hp
        engine.save_manager.save_save(run.user_id, run)
        return engine.battle_engine._append_logs_to_res(run, get_locale_text("i18n_events_b.msg_fight_guard"))

class BathePoolOption(EventOption, action="bathe_pool", text=get_locale_text("i18n_events_b.option_bathe_pool")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        cfg = EVENT_CONFIG.get("maze_pool", {})
        p.max_hp += cfg.get("max_hp_gain", 3)
        if "wither_seed" not in p.relics:
            p.hp = min(p.max_hp, p.hp + cfg.get("heal", 15))
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_events_b.msg_bathe_pool")

class FishPoolOption(EventOption, action="fish_pool", text=get_locale_text("i18n_events_b.option_fish_pool")):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        cfg = EVENT_CONFIG.get("maze_pool", {})
        if random.random() < cfg.get("relic_chance", 0.5):
            relics_pool = ["lucky_coin", "red_bottle", "leather_armor", "whetstone", "ready_pack", "arcane_rune"]
            available_relics = [r for r in relics_pool if r not in p.relics]
            got_relic = ""
            if available_relics:
                got_relic = random.choice(available_relics)
                p.relics.append(got_relic)
                if got_relic == "red_bottle":
                    red_bottle_cfg = RELIC_CONFIG.get("red_bottle", {})
                    p.max_hp += red_bottle_cfg.get("max_hp_gain", 5)
                    p.hp += red_bottle_cfg.get("heal_amount", 5)
            res = get_locale_text("i18n_events_b.msg_fish_pool_relic", relic_name=get_relic_name(got_relic)) if got_relic else get_locale_text("i18n_events_b.msg_fish_pool_empty")
        else:
            p.max_hp = max(EVENT_MIN_MAX_HP, p.max_hp - cfg.get("max_hp_loss", 2))
            p.hp = min(p.hp, p.max_hp)
            res = get_locale_text("i18n_events_b.msg_fish_pool_snake")
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return res
