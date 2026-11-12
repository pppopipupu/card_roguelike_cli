import random

from ..entities import get_relic_name
from ..data.balance_config import (
    COOP_AUTO_TARGET_CANDIDATE_COUNT,
    COOP_BUFF_STACKS_MIN,
    COOP_DOWNED_HP,
    COOP_MEND_CLEANSE_STACKS,
    COOP_PERCENT_BASE,
    COOP_REST_HEAL_PERCENT,
    COOP_REST_MEND_PERCENT,
    REWARD_CARD_COUNT,
)
from ..data.locale_data import get_locale_text
from .deck_service import DeckService


class CoopExploreMixin:
    def _coop(self, run):
        from .coop_engine import coop_for_map_engine
        return coop_for_map_engine(self.save_manager, self.map_engine)

    def _coop_finish(self, run, prefix):
        return self._coop(run).finish_player_node(run, run.user_id, prefix)

    def _choose_coop_reward(self, run, option_idx):
        data = run.node_data
        if data.get("coop_done"):
            return get_locale_text("i18n_coop_explore.coop_done_waiting")
        pool = data.get("coop_relic_pool") or []
        if 1 <= option_idx <= len(pool):
            return self._claim_coop_relic(run, option_idx - 1)
        items = data.get("items", [])
        local_idx = option_idx - len(pool)
        available = [item for item in items if not item.get("taken")]
        if local_idx < 1 or local_idx > len(available):
            return get_locale_text("i18n_coop_explore.err_invalid_reward_idx")
        chosen = available[local_idx - 1]
        real_idx = items.index(chosen)
        if chosen.get("type") == "card_reward":
            return self._claim_single_item(run, real_idx)
        res = self._claim_single_item(run, real_idx)
        available = [item for item in items if not item.get("taken")]
        if not available:
            return self._coop_finish(run, res)
        return res

    def _claim_coop_relic(self, run, pool_idx):
        data = run.node_data
        pool = data.get("coop_relic_pool") or []
        if pool_idx < 0 or pool_idx >= len(pool):
            return get_locale_text("i18n_coop_explore.err_invalid_reward_idx")
        entry = pool[pool_idx]
        rid = entry.get("relic_id")
        if entry.get("claimed_by"):
            claimant = run.players.get(entry["claimed_by"])
            player_name = claimant.name if claimant else entry["claimed_by"]
            return get_locale_text(
                "i18n_coop_explore.relic_claimed_by_other",
                relic_name=get_relic_name(rid),
                player_name=player_name,
            )
        uid = run.user_id
        if any(item.get("claimed_by") == uid for item in pool):
            return get_locale_text("i18n_coop_explore.relic_limit_reached")
        player = run.players.get(uid) or run.player
        if rid in player.relics:
            return get_locale_text("i18n_coop_explore.relic_already_owned", relic_name=get_relic_name(rid))
        entry["claimed_by"] = uid
        player.relics.append(rid)
        if rid == "red_bottle":
            player.max_hp += 5
            player.hp += 5
        notice = get_locale_text(
            "i18n_coop_explore.relic_taken_notice",
            player_name=player.name,
            relic_name=get_relic_name(rid),
        )
        coop = self._coop(run)
        for other_uid in run.party_order:
            if other_uid != uid:
                coop._notice(run, other_uid, notice)
        msg = get_locale_text("i18n_coop_explore.relic_gained", relic_name=get_relic_name(rid))
        items = data.get("items", [])
        if not [item for item in items if not item.get("taken")]:
            return self._coop_finish(run, msg)
        return msg

    def _choose_coop_rest(self, run, option_idx, target):
        data = run.node_data
        if data.get("coop_done"):
            return get_locale_text("i18n_coop_explore.coop_done_waiting")
        p = run.player
        if option_idx == 1:
            heal = p.max_hp * COOP_REST_HEAL_PERCENT // COOP_PERCENT_BASE
            p.hp = min(p.max_hp, p.hp + heal)
            return self._coop_finish(run, get_locale_text("i18n_coop_explore.rest_heal", heal=heal))
        if option_idx == 2:
            stats = self.save_manager.load_stats(run.user_id)
            class_cards = DeckService.get_class_spell_pool(p, stats, include_coop=True)
            reward_cards = random.sample(class_cards, min(REWARD_CARD_COUNT, len(class_cards))) if class_cards else []
            from ..models.state import check_and_replace_fireball
            reward_cards = [check_and_replace_fireball(run, cid) for cid in reward_cards]
            for item in data.get("items", []):
                item["taken"] = True
            self.start_card_select(run, reward_cards, "rest", init_event=False, title_key="i18n_explore_core.meditate_title", desc_key="i18n_explore_core.meditate_desc")
            return get_locale_text("msg_rest_meditate")
        if option_idx == 3:
            data["upgrade_source"] = "rest"
            data["pending_upgrade"] = True
            return "UPGRADE_FLOW"
        if option_idx == 4:
            current = run.uid_for(run.player)
            resolved = self.map_engine.battle_engine.combat_resolver.resolve_ally(run, target)
            if not resolved or resolved[0] == current or resolved[2] is not None:
                candidates = [
                    uid
                    for uid in run.party_order
                    if uid != current
                    and uid in run.players
                    and run.players[uid].hp > COOP_DOWNED_HP
                    and not run.players[uid].downed
                ]
                if len(candidates) != COOP_AUTO_TARGET_CANDIDATE_COUNT:
                    names = get_locale_text("i18n_coop_explore.list_delimiter").join(f"a{run.party_order.index(uid) + 1}" for uid in candidates)
                    return get_locale_text("i18n_coop_explore.mend_target_prompt", names=names)
                resolved = (candidates[0], run.players[candidates[0]], None)
            uid, ally, grid = resolved
            heal = ally.max_hp * COOP_REST_MEND_PERCENT // COOP_PERCENT_BASE
            ally.hp = min(ally.max_hp, ally.hp + heal)
            from ..entities.buffs import is_debuff
            removed = ""
            for buff in list(ally.buffs):
                if is_debuff(buff.id):
                    buff.stacks -= COOP_MEND_CLEANSE_STACKS
                    removed = get_locale_text("i18n_coop_explore.mend_cleanse_suffix", buff_name=buff.name)
                    if buff.stacks <= COOP_BUFF_STACKS_MIN:
                        ally.buffs.remove(buff)
                    break
            msg = get_locale_text("i18n_coop_explore.mend_success", ally_name=ally.name, heal=heal, removed=removed)
            return self._coop_finish(run, msg)
        return get_locale_text("err_invalid_option_idx")

    def _begin_coop_gem(self, run, previous):
        if not getattr(run, "coop_id", "") or not previous:
            return
        from .coop_engine import SHARED_PERSIST_KEYS
        for key in SHARED_PERSIST_KEYS:
            if key in previous and key != "coop_node_type":
                run.node_data[key] = previous[key]
        run.node_data["gem_prev_coop_type"] = previous.get("coop_node_type", "")
        run.node_data["coop_node_type"] = "gem_insert"

    def _end_coop_gem(self, run, gem_data, next_type, next_data):
        run.node_type = next_type
        run.node_data = next_data if next_data is not None else {}
        if not getattr(run, "coop_id", "") or not gem_data:
            return
        from .coop_engine import SHARED_PERSIST_KEYS
        for key in SHARED_PERSIST_KEYS:
            if key in gem_data and key not in run.node_data:
                run.node_data[key] = gem_data[key]
        previous_type = gem_data.get("gem_prev_coop_type") or next_type
        run.node_data["coop_node_type"] = previous_type
        run.node_data.pop("gem_prev_coop_type", None)
        shared = getattr(run, "_coop_shared", None)
        if isinstance(shared, dict):
            shared.pop("gem_prev_coop_type", None)
