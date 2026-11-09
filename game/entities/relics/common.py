import re
from ...data.relic_data import RELIC_CONFIG
from ...data.locale_data import get_locale_text
from .base import RelicImpl
from .registry import register_relic

class LeatherArmorRelic(RelicImpl):
    def __init__(self, relic_id: str):
        super().__init__(relic_id)
        cfg = RELIC_CONFIG.get(relic_id, {})
        self.shield_gain = cfg.get("shield_gain", 4)

    def on_battle_start(self, run, engine):
        engine._gain_shield(run, "p0", self.shield_gain)
        engine._log_event(run, get_locale_text("i18n_relics_amulets.common.leather_armor.trigger", shield_gain=self.shield_gain))

class AncientSigilRelic(RelicImpl):
    def __init__(self, relic_id: str):
        super().__init__(relic_id)
        cfg = RELIC_CONFIG.get(relic_id, {})
        self.proc_chance = cfg.get("proc_chance", 0.5)
        self.heal_amount = cfg.get("heal_amount", 3)
        self.shield_gain = cfg.get("shield_gain", 5)

    def on_card_played(self, event, run, engine):
        if getattr(event.card, "exhaust", False):
            import random
            if random.random() < self.proc_chance:
                engine._heal_target(run, "p0", self.heal_amount)
                engine._log_event(run, get_locale_text("i18n_relics_amulets.common.ancient_sigil.heal"))
            else:
                engine._gain_shield(run, "p0", self.shield_gain)
                engine._log_event(run, get_locale_text("i18n_relics_amulets.common.ancient_sigil.shield"))


for name, obj in list(globals().items()):
    if isinstance(obj, type) and issubclass(obj, RelicImpl) and obj is not RelicImpl:
        snake = re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()
        if snake.endswith('_relic'):
            relic_id = snake[:-6]
            register_relic(relic_id)(obj)
