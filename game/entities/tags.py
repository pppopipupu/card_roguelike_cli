import copy
from typing import Optional
from ..models.state import CardTag, Card, GameRun
from ..models.events import CardPlayedEvent, CardExhaustEvent, CardExtraTriggerEvent
from ..data.text.locale_data import get_locale_text

class ReplayTag(CardTag):
    def execute(self, card: Card, run: GameRun, target: Optional[str], engine) -> Optional[str]:
        if self.value > 0:
            from ..core.battle.card_executor import execute_extra_card_effect
            for _ in range(self.value):
                if engine.is_battle_won(run):
                    break
                execute_extra_card_effect(
                    engine,
                    run,
                    card,
                    target,
                    trigger_type="replay",
                    msg_key="i18n_buffs.replay_trigger_msg",
                )
        return None

class FragileTag(CardTag):
    def handle_post_play(self, card: Card, run: GameRun, cid: str, source: str, engine) -> bool:
        p = run.player
        from ..models.state import ensure_card_state
        card_state = ensure_card_state(cid)
        curr_fragile = card_state.fragile
        if curr_fragile <= 0:
            curr_fragile = self.value

        match_state = copy.copy(card_state)
        match_state.replay = 0
        match_state.fragile = 0

        found = None
        for dc in p.deck:
            if (dc.id == match_state.id and
                dc.upgraded == match_state.upgraded and
                dc.gems == match_state.gems and
                dc.fleeting_used == match_state.fleeting_used):
                found = dc
                break
        if not found:
            for dc in p.deck:
                if (dc.id == match_state.id and
                    dc.upgraded == match_state.upgraded and
                    dc.gems == match_state.gems):
                    found = dc
                    break

        if curr_fragile <= getattr(self, "break_threshold", 1):
            if found:
                p.deck.remove(found)
            engine._log_event(run, get_locale_text("i18n_buffs.fragile_break_log", card=card.name))
        else:
            next_fragile = curr_fragile - getattr(self, "break_step", 1)
            next_cid = copy.copy(card_state)
            next_cid.fragile = next_fragile

            from ..entities.cards import ALL_CARDS
            removed_by_fleeting = False
            if getattr(card, "fleeting", False):
                fleeting_total = int(getattr(card, "fleeting_total", 1) or 1)
                next_fleeting_used = int(getattr(next_cid, "fleeting_used", 0) or 0) + 1
                if next_fleeting_used >= fleeting_total:
                    if found:
                        p.deck.remove(found)
                    engine._log_event(run, get_locale_text("i18n_battle_core.fleeting_remove_log", card=card.name, name=card.name))
                    removed_by_fleeting = True
                else:
                    next_cid.fleeting_used = next_fleeting_used
                    if found:
                        found.fleeting_used = next_fleeting_used
                    remaining = fleeting_total - next_fleeting_used
                    engine._log_event(run, get_locale_text("i18n_battle_core.fleeting_wear_log", name=card.name, remaining=remaining))
            if not removed_by_fleeting:
                if any(b.id == "void_exhaustion" for b in p.buffs):
                    p.exhaust_pile.append(next_cid)
                    engine._log_event(run, get_locale_text("i18n_buffs.void_exhaustion_move_log", card=card.name))
                    exhaust_evt = CardExhaustEvent(run, next_cid, "played")
                    engine.event_bus.dispatch(exhaust_evt)
                elif getattr(card, "exhaust", False):
                    exhaust_total = int(getattr(card, "exhaust_total", 1) or 1)
                    next_exhaust_used = int(getattr(next_cid, "exhaust_used", 0) or 0) + 1
                    next_cid.exhaust_used = next_exhaust_used
                    if next_exhaust_used >= exhaust_total:
                        p.exhaust_pile.append(next_cid)
                        engine._log_event(run, get_locale_text("i18n_battle_core.exhaust_card_log", name=card.name))
                        exhaust_evt = CardExhaustEvent(run, next_cid, "played")
                        engine.event_bus.dispatch(exhaust_evt)
                    else:
                        p.discard_pile.append(next_cid)
                        remaining = exhaust_total - next_exhaust_used
                        engine._log_event(run, get_locale_text("i18n_battle_core.exhaust_wear_log", name=card.name, remaining=remaining))
                else:
                    p.discard_pile.append(next_cid)
                    next_card = ALL_CARDS.get(next_cid)
                    next_name = next_card.name if next_card else card.name
                    engine._log_event(run, get_locale_text("i18n_buffs.fragile_wear_log", card=card.name, next=next_name))
        return True


class BladeTag(CardTag):
    def __init__(self, name: str = "blade", value: int = 1):
        super().__init__(name, value)


class HandTag(CardTag):
    def __init__(self, name: str = "hand", value: int = 1):
        super().__init__(name, value)


class LyricsTag(CardTag):
    def __init__(self, name: str = "lyrics", value: int = 1):
        super().__init__(name, value)


class SentientTag(CardTag):
    def __init__(self, name: str = "sentient", value: int = 1):
        super().__init__(name, value)
