from typing import List, Optional
import re
from .registry import register_buff, BUFF_CLASS_REGISTRY

def is_debuff(buff_id: str) -> bool:
    clean_id = buff_id[:-1] if buff_id.endswith("+") else buff_id
    if clean_id.startswith("minor_vulnerable_") or clean_id.startswith("vulnerable_"):
        return True
    from ...data.buff_data import BUFF_CONFIG
    cfg = BUFF_CONFIG.get(clean_id, {})
    return cfg.get("is_debuff", False)

class BuffImpl:
    auto_register = True
    def __init__(self, stacks: int):
        self.stacks = stacks
        self.upgraded = False
        self.stacks2: Optional[int] = None

    def on_card_play(self, event, buff_state, entity):
        pass

    def on_card_played(self, event, buff_state, entity):
        pass

    def on_turn_start(self, event, buff_state, entity):
        pass

    def on_turn_end(self, event, buff_state, entity):
        pass

    def on_damage_calculate(self, event, buff_state, entity):
        pass

    def on_damage_calculate_defend(self, event, buff_state, entity):
        pass

    def on_damage_take_defend(self, event, buff_state, entity, engine):
        pass

    def on_heal(self, event, buff_state, entity):
        pass

    def on_heal_calculate(self, event, buff_state, entity):
        pass

    def on_shield_gain(self, event, buff_state, entity):
        pass

    def on_enemy_sync_intents(self, event, buff_state, entity):
        pass

    def on_damage_take_attack(self, event, buff_state, entity, engine):
        pass

    def on_card_exhaust(self, event, buff_state, entity):
        pass
def get_buff_impl(buff_id: str, stacks: int, stacks2: Optional[int] = None) -> Optional[BuffImpl]:
    upgraded = False
    if isinstance(buff_id, str) and buff_id.endswith("+"):
        upgraded = True
        buff_id = buff_id[:-1]
    if buff_id.startswith("minor_vulnerable_"):
        from .debuffs import MinorVulnerableBuff
        dtype = buff_id[len("minor_vulnerable_"):]
        inst = MinorVulnerableBuff(stacks, dtype)
        inst.stacks2 = stacks2
        inst.upgraded = upgraded
        return inst
    elif buff_id.startswith("vulnerable_"):
        from .debuffs import VulnerableBuff
        dtype = buff_id[len("vulnerable_"):]
        inst = VulnerableBuff(stacks, dtype)
        inst.stacks2 = stacks2
        inst.upgraded = upgraded
        return inst
    elif buff_id.startswith("resist_"):
        from .buffs import ResistBuff
        dtype = buff_id[len("resist_"):]
        inst = ResistBuff(stacks, dtype)
        inst.stacks2 = stacks2
        inst.upgraded = upgraded
        return inst
    elif buff_id.startswith("immune_"):
        from .buffs import ImmuneBuff
        dtype = buff_id[len("immune_"):]
        inst = ImmuneBuff(stacks, dtype)
        inst.stacks2 = stacks2
        inst.upgraded = upgraded
        return inst
    cls = BUFF_CLASS_REGISTRY.get(buff_id)
    if not cls and isinstance(buff_id, str) and buff_id.endswith("_buff"):
        cls = BUFF_CLASS_REGISTRY.get(buff_id[:-5])
    if cls:
        inst = cls(stacks)
        inst.stacks2 = stacks2
        inst.upgraded = upgraded
        return inst
    return None
