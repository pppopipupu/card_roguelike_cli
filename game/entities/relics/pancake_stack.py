from .base import RelicImpl
from .registry import register_relic
from ...data.entities.buffs.buff_data import BUFF_CONFIG
from ...data.text.locale_data import get_locale_text


def _get_combo_buff(player):
    for b in getattr(player, "buffs", []) or []:
        if b.id == "pancake_stack_combo":
            return b
    return None


@register_relic("pancake_stack")
class PancakeStackRelic(RelicImpl):
    def on_battle_start(self, run, engine):
        uid = run.uid_for(run.player) or run.user_id
        last_map = run.node_data.get("pancake_last_cost_a")
        if isinstance(last_map, dict):
            last_map.pop(uid, None)
        pend_map = run.node_data.get("pancake_pending_replay")
        if isinstance(pend_map, dict):
            pend_map.pop(uid, None)

    def on_card_play(self, event, run, engine):
        if event.cancelled or run.node_data.get("pancake_replaying"):
            return
        p = run.player
        uid = run.uid_for(p) or run.user_id
        cur_cost = int(getattr(event, "cost_a", 0) or 0)
        last_map = run.node_data.setdefault("pancake_last_cost_a", {})
        pend_map = run.node_data.setdefault("pancake_pending_replay", {})
        prev_cost = last_map.get(uid)
        combo_buff = _get_combo_buff(p)
        bcfg = BUFF_CONFIG["pancake_stack_combo"]

        if prev_cost is None or combo_buff is None:
            last_map[uid] = cur_cost
            pend_map[uid] = 0
            if combo_buff is None:
                engine.combat_resolver.add_buff_to(p, "pancake_stack_combo", bcfg["name"], bcfg["desc"], 1)
            else:
                combo_buff.stacks = 1
            engine._log_event(run, get_locale_text("i18n_kappa_pancake.pancake.log_start", cost=cur_cost))
            return

        if cur_cost > int(prev_cost):
            replay_x = max(1, int(combo_buff.stacks) if combo_buff is not None else 1)
            next_stacks = replay_x + 1
            last_map[uid] = cur_cost
            pend_map[uid] = replay_x
            if combo_buff is None:
                engine.combat_resolver.add_buff_to(p, "pancake_stack_combo", bcfg["name"], bcfg["desc"], next_stacks)
            else:
                combo_buff.stacks = next_stacks
            engine._log_event(
                run,
                get_locale_text(
                    "i18n_kappa_pancake.pancake.log_combo",
                    stacks=next_stacks,
                    prev=int(prev_cost),
                    cost=cur_cost,
                    card=event.card.name,
                    replay=replay_x,
                ),
            )
            return

        last_map.pop(uid, None)
        pend_map[uid] = 0
        if combo_buff is not None and combo_buff in p.buffs:
            p.buffs.remove(combo_buff)
        engine._log_event(
            run,
            get_locale_text(
                "i18n_kappa_pancake.pancake.log_break",
                prev=int(prev_cost),
                cost=cur_cost,
            ),
        )
