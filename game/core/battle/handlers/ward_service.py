import random
from ....models.events import DamageRedirectEvent
from ....data.text.locale_data import get_locale_text
from ..event_bus import PRIORITY_SYSTEM_PRE


def pick_ward_minion(player):
    """返回拥有守护 Buff 的随机随从格位。"""
    if player is None:
        return None
    grids = [
        grid
        for grid, minion in player.minions.items()
        if any(buff.id == "ward" for buff in minion.buffs)
    ]
    if not grids:
        return None
    return random.choice(grids)


class WardRedirectHandler:
    """在单体敌方攻击指向玩家时把目标重定向到守护随从。"""

    def __init__(self, event_bus, engine):
        self.engine = engine
        event_bus.subscribe(DamageRedirectEvent, self.on_damage_redirect, PRIORITY_SYSTEM_PRE)

    def on_damage_redirect(self, event):
        if event.redirected or not event.is_single_target:
            return
        if event.target != "p0" or not event.source.startswith("enemy:"):
            return
        grid = pick_ward_minion(event.run.player)
        if grid is None:
            return
        minion = event.run.player.minions[grid]
        event.target = f"p{grid}"
        event.redirected = True
        self.engine._log_event(
            event.run,
            get_locale_text(
                "i18n_entity_wiring.enemy_base.ward_redirect",
                name=event.source[6:],
                m_name=minion.name,
            ),
        )
