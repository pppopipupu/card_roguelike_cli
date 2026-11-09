import random

from ..entities import ALL_CARDS, get_relic_name
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
        from .coop_engine import CoopEngine
        battle_engine = self.map_engine.battle_engine
        root = getattr(battle_engine, "game_engine", None) or battle_engine
        return CoopEngine(self.save_manager, root)

    def _coop_finish(self, run, prefix):
        return self._coop(run).finish_player_node(run, run.user_id, prefix)

    def _choose_coop_reward(self, run, option_idx):
        data = run.node_data
        if data.get("coop_done"):
            return get_locale_text("i18n_coop_explore.coop_done_waiting")
        pending = data.get("pending_cards")
        if pending is not None:
            can_skip = data.get("pending_card_can_skip", True)
            skip_idx = len(pending) + 1
            if not can_skip and (option_idx < 1 or option_idx > len(pending)):
                return get_locale_text("i18n_coop_explore.err_cannot_skip_reward")
            if can_skip and (option_idx < 1 or option_idx > skip_idx):
                return get_locale_text("err_invalid_option_idx")
            data["pending_cards"] = None
            data["pending_card_can_skip"] = False
            if option_idx == skip_idx:
                msg = get_locale_text("i18n_coop_explore.card_select_skipped")
            else:
                cid = pending[option_idx - 1]
                from ..models.state import ensure_card_state
                c_state = ensure_card_state(cid)
                from ..models.events import CardObtainEvent
                self.map_engine.battle_engine.event_bus.dispatch(CardObtainEvent(run, c_state))
                p = run.player
                p.deck.append(c_state)
                card = ALL_CARDS.get(cid)
                msg = get_locale_text("i18n_coop_explore.card_reward_gained", card_name=card.name if card else cid)
            available = [item for item in data.get("items", []) if not item.get("taken")]
            if not available:
                return self._coop_finish(run, msg)
            return msg
        items = data.get("items", [])
        available = [item for item in items if not item.get("taken")]
        if option_idx < 1 or option_idx > len(available):
            return get_locale_text("i18n_coop_explore.err_invalid_reward_idx")
        chosen = available[option_idx - 1]
        real_idx = items.index(chosen)
        if chosen.get("type") == "card_reward":
            chosen["taken"] = True
            data["pending_cards"] = list(chosen.get("cards", []))
            data["pending_card_can_skip"] = True
            data["pending_card_upgraded"] = False
            cards = chosen.get("cards", [])
            lines = [get_locale_text("i18n_coop_explore.card_reward_start")]
            for idx, cid in enumerate(cards, 1):
                card = ALL_CARDS.get(cid)
                lines.append(f" [{idx}] {card.name if card else cid}")
            lines.append(get_locale_text("i18n_coop_explore.reward_skip_option", idx=len(cards) + 1))
            return "\n".join(lines)
        if chosen.get("type") == "shared_relic":
            chosen["taken"] = True
            rid = chosen.get("relic_id")
            count = self._coop(run).gain_shared_relic(run, run.user_id, rid)
            msg = get_locale_text("i18n_coop_explore.shared_relic_registered", relic_name=get_relic_name(rid), count=count)
            remaining = [item for item in items if not item.get("taken")]
            if not remaining:
                return self._coop_finish(run, msg)
            return msg
        res = self._claim_single_item(run, real_idx)
        available = [item for item in items if not item.get("taken")]
        if not available:
            return self._coop_finish(run, res)
        return res

    def _choose_coop_rest(self, run, option_idx, target):
        data = run.node_data
        if data.get("coop_done"):
            return get_locale_text("i18n_coop_explore.coop_done_waiting")
        pending = data.get("pending_cards")
        if pending is not None:
            skip_idx = len(pending) + 1
            if option_idx < 1 or option_idx > skip_idx:
                return get_locale_text("err_invalid_option_idx")
            data["pending_cards"] = None
            if option_idx == skip_idx:
                msg = get_locale_text("i18n_coop_explore.meditate_abandoned")
            else:
                cid = pending[option_idx - 1]
                from ..models.state import ensure_card_state
                c_state = ensure_card_state(cid)
                from ..models.events import CardObtainEvent
                self.map_engine.battle_engine.event_bus.dispatch(CardObtainEvent(run, c_state))
                run.player.deck.append(c_state)
                card = ALL_CARDS.get(cid)
                msg = get_locale_text("i18n_coop_explore.meditate_card_gained", card_name=card.name if card else cid)
            return self._coop_finish(run, msg)
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
            data["pending_cards"] = reward_cards
            lines = [get_locale_text("i18n_coop_explore.meditate_desc")]
            for idx, cid in enumerate(reward_cards, 1):
                card = ALL_CARDS.get(cid)
                lines.append(f" [{idx}] {card.name if card else cid}")
            lines.append(get_locale_text("i18n_coop_explore.meditate_skip_option", idx=len(reward_cards) + 1))
            return "\n".join(lines)
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
