from ...models.state import GameRun, EnemyState
from ...models.events import TurnStartEvent, TurnEndEvent
from ...entities import get_enemy_template
from ...data.text.locale_data import get_locale_text
from ..text.events import JoinedText, LocaleText, RenderedText, TextDocument, locale_text
from ..text.pipeline import render_text


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
            from ...models.events import EnemyRollIntentEvent
            roll_evt = EnemyRollIntentEvent(run, enemy)
            self.engine.event_bus.dispatch(roll_evt)
            if roll_evt.cancelled:
                enemy.intents = []
            else:
                enemy.intents = template.roll_intents(run, self.engine, enemy)
            self.sync_enemy_intents(enemy)

    def enemy_turn(self, run: GameRun) -> str:
        return render_text(self.enemy_turn_events(run), "battle")

    def enemy_turn_events(self, run: GameRun) -> TextDocument:
        logs: list[LocaleText | RenderedText | str] = []
        pending = run.node_data.get("pending_transitions", {})
        if pending:
            for enemy in list(run.enemies):
                if enemy.name in pending:
                    target_phase = pending.pop(enemy.name)
                    template = get_enemy_template(enemy.name)
                    if hasattr(template, "apply_phase_transition"):
                        transition_logs: list[str] = []
                        template.apply_phase_transition(run, enemy, target_phase, self.engine, transition_logs)
                        logs.extend(RenderedText(text=item) for item in transition_logs if item)
            run.node_data["pending_transitions"] = pending
        decay_entries: list[LocaleText] = []
        for idx, enemy in enumerate(run.enemies):
            if enemy.hp > 0 and enemy.shield > 0:
                lost = enemy.shield - (enemy.shield // 2)
                enemy.shield = enemy.shield // 2
                if lost > 0:
                    decay_entries.append(locale_text(
                        "i18n_battle_core.shield_decay_entry",
                        params={"name": enemy.name, "lost": lost},
                    ))
                    from ...models.events import ShieldDecayEvent
                    self.engine.event_bus.dispatch(ShieldDecayEvent(run, f"e{idx+1}", lost))
            else:
                enemy.shield = 0
        if decay_entries:
            logs.append(locale_text(
                "i18n_battle_core.enemy_shield_decay_line",
                params={"entries": JoinedText(parts=decay_entries, separator="，")},
            ))
        self.engine.event_bus.dispatch(TurnStartEvent(run, is_player=False))
        from .party_battle import AOE_INTENT_TYPES, alive_uids, is_all_downed, pick_enemy_target
        viewer = run.player
        viewer_uid = run.user_id
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
                    logs.append(locale_text(
                        "i18n_battle_core.cancel_intent_no_a_log",
                        params={"enemy": enemy.name, "intent": it.desc},
                    ))
                    it.cancelled = True
                    it.cancelled_desc = get_locale_text("i18n_battle_core.cancelled_desc")
                    continue
                if it.cost_ba > 0 and enemy.bonus_actions < it.cost_ba:
                    logs.append(locale_text(
                        "i18n_battle_core.cancel_intent_no_ba_log",
                        params={"enemy": enemy.name, "intent": it.desc},
                    ))
                    it.cancelled = True
                    it.cancelled_desc = get_locale_text("i18n_battle_core.cancelled_desc")
                    continue
                enemy.actions = max(0, enemy.actions - it.cost_a)
                enemy.bonus_actions = max(0, enemy.bonus_actions - it.cost_ba)
                if it.type == "phase_transition":
                    logs.append(locale_text(
                        "i18n_battle_core.phase_transition_log",
                        params={"enemy": enemy.name, "intent": it.desc.split(' (')[0]},
                    ))
                    continue
                target = pick_enemy_target(run, index, it, viewer_uid)
                if target == "ALL":
                    targets = [(uid, run.players[uid]) for uid in alive_uids(run)]
                else:
                    targets = [(target, run.players.get(target))]
                run.node_data["enemy_single_target_attack"] = target != "ALL" and it.type not in AOE_INTENT_TYPES
                try:
                    for uid, player in targets:
                        if player is None or player.downed or player.hp <= 0:
                            continue
                        run.player = player
                        run.user_id = uid
                        run.node_data["coop_damage_target_uid"] = uid
                        run.node_data["coop_damage_aoe"] = target == "ALL"
                        run.node_data["current_acting_enemy_idx"] = run.enemies.index(enemy) if enemy in run.enemies else index - 1
                        template_logs: list[str] = []
                        try:
                            template.execute_intent(run, self.engine, enemy, it, template_logs)
                        finally:
                            run.node_data.pop("current_acting_enemy_idx", None)
                            run.player = viewer
                            run.user_id = viewer_uid
                        logs.extend(RenderedText(text=item) for item in template_logs if item)
                finally:
                    run.node_data.pop("enemy_single_target_attack", None)
                if is_all_downed(run):
                    if run.player_count() > 1:
                        logs.append(locale_text(key="i18n_battle_core.coop_all_downed_log"))
                    break
            if is_all_downed(run):
                break
        self.engine.event_bus.dispatch(TurnEndEvent(run, is_player=False))
        run.node_data.pop("coop_damage_aoe", None)
        run.node_data.pop("coop_damage_target_uid", None)
        for enemy in run.enemies:
            enemy.actions = enemy.max_actions
            enemy.bonus_actions = enemy.max_bonus_actions
        document: TextDocument = []
        for item in logs:
            document.append(RenderedText(text=item) if isinstance(item, str) else item)
        return document
