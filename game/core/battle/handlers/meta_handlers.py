from ....models.events import (
    BattleStartEvent, MinionSummonEvent, DamageTakeEvent,
    MinionDeathEvent, BattleWinEvent, BuffAppliedEvent,
)
from ....models.stats_tracker import StatsTracker


class RallyTriggerHandler:
    """维护集结计数，供依赖召唤次数的效果读取。"""

    def __init__(self, event_bus, engine):
        self.engine = engine
        event_bus.subscribe(BattleStartEvent, self.on_battle_start)
        event_bus.subscribe(MinionSummonEvent, self.on_minion_summon)

    def on_battle_start(self, event):
        event.run.node_data["rally_count"] = 0

    def on_minion_summon(self, event):
        event.run.node_data["rally_count"] = event.run.node_data.get("rally_count", 0) + 1


class StatTrackingHandler:
    """统计伤害、击杀并在战斗胜利时落盘。"""

    def __init__(self, event_bus, save_manager):
        self.save_manager = save_manager
        event_bus.subscribe(DamageTakeEvent, self.on_damage_take)
        event_bus.subscribe(MinionDeathEvent, self.on_minion_death)
        event_bus.subscribe(BattleWinEvent, self.on_battle_win)

    @staticmethod
    def _stat_uid(run):
        if run is None:
            return ""
        player = getattr(run, "player", None)
        if player is not None and getattr(player, "is_mercenary", False):
            return getattr(player, "mercenary_owner", "") or ""
        return getattr(run, "user_id", "")

    def on_damage_take(self, event):
        if event.target.startswith("e") and event.amount > 0:
            StatsTracker.record_damage(event.run, self._stat_uid(event.run), event.amount)

    def on_minion_death(self, event):
        if event.is_enemy:
            StatsTracker.record_kill(event.run, self._stat_uid(event.run))

    def on_battle_win(self, event):
        StatsTracker.flush(self.save_manager, event.run)


class AchievementObserver:
    """在 Buff 落地后记录成就统计，避免引擎直接判断具体 Buff ID。"""

    def __init__(self, event_bus, engine, save_manager):
        self.engine = engine
        self.save_manager = save_manager
        event_bus.subscribe(BuffAppliedEvent, self.on_buff_applied)

    def on_buff_applied(self, event):
        if event.buff_id != "fusion_overcharge":
            return
        entity = event.entity
        run = event.run
        if getattr(entity, "is_mercenary", False):
            return
        uid = run.uid_for(entity)
        if not uid:
            return
        if uid != getattr(run, "user_id", "") and uid not in run.human_uids():
            return
        total = sum(b.stacks for b in getattr(entity, "buffs", []) if b.id == "fusion_overcharge")
        if total < 8:
            return
        from ...progress.achievement_service import AchievementService
        AchievementService(self.save_manager).record_stat(
            uid,
            "max_fusion_overcharge",
            total,
            mode="max",
            run=run,
            battle_engine=self.engine,
        )
