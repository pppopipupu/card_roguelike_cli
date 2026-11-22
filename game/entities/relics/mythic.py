from ...data.entities.relic_data import RELIC_CONFIG
from ...data.text.locale_data import get_locale_text
from .base import RelicImpl
from .registry import register_relic

@register_relic("infinite_hourglass")
class InfiniteHourglassRelic(RelicImpl):
    def __init__(self, relic_id: str):
        super().__init__(relic_id)
        cfg = RELIC_CONFIG.get(relic_id, {})
        self.extra_turns = cfg.get("extra_turns", 1)
        self.bonus_actions = cfg.get("bonus_actions", 1)

    def on_battle_start(self, run, engine):
        from ...core.battle.extra_turn_service import MODE_TIME_STOP, grant_extra_turn
        uid = run.uid_for(run.player) or run.user_id
        grant_extra_turn(run, uid, MODE_TIME_STOP, self.extra_turns, break_on_damage=True, source=self.relic_id)
        engine._log_event(run, get_locale_text("i18n_relics_amulets.mythic.infinite_hourglass.battle_start"))

    def on_turn_start(self, event, run, engine):
        p = run.player
        p.bonus_actions += self.bonus_actions
        engine._log_event(run, get_locale_text("i18n_relics_amulets.mythic.infinite_hourglass.turn_start"))

@register_relic("trash_mountain")
class TrashMountainRelic(RelicImpl):
    def on_reward_generate(self, event, run, engine):
        for item in event.items:
            if item.get("type") == "card_reward":
                item["force"] = True

    def on_card_select_init(self, event, run, engine):
        event.can_skip = False
        event.upgraded = True

    def on_card_obtain(self, event, run, engine):
        event.card_state.upgraded = True
