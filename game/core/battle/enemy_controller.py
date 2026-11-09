from ...models.state import GameRun, EnemyState
from ...models.events import TurnStartEvent, TurnEndEvent
from ...entities import get_enemy_template

class EnemyTurnController:
    def __init__(self, engine):
        self.engine = engine

    def sync_enemy_intents(self, enemy: EnemyState):
        from ...models.state import EnemyIntentState
        has_phase_transition = any(it.type == "phase_transition" for it in enemy.intents)
        if has_phase_transition:
            enemy.intent_a_type = ""
            enemy.intent_a_val = 0
            enemy.intent_a_desc = ""
            enemy.intent_a2_type = ""
            enemy.intent_a2_val = 0
            enemy.intent_a2_desc = ""
            enemy.intent_ba_type = ""
            enemy.intent_ba_val = 0
            enemy.intent_ba_desc = ""
            enemy.intent_ba2_type = ""
            enemy.intent_ba2_val = 0
            enemy.intent_ba2_desc = ""
        has_old_active = False
        old_intents = []
        if not has_phase_transition and enemy.intent_a_desc and "已取消" not in enemy.intent_a_desc and "眩晕" not in enemy.intent_a_desc:
            old_intents.append(EnemyIntentState(type=enemy.intent_a_type, val=enemy.intent_a_val, desc=enemy.intent_a_desc, cost_a=1, cost_ba=0))
            has_old_active = True
        if not has_phase_transition and getattr(enemy, "intent_a2_desc", None) and "已取消" not in enemy.intent_a2_desc:
            old_intents.append(EnemyIntentState(type=enemy.intent_a2_type, val=enemy.intent_a2_val, desc=enemy.intent_a2_desc, cost_a=1, cost_ba=0))
            has_old_active = True
        if not has_phase_transition and enemy.intent_ba_desc and "已取消" not in enemy.intent_ba_desc:
            old_intents.append(EnemyIntentState(type=enemy.intent_ba_type, val=enemy.intent_ba_val, desc=enemy.intent_ba_desc, cost_a=0, cost_ba=1))
            has_old_active = True
        if not has_phase_transition and getattr(enemy, "intent_ba2_desc", None) and "已取消" not in getattr(enemy, "intent_ba2_desc", ""):
            old_intents.append(EnemyIntentState(type=enemy.intent_ba2_type, val=enemy.intent_ba2_val, desc=enemy.intent_ba2_desc, cost_a=0, cost_ba=1))
            has_old_active = True

        if has_old_active:
            if not enemy.intents or len(enemy.intents) != len(old_intents) or any(
                enemy.intents[i].type != old_intents[i].type or enemy.intents[i].desc != old_intents[i].desc
                for i in range(min(len(enemy.intents), len(old_intents)))
            ):
                enemy.intents = old_intents

        from ...models.events import EnemySyncIntentsEvent
        evt = EnemySyncIntentsEvent(enemy)
        self.engine.event_bus.dispatch(evt)

        has_stun = any(b.id == "stun" and b.stacks > 0 for b in getattr(enemy, "buffs", []))
        if has_stun:
            pass
        else:
            temp_a = enemy.actions
            temp_ba = enemy.bonus_actions
            for it in enemy.intents:
                it.cancelled = False
                it.cancelled_desc = ""
                if it.cost_a > 0:
                    if temp_a >= it.cost_a:
                        temp_a -= it.cost_a
                    else:
                        it.cancelled = True
                        it.cancelled_desc = "已取消 (动作点不足)"
                if it.cost_ba > 0:
                    if temp_ba >= it.cost_ba:
                        temp_ba -= it.cost_ba
                    else:
                        it.cancelled = True
                        it.cancelled_desc = "已取消 (动作点不足)"
        enemy.intent_a_type = ""
        enemy.intent_a_val = 0
        enemy.intent_a_desc = ""
        enemy.intent_a2_type = ""
        enemy.intent_a2_val = 0
        enemy.intent_a2_desc = ""
        enemy.intent_ba_type = ""
        enemy.intent_ba_val = 0
        enemy.intent_ba_desc = ""
        enemy.intent_ba2_type = ""
        enemy.intent_ba2_val = 0
        enemy.intent_ba2_desc = ""
        a_slots = []
        ba_slots = []
        for it in enemy.intents:
            desc = it.cancelled_desc if it.cancelled else it.desc
            itype = "" if (it.cancelled or it.type == "stun") else it.type
            val = 0 if it.cancelled else it.val
            if it.cost_ba > 0:
                ba_slots.append((itype, val, desc))
            else:
                a_slots.append((itype, val, desc))
        if len(a_slots) >= 1:
            enemy.intent_a_type, enemy.intent_a_val, enemy.intent_a_desc = a_slots[0]
        if len(a_slots) >= 2:
            enemy.intent_a2_type, enemy.intent_a2_val, enemy.intent_a2_desc = a_slots[1]
        if len(ba_slots) >= 1:
            enemy.intent_ba_type, enemy.intent_ba_val, enemy.intent_ba_desc = ba_slots[0]
        if len(ba_slots) >= 2:
            enemy.intent_ba2_type, enemy.intent_ba2_val, enemy.intent_ba2_desc = ba_slots[1]

    def roll_enemy_intent(self, run: GameRun):
        for enemy in run.enemies:
            if enemy.hp <= 0:
                continue
            enemy.intent_type = ""
            enemy.intent_val = 0
            enemy.intent_desc = ""
            enemy.intent_a_type = ""
            enemy.intent_a_val = 0
            enemy.intent_a_desc = ""
            enemy.intent_a2_type = ""
            enemy.intent_a2_val = 0
            enemy.intent_a2_desc = ""
            enemy.intent_ba_type = ""
            enemy.intent_ba_val = 0
            enemy.intent_ba_desc = ""
            enemy.intent_ba2_type = ""
            enemy.intent_ba2_val = 0
            enemy.intent_ba2_desc = ""
            enemy.intents = []
            template = get_enemy_template(enemy.name)
            enemy.intents = template.roll_intents(run, self.engine, enemy)
            self.sync_enemy_intents(enemy)

    def enemy_turn(self, run: GameRun) -> str:
        if getattr(run, "coop_id", ""):
            from ..coop_engine import CoopEngine
            return CoopEngine(self.engine.save_manager, self.engine).enemy_turn(run, self)
        logs = []
        pending = run.node_data.get("pending_transitions", {})
        if pending:
            active_enemies = list(run.enemies)
            for enemy in active_enemies:
                if enemy.name in pending:
                    target_phase = pending.pop(enemy.name)
                    template = get_enemy_template(enemy.name)
                    if hasattr(template, "apply_phase_transition"):
                        template.apply_phase_transition(run, enemy, target_phase, self.engine, logs)
            run.node_data["pending_transitions"] = pending
        decay_enemies = []
        for idx, enemy in enumerate(run.enemies):
            if enemy.hp > 0 and enemy.shield > 0:
                lost = enemy.shield - (enemy.shield // 2)
                enemy.shield = enemy.shield // 2
                if lost > 0:
                    decay_enemies.append(f"【{enemy.name}】失去 {lost} 点护盾")
                    from ...models.events import ShieldDecayEvent
                    self.engine.event_bus.dispatch(ShieldDecayEvent(run, f"e{idx+1}", lost))
            else:
                enemy.shield = 0
        if decay_enemies:
            logs.append("🛡️ 护盾流失：" + "，".join(decay_enemies))
        evt_turn = TurnStartEvent(run, is_player=False)
        self.engine.event_bus.dispatch(evt_turn)
        active_enemies = list(run.enemies)
        for idx, enemy in enumerate(active_enemies):
            if enemy.hp <= 0:
                continue
            if enemy.actions == 0 and enemy.bonus_actions == 0:
                continue
            template = get_enemy_template(enemy.name)
            for it in list(enemy.intents):
                if enemy.hp <= 0:
                    break
                if it.cancelled:
                    continue
                if it.cost_a > 0 and enemy.actions < it.cost_a:
                    logs.append(f"⚠️ 【{enemy.name}】因动作点（A）不足，取消了意图【{it.desc}】。")
                    it.cancelled = True
                    it.cancelled_desc = "已取消 (动作点不足)"
                    continue
                if it.cost_ba > 0 and enemy.bonus_actions < it.cost_ba:
                    logs.append(f"⚠️ 【{enemy.name}】因附赠动作点（BA）不足，取消了意图【{it.desc}】。")
                    it.cancelled = True
                    it.cancelled_desc = "已取消 (动作点不足)"
                    continue
                enemy.actions = max(0, enemy.actions - it.cost_a)
                enemy.bonus_actions = max(0, enemy.bonus_actions - it.cost_ba)
                if it.type == "phase_transition":
                    logs.append(f"⏳ 【{enemy.name}】正在进行【{it.desc.split(' (')[0]}】！此回合免疫所有伤害。")
                    continue
                run.node_data["current_acting_enemy_idx"] = run.enemies.index(enemy)
                try:
                    template.execute_intent(run, self.engine, enemy, it, logs)
                finally:
                    if "current_acting_enemy_idx" in run.node_data:
                        del run.node_data["current_acting_enemy_idx"]
        evt_turn_end = TurnEndEvent(run, is_player=False)
        self.engine.event_bus.dispatch(evt_turn_end)
        for enemy in run.enemies:
            enemy.actions = enemy.max_actions
            enemy.bonus_actions = enemy.max_bonus_actions
        return "\n".join(logs)
