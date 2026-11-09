import random

from ..entities import ALL_CARDS, get_relic_name
from ..entities.cards.market import is_coop_only


class CoopExploreMixin:
    def _coop(self, run):
        from .coop_engine import CoopEngine
        return CoopEngine(self.save_manager, self.map_engine.battle_engine)

    def _coop_finish(self, run, prefix):
        return self._coop(run).finish_player_node(run, run.user_id, prefix)

    def _choose_coop_reward(self, run, option_idx):
        data = run.node_data
        if data.get("coop_done"):
            return "⏳ 你已完成本节点行动，正在等待队友。"
        pending = data.get("pending_cards")
        if pending is not None:
            can_skip = data.get("pending_card_can_skip", True)
            skip_idx = len(pending) + 1
            if not can_skip and (option_idx < 1 or option_idx > len(pending)):
                return "❌ 该卡牌奖励不能跳过。"
            if can_skip and (option_idx < 1 or option_idx > skip_idx):
                return "❌ 无效的选择序号。"
            data["pending_cards"] = None
            data["pending_card_can_skip"] = False
            if option_idx == skip_idx:
                msg = "你跳过了这次选卡。"
            else:
                cid = pending[option_idx - 1]
                from ..models.state import ensure_card_state
                c_state = ensure_card_state(cid)
                from ..models.events import CardObtainEvent
                self.map_engine.battle_engine.event_bus.dispatch(CardObtainEvent(run, c_state))
                p = run.player
                p.deck.append(c_state)
                card = ALL_CARDS.get(cid)
                msg = f"你将【{card.name if card else cid}】加入了卡组。"
            available = [item for item in data.get("items", []) if not item.get("taken")]
            if not available:
                return self._coop_finish(run, msg)
            return msg
        items = data.get("items", [])
        available = [item for item in items if not item.get("taken")]
        if option_idx < 1 or option_idx > len(available):
            return "❌ 无效的奖励序号。"
        chosen = available[option_idx - 1]
        real_idx = items.index(chosen)
        if chosen.get("type") == "card_reward":
            chosen["taken"] = True
            data["pending_cards"] = list(chosen.get("cards", []))
            data["pending_card_can_skip"] = True
            data["pending_card_upgraded"] = False
            cards = chosen.get("cards", [])
            lines = ["🃏 你开启了个人卡牌三选一奖励，请选择一张加入卡组："]
            for idx, cid in enumerate(cards, 1):
                card = ALL_CARDS.get(cid)
                lines.append(f" [{idx}] {card.name if card else cid}")
            lines.append(f" [{len(cards) + 1}] 跳过本次选卡")
            return "\n".join(lines)
        if chosen.get("type") == "shared_relic":
            chosen["taken"] = True
            rid = chosen.get("relic_id")
            count = self._coop(run).gain_shared_relic(run, run.user_id, rid)
            msg = f"🎒 你登记争夺共享遗物【{get_relic_name(rid)}】（当前 {count} 人争夺）。全队完成奖励后将进行猜拳裁决。"
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
            return "⏳ 你已完成本节点行动，正在等待队友。"
        pending = data.get("pending_cards")
        if pending is not None:
            skip_idx = len(pending) + 1
            if option_idx < 1 or option_idx > skip_idx:
                return "❌ 无效的选择序号。"
            data["pending_cards"] = None
            if option_idx == skip_idx:
                msg = "你放弃了这次冥想感悟。"
            else:
                cid = pending[option_idx - 1]
                from ..models.state import ensure_card_state
                c_state = ensure_card_state(cid)
                from ..models.events import CardObtainEvent
                self.map_engine.battle_engine.event_bus.dispatch(CardObtainEvent(run, c_state))
                run.player.deck.append(c_state)
                card = ALL_CARDS.get(cid)
                msg = f"你领悟了【{card.name if card else cid}】并加入卡组。"
            return self._coop_finish(run, msg)
        p = run.player
        if option_idx == 1:
            heal = p.max_hp * 35 // 100
            p.hp = min(p.max_hp, p.hp + heal)
            return self._coop_finish(run, f"你感到精力充沛，恢复了 {heal} 点生命值。")
        if option_idx == 2:
            class_color = "warrior" if getattr(p, "selected_class", "法师") == "战士" else "wizard"
            stats = self.save_manager.load_stats(run.user_id)
            from ..entities.cards.market import is_card_available
            class_cards = [
                cid for cid, c in ALL_CARDS.items()
                if c.color == class_color
                and c.type == "spell"
                and c.rarity not in ("legendary", "mythic", "artifact")
                and not cid.startswith("curse_")
                and not cid.startswith("duel_")
                and (getattr(run, "coop_id", "") or not is_coop_only(cid))
                and is_card_available(cid, stats)
            ]
            reward_cards = random.sample(class_cards, min(3, len(class_cards))) if class_cards else []
            from ..models.state import check_and_replace_fireball
            reward_cards = [check_and_replace_fireball(run, cid) for cid in reward_cards]
            data["pending_cards"] = reward_cards
            lines = ["你面对篝火静静冥想，脑海中浮现出了三道奥术灵光："]
            for idx, cid in enumerate(reward_cards, 1):
                card = ALL_CARDS.get(cid)
                lines.append(f" [{idx}] {card.name if card else cid}")
            lines.append(f" [{len(reward_cards) + 1}] 放弃感悟")
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
                    and run.players[uid].hp > 0
                    and not run.players[uid].downed
                ]
                if len(candidates) != 1:
                    names = "、".join(f"a{run.party_order.index(uid) + 1}" for uid in candidates)
                    return f"❌ 请指定要救治的队友，例如：选择 4 a2。当前可选：{names}"
                resolved = (candidates[0], run.players[candidates[0]], None)
            uid, ally, grid = resolved
            heal = ally.max_hp * 30 // 100
            ally.hp = min(ally.max_hp, ally.hp + heal)
            from ..entities.buffs import is_debuff
            removed = ""
            for buff in list(ally.buffs):
                if is_debuff(buff.id):
                    buff.stacks -= 1
                    removed = f"，并净化了 1 层【{buff.name}】"
                    if buff.stacks <= 0:
                        ally.buffs.remove(buff)
                    break
            msg = f"🔥 你救治了【{ally.name}】，为其恢复 {heal} 点生命{removed}。"
            return self._coop_finish(run, msg)
        return "❌ 无效的选择序号。"

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
