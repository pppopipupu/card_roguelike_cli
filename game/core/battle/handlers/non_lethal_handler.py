from ....models.events import EnemyBeforeDeathEvent, PlayerBeforeDeathEvent
from ..event_bus import PRIORITY_INTERCEPT


class NonLethalCombatHandler:
    def __init__(self, event_bus, engine):
        self.engine = engine
        event_bus.subscribe(PlayerBeforeDeathEvent, self.on_player_before_death, priority=PRIORITY_INTERCEPT - 100)
        event_bus.subscribe(EnemyBeforeDeathEvent, self.on_enemy_before_death, priority=PRIORITY_INTERCEPT - 100)

    def on_player_before_death(self, event: PlayerBeforeDeathEvent):
        if event.cancelled:
            return
        run = event.run
        if not run or not (run.node_data or {}).get("non_lethal"):
            return
        if not (run.node_data or {}).get("npc_combat"):
            return
        event.cancel()
        event.player.hp = 1
        event.player.downed = False
        run.node_data["non_lethal_result"] = "player_yield"

    def on_enemy_before_death(self, event: EnemyBeforeDeathEvent):
        if event.cancelled:
            return
        run = event.run
        if not run or not (run.node_data or {}).get("non_lethal"):
            return
        if not (run.node_data or {}).get("npc_combat"):
            return
        alive_others = [e for e in (run.enemies or ()) if e is not event.enemy and e.hp > 0 and not getattr(e, "is_summon", False)]
        if alive_others:
            return
        event.cancel()
        event.enemy.hp = 1
        run.node_data["non_lethal_result"] = "npc_yield"
