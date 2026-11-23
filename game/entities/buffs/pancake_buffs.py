from .base import BuffImpl, register_buff


@register_buff("pancake_stack_combo")
class PancakeStackComboBuff(BuffImpl):
    def on_card_effect_resolved(self, event, buff_state, entity):
        run = event.run
        if entity != run.player or run.node_data.get("pancake_replaying"):
            return
        uid = run.uid_for(run.player) or run.user_id
        pend_map = run.node_data.get("pancake_pending_replay")
        if not isinstance(pend_map, dict):
            return
        replay_x = int(pend_map.pop(uid, 0) or 0)
        if replay_x <= 0:
            return
        engine = event.engine
        from ...core.battle.card_executor import execute_extra_card_effect
        run.node_data["pancake_replaying"] = True
        try:
            for _ in range(replay_x):
                if engine.is_battle_won(run):
                    break
                execute_extra_card_effect(engine, run, event.card, event.target, trigger_type="replay")
        finally:
            run.node_data["pancake_replaying"] = False
