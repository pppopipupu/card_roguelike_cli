from typing import Optional
import re
from ...data.relic_data import RELIC_CONFIG
from .registry import register_relic, RELIC_CLASS_REGISTRY

class RelicImpl:
    def __init__(self, relic_id: str):
        self.relic_id = relic_id
        self.name = RELIC_CONFIG.get(relic_id, {}).get("name", relic_id)
        self.desc = RELIC_CONFIG.get(relic_id, {}).get("desc", "")
        self.rarity = RELIC_CONFIG.get(relic_id, {}).get("rarity", "common")

    def on_battle_start(self, run, engine):
        pass

    def on_turn_start(self, event, run, engine):
        pass

    def on_turn_end(self, event, run, engine):
        pass

    def on_card_play(self, event, run, engine):
        pass

    def on_card_played(self, event, run, engine):
        pass

    def on_damage_calculate(self, event, run, engine):
        pass

    def on_damage_calculate_defend(self, event, run, engine):
        pass

    def on_damage_take(self, event, run, engine):
        pass

    def on_damage_take_defend(self, event, run, engine):
        pass
    def on_before_damage_apply(self, event, run, engine):
        pass


    def on_shield_gain(self, event, run, engine):
        pass

    def on_shield_decay(self, event, run, engine):
        pass

    def on_heal(self, event, run, engine):
        pass

    def on_heal_calculate(self, event, run, engine):
        pass

    def on_node_enter(self, run, engine):
        pass

    def modify_initial_draw(self, run, draw_count: int, engine) -> int:
        return draw_count


def get_relic_impl(relic_id: str) -> Optional[RelicImpl]:
    cls = RELIC_CLASS_REGISTRY.get(relic_id)
    if cls:
        return cls(relic_id)
    return None

def get_relic_name(relic_id: str) -> str:
    return RELIC_CONFIG.get(relic_id, {}).get("name", relic_id)

def get_relic_desc(relic_id: str) -> str:
    return RELIC_CONFIG.get(relic_id, {}).get("desc", "")

def get_relic_rarity(relic_id: str) -> str:
    return RELIC_CONFIG.get(relic_id, {}).get("rarity", "common")

ALL_RELIC_IDS = list(RELIC_CONFIG.keys())
