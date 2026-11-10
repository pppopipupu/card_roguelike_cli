from ...models.state import GameRun, EnemyState
from ...models.events import TurnStartEvent, TurnEndEvent
from ...entities import get_enemy_template
from ...data.locale_data import get_locale_text

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

        if has_old_active and not enemy.intents:
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
                        it.cancelled_desc = get_locale_text("i18n_battle_core.cancelled_desc")
                if it.cost_ba > 0:
                    if temp_ba >= it.cost_ba:
                        temp_ba -= it.cost_ba
                    else:
                        it.cancelled = True
                        it.cancelled_desc = get_locale_text("i18n_battle_core.cancelled_desc")
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
            if hasattr(template, "on_battle_start") and not getattr(enemy, "_battle_init_done", False):
                enemy._battle_init_done = True
                template.on_battle_start(run, enemy, self.engine)
            for buff in list(getattr(enemy, "buffs", [])):
                if buff.id == "astral_speed":
                    enemy.actions += buff.stacks
                    enemy.buffs.remove(buff)
                elif buff.id == "bonus_speed":
                    enemy.bonus_actions += buff.stacks
                    enemy.buffs.remove(buff)
            enemy.intents = template.roll_intents(run, self.engine, enemy)
            self.sync_enemy_intents(enemy)

    def enemy_turn(self, run: GameRun) -> str:
        logs = []
        pending = run.node_data.get("pending_transitions", {})
        if pending:
            for enemy in list(run.enemies):
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
                    decay_enemies.append(get_locale_text("i18n_battle_core.shield_decay_entry", name=enemy.name, lost=lost))
                    from ...models.events import ShieldDecayEvent
                    self.engine.event_bus.dispatch(ShieldDecayEvent(run, f"e{idx+1}", lost))
            else:
                enemy.shield = 0
        if decay_enemies:
            logs.append(get_locale_text("i18n_battle_core.enemy_shield_decay_line", entries="，".join(decay_enemies)))
        self.engine.event_bus.dispatch(TurnStartEvent(run, is_player=False))
        is_coop = bool(getattr(run, "coop_id", ""))
        viewer = run.player
        viewer_uid = run.user_id
        coop = None

        def coop_engine():
            nonlocal coop
            if coop is None:
                from ..coop_engine import CoopEngine
                coop = CoopEngine(self.engine.save_manager, self.engine)
            return coop

        for index, enemy in enumerate(list(run.enemies), 1):
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
                    logs.append(get_locale_text("i18n_battle_core.cancel_intent_no_a_log", enemy=enemy.name, intent=it.desc))
                    it.cancelled = True
                    it.cancelled_desc = get_locale_text("i18n_battle_core.cancelled_desc")
                    continue
                if it.cost_ba > 0 and enemy.bonus_actions < it.cost_ba:
                    logs.append(get_locale_text("i18n_battle_core.cancel_intent_no_ba_log", enemy=enemy.name, intent=it.desc))
                    it.cancelled = True
                    it.cancelled_desc = get_locale_text("i18n_battle_core.cancelled_desc")
                    continue
                enemy.actions = max(0, enemy.actions - it.cost_a)
                enemy.bonus_actions = max(0, enemy.bonus_actions - it.cost_ba)
                if it.type == "phase_transition":
                    logs.append(get_locale_text("i18n_battle_core.phase_transition_log", enemy=enemy.name, intent=it.desc.split(' (')[0]))
                    continue
                if is_coop:
                    coop_eng = coop_engine()
                    target = coop_eng._pick_enemy_target(run, index, it, viewer_uid)
                    if target == "ALL":
                        targets = [(uid, run.players[uid]) for uid in coop_eng._alive_uids(run)]
                    else:
                        targets = [(target, run.players.get(target))]
                else:
                    targets = [("p0", run.player)]
                for uid, player in targets:
                    if player is None or player.downed or player.hp <= 0:
                        continue
                    if is_coop:
                        run.player = player
                        run.user_id = uid
                        run.node_data["coop_damage_target_uid"] = uid
                        run.node_data["coop_damage_aoe"] = target == "ALL"
                    run.node_data["current_acting_enemy_idx"] = run.enemies.index(enemy) if enemy in run.enemies else index - 1
                    try:
                        template.execute_intent(run, self.engine, enemy, it, logs)
                    finally:
                        run.node_data.pop("current_acting_enemy_idx", None)
                        if is_coop:
                            run.player = viewer
                            run.user_id = viewer_uid
                if is_coop and coop_engine().is_all_downed(run):
                    logs.append(get_locale_text("i18n_battle_core.coop_all_downed_log"))
                    break
            if is_coop and coop_engine().is_all_downed(run):
                break
        self.engine.event_bus.dispatch(TurnEndEvent(run, is_player=False))
        if is_coop:
            run.node_data.pop("coop_damage_aoe", None)
            run.node_data.pop("coop_damage_target_uid", None)
            for player in run.players.values():
                player.buffs[:] = [buff for buff in player.buffs if buff.id != "coop_aegis"]
        for enemy in run.enemies:
            enemy.actions = enemy.max_actions
            enemy.bonus_actions = enemy.max_bonus_actions
        return "\n".join(logs)
