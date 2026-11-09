from typing import Optional
from ...models.state import Card
from ...data.locale_data import get_locale_text
from .registry import register_card

@register_card("curse_dazed")
@register_card("curse_agony")
@register_card("curse_dimensional_tear")
@register_card("curse_wound")
class CurseCard(Card):
    def execute(self, run, target, engine) -> str:
        return get_locale_text("i18n_cards_misc.curse.cannot_play")

@register_card("curse_indigestion")
class IndigestionCurse(Card):
    def execute(self, run, target, engine) -> str:
        p = run.player
        p.bonus_actions = max(0, p.bonus_actions - 1)
        return get_locale_text("i18n_cards_misc.curse.indigestion_log")

@register_card("curse_mana_backflow")
class ManaBackflowCurse(Card):
    def execute(self, run, target, engine) -> str:
        p = run.player
        loss = min(8, p.hp - 1) if p.hp > 1 else 0
        if loss > 0:
            engine._damage_target(run, "p0", loss, source="self", damage_type="true")
        return get_locale_text("i18n_cards_misc.curse.mana_backflow_log")

@register_card("curse_intangible_whisper")
class IntangibleWhisperCurse(Card):
    def execute(self, run, target, engine) -> str:
        run.node_data["draw_penalty_next_turn"] = run.node_data.get("draw_penalty_next_turn", 0) + 3
        return get_locale_text("i18n_cards_misc.curse.intangible_whisper_log")

