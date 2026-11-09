from ...data.relic_data import RELIC_CONFIG
from ...data.locale_data import get_locale_text
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
        run.node_data["extra_turns_left"] = self.extra_turns
        run.node_data["time_stop_upgraded"] = False
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
