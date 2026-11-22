import random

from ....data.battle.class_battle_config import CLASS_BATTLE_INIT, CLASS_TURN_START_FLAGS
from ....data.entities.buffs.buff_data import BUFF_CONFIG
from ....data.progression.balance_config import (
    CLASS_TURN_RESOURCES,
    SUBCLASS_TIME_SHIFT_BONUS_ACTIONS,
    SUBCLASS_TIME_SHIFT_CHANCE,
)
from ....data.text.locale_data import get_locale_text
from ....models.events import BattleStartEvent, TurnResourceInitEvent, TurnStartEvent


class ClassPassiveHandler:
    """职业与子职业被动入口，接管回合资源与被动触发。"""

    def __init__(self, event_bus, engine):
        self.engine = engine
        event_bus.subscribe(BattleStartEvent, self.on_battle_start)
        event_bus.subscribe(TurnResourceInitEvent, self.on_turn_resource_init)
        event_bus.subscribe(TurnStartEvent, self.on_turn_start)

    def _apply_battle_init(self, event, key: str):
        cfg = CLASS_BATTLE_INIT.get(key, {})
        player = event.run.player
        for flag, value in cfg.get("flags", {}).items():
            event.run.node_data[event.run.turn_key(flag, player)] = value
        for buff_id in cfg.get("buffs", ()):
            buff_cfg = BUFF_CONFIG.get(buff_id, {})
            self.engine._add_buff_to(
                player,
                buff_id,
                buff_cfg.get("name", buff_id),
                buff_cfg.get("desc", ""),
            )

    def on_battle_start(self, event):
        player = event.run.player
        if player is None:
            return
        self._apply_battle_init(event, str(getattr(player, "selected_class", "") or ""))
        self._apply_battle_init(event, str(getattr(player, "subclass", "") or ""))
        if str(getattr(player, "subclass", "") or "") != "时序法师":
            return
        if random.random() >= SUBCLASS_TIME_SHIFT_CHANCE:
            return
        player.bonus_actions += SUBCLASS_TIME_SHIFT_BONUS_ACTIONS
        self.engine._log_event(event.run, get_locale_text("i18n_battle_core.time_shift_initial_log"))

    def on_turn_resource_init(self, event):
        selected_class = str(getattr(event.player, "selected_class", "") or "")
        cfg = CLASS_TURN_RESOURCES.get(selected_class)
        if not cfg:
            return
        actions = cfg.get("actions", 0) or 0
        bonus_actions = cfg.get("bonus_actions", 0) or 0
        event.actions = int(actions)
        event.bonus_actions = int(bonus_actions)

    def on_turn_start(self, event):
        if not event.is_player:
            return
        player = event.run.player
        for key in (str(getattr(player, "selected_class", "") or ""), str(getattr(player, "subclass", "") or "")):
            for flag, value in CLASS_TURN_START_FLAGS.get(key, {}).items():
                event.run.node_data[event.run.turn_key(flag, player)] = value
        if str(getattr(player, "subclass", "") or "") != "时序法师":
            return
        if random.random() >= SUBCLASS_TIME_SHIFT_CHANCE:
            return
        player.bonus_actions += SUBCLASS_TIME_SHIFT_BONUS_ACTIONS
        self.engine._log_event(event.run, get_locale_text("i18n_battle_core.time_shift_turn_log"))
