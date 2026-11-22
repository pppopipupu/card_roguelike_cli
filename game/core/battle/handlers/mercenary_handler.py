from ....models.events import DamageRedirectEvent
from ..event_bus import PRIORITY_SYSTEM_PRE


class ChaoticMercenaryRedirectHandler:
    """混乱雇佣兵在场时把对敌伤害随机重定向到其他敌方目标。"""

    def __init__(self, event_bus, engine):
        self.engine = engine
        event_bus.subscribe(DamageRedirectEvent, self.on_damage_redirect, PRIORITY_SYSTEM_PRE)

    def on_damage_redirect(self, event):
        run = event.run
        chaotic_uid = run.node_data.get("chaotic_attacker_uid")
        if not chaotic_uid or event.redirected:
            return
        if not event.target.startswith("e") or event.source not in ("p0", "player", "effect"):
            return
        from ...party.mercenary import pick_chaotic_target
        rerouted = pick_chaotic_target(run, chaotic_uid)
        if not rerouted:
            return
        event.target = rerouted
        if chaotic_uid in run.party_order:
            event.source = f"a{run.party_order.index(chaotic_uid) + 1}"
        else:
            event.source = "chaotic_merc"
        event.redirected = True
