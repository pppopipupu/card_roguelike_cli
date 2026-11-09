from typing import Optional

from ..data.locale_data import get_locale_text

class Effect:
    def apply(self, run, source: str, target: str, engine) -> str:
        return ""

class DamageEffect(Effect):
    def __init__(self, amount: int):
        self.amount = amount

    def apply(self, run, source: str, target: str, engine) -> str:
        name = engine._get_target_name(run, target)
        engine._damage_target(run, target, self.amount)
        return get_locale_text("i18n_buffs.effect_damage", name=name, amount=self.amount)

class HealEffect(Effect):
    def __init__(self, amount: int):
        self.amount = amount

    def apply(self, run, source: str, target: str, engine) -> str:
        name = engine._get_target_name(run, target)
        engine._heal_target(run, target, self.amount)
        return get_locale_text("i18n_buffs.effect_heal", name=name, amount=self.amount)

class ShieldEffect(Effect):
    def __init__(self, amount: int):
        self.amount = amount

    def apply(self, run, source: str, target: str, engine) -> str:
        name = engine._get_target_name(run, target)
        engine._gain_shield(run, target, self.amount)
        return get_locale_text("i18n_buffs.effect_shield", name=name, amount=self.amount)

class DrawCardEffect(Effect):
    def __init__(self, count: int):
        self.count = count

    def apply(self, run, source: str, target: str, engine) -> str:
        engine._draw_cards(run.player, self.count, run)
        return get_locale_text("i18n_buffs.effect_draw", count=self.count)

class ModifyActionEffect(Effect):
    def __init__(self, count: int, action_type: str = "A"):
        self.count = count
        self.action_type = action_type

    def apply(self, run, source: str, target: str, engine) -> str:
        p = run.player
        if self.action_type == "A":
            p.actions += self.count
            return get_locale_text("i18n_buffs.effect_gain_a", count=self.count)
        else:
            p.bonus_actions += self.count
            return get_locale_text("i18n_buffs.effect_gain_ba", count=self.count)
