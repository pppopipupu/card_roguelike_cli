import random
from typing import Optional
from ...models.state import GameRun, PlayerState, EnemyState, MinionState, Card, check_and_replace_fireball
from ...data.map_config import MapConfig
from ...data.corpse_config import CorpseConfig

from ...entities import ALL_CARDS, ALL_MINIONS, ALL_AMULETS, get_relic_name, get_relic_impl
from ...models.events import (
    CardPlayEvent, CardPlayedEvent, CardExhaustEvent, CardDiscardEvent,
    TurnEndEvent, TurnStartEvent, BattleWinEvent, DamageCalculateEvent
)

class CardPlayer:
    def __init__(self, engine):
        self.engine = engine

    def _handle_card_post_play(self, run, card, c_state, source="played"):
        p = run.player
        from ...models.state import ensure_card_state
        c_state = ensure_card_state(c_state)
        import copy
        clean_state = copy.copy(c_state)
        clean_state.return_left = 0

        if hasattr(card, "handle_post_play") and card.handle_post_play(run, c_state, source, self.engine):
            return
        if getattr(card, "fleeting", False):
            match_state = copy.copy(clean_state)
            match_state.replay = 0
            match_state.fragile = 0
            found = None
            for dc in p.deck:
                if (dc.id == match_state.id and 
                    dc.upgraded == match_state.upgraded and 
                    dc.gems == match_state.gems):
                    found = dc
                    break
            if found:
                p.deck.remove(found)
        elif any(b.id == "void_exhaustion" for b in p.buffs):
            p.exhaust_pile.append(clean_state)
            self.engine._log_event(run, f"✨ [虚空耗竭] 【{card.name}】已被强行移入消耗堆！")
            exhaust_evt = CardExhaustEvent(run, c_state, source)
            self.engine.event_bus.dispatch(exhaust_evt)
        elif card.type in ("minion", "amulet"):
            if card.type == "minion":
                self.engine._log_event(run, f"✨ [消耗] 【{card.name}】进入战场。")
            else:
                self.engine._log_event(run, f"✨ [消耗] 【{card.name}】部署完毕。")
            exhaust_evt = CardExhaustEvent(run, c_state, source)
            self.engine.event_bus.dispatch(exhaust_evt)
        elif getattr(card, "exhaust", False):
            p.exhaust_pile.append(clean_state)
            self.engine._log_event(run, f"✨ [消耗] 【{card.name}】已被移入消耗堆。")
            exhaust_evt = CardExhaustEvent(run, c_state, source)
            self.engine.event_bus.dispatch(exhaust_evt)
        else:
            p.discard_pile.append(clean_state)

    def draw_cards(self, p: PlayerState, count: int, run: Optional[GameRun] = None, ignore_focus: bool = False, depth: int = 0):
        if not ignore_focus and any(b.id == "tactical_focus" for b in p.buffs):
            if run is not None:
                self.engine._log_event(run, "⚠️ [无法抽牌] 本回合无法再抽牌。")
            return
        max_hand = 9 if "mask_of_void" in p.relics else 12
        drawn_cards = []
        reshuffled = False
        hand_full_logged = False
        for _ in range(count):
            if not p.draw_pile:
                if p.discard_pile:
                    p.draw_pile = p.discard_pile.copy()
                    random.shuffle(p.draw_pile)
                    p.discard_pile.clear()
                    reshuffled = True
            if p.draw_pile:
                cid = p.draw_pile.pop()
                is_hell_raider = any(b.id == "hell_raider" for b in p.buffs)
                is_hell_raider_upg = any(b.id == "hell_raider_upgraded" for b in p.buffs)
                if run is not None and (is_hell_raider or is_hell_raider_upg):
                    card_obj = ALL_CARDS.get(cid)
                    cost_a_limit = 2 if is_hell_raider_upg else 1
                    if card_obj and getattr(card_obj, "cost_a", 0) <= cost_a_limit and getattr(card_obj, "cost_ba", 0) == 0:
                        buff_prefix = "地狱狂徒+" if is_hell_raider_upg else "地狱狂徒"
                        self.engine._log_event(run, f"🔥 [{buff_prefix}] 触发自动连携，免费打出刚抽到的 {getattr(card_obj, 'cost_a', 0)}A 卡牌【{card_obj.name}】！")
                        p0_spells = {"first_aid", "get_ready", "adrenaline", "mana_potion", "mass_healing_word", "refresh_spirit", "shield", "misty_step", "arcane_intellect", "calculated_gamble", "time_warp", "time_stop", "archmage_wish", "wizard_magic_shield", "warrior_blood_fury", "wizard_prismatic_wall", "wizard_antimagic_field"}
                        target = "p0"
                        if card_obj.type == "spell" and card_obj.id not in p0_spells:
                            target = self.engine._get_first_alive_enemy(run)
                        elif card_obj.type == "minion" or card_obj.type == "amulet":
                            target = self.engine._get_free_grid(run.player)
                            if not target:
                                target = "p1"
                        res_action = self.engine._execute_card_effect(run, card_obj, target)
                        played_evt = CardPlayedEvent(run, card_obj, target, res_action, is_extra=True)
                        self.engine.event_bus.dispatch(played_evt)
                        self.engine._log_event(run, f" 连携打出反馈：{played_evt.feedback}")
                        self._handle_card_post_play(run, card_obj, cid, source="hell_raider")
                        if is_hell_raider_upg and depth < 5:
                            self.engine._log_event(run, "🔥 [地狱狂徒+] 额外抽取 1 张卡牌。")
                            self.draw_cards(p, 1, run, depth=depth+1)
                        continue
                if len(p.hand) < max_hand:
                    p.hand.append(cid)
                    drawn_cards.append(cid)
                else:
                    p.discard_pile.append(cid)
                    if run is not None:
                        card_obj = ALL_CARDS.get(cid)
                        card_name = card_obj.name if card_obj else "未知卡牌"
                        self.engine._log_event(run, f"⚠️ 提示：手牌已满，卡牌【{card_name}】被放入弃牌堆。")
        if run is not None:
            if reshuffled:
                self.engine._log_event(run, "🔄 弃牌堆已重新洗入抽牌堆。")

    def discard_card(self, run: GameRun, cid) -> str:
        from ...models.state import ensure_card_state
        c_state = ensure_card_state(cid)
        p = run.player
        card = ALL_CARDS.get(c_state)
        discard_evt = CardDiscardEvent(run, c_state, "manual")
        self.engine.event_bus.dispatch(discard_evt)
        if "mindflayer_brain" in p.relics:
            alive = [e for e in run.enemies if e.hp > 0]
            if alive:
                import random
                target_enemy = random.choice(alive)
                idx = run.enemies.index(target_enemy) + 1
                self.engine._log_event(run, f"🧠 [夺心魔脑核] 触发！弃牌对【{target_enemy.name}】造成 3 点心灵伤害！")
                self.engine.combat_resolver.damage_target(run, f"e{idx}", 3, source="relic:mindflayer_brain", damage_type="psychic")
        if not card:
            p.discard_pile.append(c_state)
            return self.engine._append_logs_to_res(run, "")
        if getattr(card, "agile", False):
            target = None
            if card.type == "spell":
                p0_spells = {"first_aid", "get_ready", "adrenaline", "mana_potion", "mass_healing_word", "refresh_spirit", "shield", "misty_step", "arcane_intellect", "calculated_gamble", "time_warp", "time_stop", "archmage_wish"}
                if card.id in p0_spells:
                    target = "p0"
                else:
                    target = self.engine._get_first_alive_enemy(run)
                if target == "0" or target == "e0":
                    target = "e1"
            run.node_data["extra_play_msgs"] = []
            res = self.engine._execute_card_effect(run, card, target)
            if hasattr(card, "execute_tags"):
                card.execute_tags(run, target, self.engine)
            played_evt = CardPlayedEvent(run, card, target, res)
            self.engine.event_bus.dispatch(played_evt)
            res = played_evt.feedback
            extra_msgs = run.node_data.pop("extra_play_msgs", [])
            if len(extra_msgs) > 10:
                res += f"x {len(extra_msgs)}次"
            else:
                res += "".join(extra_msgs)
            self._handle_card_post_play(run, card, c_state, source="agile")
            self._reindex_minions(p)
            return self.engine._append_logs_to_res(run, f"✨ 触发[灵巧]：丢弃【{card.name}】时自动打出！效果：{res}")
        else:
            p.discard_pile.append(c_state)
            self._reindex_minions(p)
            return self.engine._append_logs_to_res(run, "")

    def play_card(self, run: GameRun, hand_idx: int, target: Optional[str] = None) -> str:
        initial_status = [(e.hp, e.shield) for e in run.enemies]
        p = run.player
        if run.node_type != "battle":
            return "❌ 只有在战斗中才能使用卡牌。"
        if hand_idx < 1 or hand_idx > len(p.hand):
            return "❌ 无效的手牌序号。"
        from ...models.state import ensure_card_state
        cid = ensure_card_state(p.hand[hand_idx - 1])
        p.hand[hand_idx - 1] = cid
        card = ALL_CARDS.get(cid)
        if not card:
            return "❌ 卡牌不存在。"
        if getattr(card, "unplayable", False):
            return "❌ 该卡牌不能被打出。"
        base_id = card.id
        is_discover = base_id == "discover"
        is_emperor_eye = base_id.startswith("neutral_emperor_eye")
        if not is_discover:
            if target is None:
                if is_emperor_eye:
                    pass
                elif card.type in ("spell", "attack"):
                    p0_spells = {"first_aid", "get_ready", "adrenaline", "mana_potion", "mass_healing_word", "refresh_spirit", "shield", "misty_step", "arcane_intellect", "calculated_gamble", "time_warp", "time_stop", "archmage_wish"}
                    if card.id in p0_spells:
                        target = "p0"
                    else:
                        target = self.engine._get_first_alive_enemy(run)

            if target is not None:
                if is_emperor_eye:
                    pass
                else:
                    if isinstance(target, str) and target.isdigit():
                        target = f"e{target}"
                    if target == "0" or target == "e0":
                        target = "e1"
                    elif target == "p":
                        target = "p0"
                    if target.startswith("e"):
                        try:
                            grid = int(target[1:]) - 1
                        except ValueError:
                            grid = 0
                        if grid < 0 or grid >= len(run.enemies):
                            return f"❌ 敌方格子 [{target}] 没有敌人。"
                    elif target == "p0":
                        pass
                    elif target.startswith("p"):
                        grid = target[1:]
                        if grid not in p.minions:
                            return f"❌ 我方格子 [{grid}] 没有随从。"
                    else:
                        return "❌ 无效的目标选择。"
        if card.type in ("minion", "amulet") and self.engine._get_free_grid(p) is None:
            return "❌ 你的战场格子已满，无法召唤随从或部署护符。"
        
        req_a = card.cost_a
        req_ba = card.cost_ba
        real_x_a = 0
        real_x_ba = 0
        if req_a == -1:
            real_x_a = p.actions
            req_a = p.actions
        if req_ba == -1:
            real_x_ba = p.bonus_actions
            req_ba = p.bonus_actions

        if "chemical_x" in p.relics:
            if card.cost_a == -1:
                real_x_a += 2
            if card.cost_ba == -1:
                real_x_ba += 2

        run.node_data["last_x_cost_a"] = real_x_a
        run.node_data["last_x_cost_ba"] = real_x_ba

        play_evt = CardPlayEvent(run, card, target, req_a, req_ba)
        self.engine.event_bus.dispatch(play_evt)
        if play_evt.cancelled:
            return f"⚠️ 【时空紊乱】 尤格-索托斯的真理力场发生扭曲！你打出的法术【{card.name}】还未生效，就直接在虚空涟漪中被强制消耗了！"
        req_a = play_evt.cost_a
        req_ba = play_evt.cost_ba
        target = play_evt.target
        if p.actions < req_a or p.bonus_actions < req_ba:
            return f"❌ 你的动作资源不足（需要 {req_a}A {req_ba}BA，当前 {p.actions}A {p.bonus_actions}BA）。"
        p.actions -= req_a
        p.bonus_actions -= req_ba
        p.hand.pop(hand_idx - 1)
        
        split_to_ten_active = False
        split_to_ten_buff = next((b for b in p.buffs if b.id == "split_to_ten"), None)
        if split_to_ten_buff and split_to_ten_buff.stacks > 0:
            split_to_ten_active = True
            split_to_ten_buff.stacks -= 1
            if split_to_ten_buff.stacks <= 0:
                p.buffs.remove(split_to_ten_buff)
        run.node_data["split_to_ten_active"] = split_to_ten_active
        
        initial_stack_len = len(run.node_data.get("state_stack", []))
        run.node_data["current_playing_card_cid"] = cid
        run.node_data["current_playing_card_hand_idx"] = hand_idx - 1
        run.node_data["card_played_triggered_dmg"] = False
        run.node_data["card_played_triggered_shield"] = False
        run.node_data["card_played_triggered_heal"] = False
        run.node_data["current_playing_card_id"] = card.id
        run.node_data["extra_play_msgs"] = []
        try:
            res = self.engine._execute_card_effect(run, card, target)

            suspend_post_play = False
            if len(run.node_data.get("state_stack", [])) > initial_stack_len:
                suspend_post_play = True
                run.node_data["suspended_card_cid"] = cid
                run.node_data["suspended_card_cost_a"] = req_a
                run.node_data["suspended_card_cost_ba"] = req_ba
                run.node_data["suspended_card_hand_idx"] = hand_idx - 1

            if not suspend_post_play:
                if hasattr(card, "execute_tags"):
                    card.execute_tags(run, target, self.engine)

                return_left = cid.return_left
                if return_left <= 0:
                    if hasattr(card, "gems") and card.gems:
                        if "gem_return_5" in card.gems:
                            return_left = 5
                        elif "gem_return_3" in card.gems:
                            return_left = 3

                should_return = False
                import copy
                new_cid = copy.copy(cid)
                if return_left > 0:
                    next_left = return_left - 1
                    if next_left > 0:
                        should_return = True
                        new_cid.return_left = next_left

                if should_return:
                    p.hand.append(new_cid)
                    run.node_data["extra_return_msg"] = f"\n✨ [返回] 【{card.name}】打出后回到了你的手牌！（剩余次数 {next_left}）"
                else:
                    self._handle_card_post_play(run, card, cid, source="played")

                if hasattr(card, "gems") and card.gems:
                    has_shield_gem = any(g in card.gems for g in ("gem_shield_add_3", "gem_shield_add_8"))
                    if has_shield_gem and not run.node_data.get("card_played_triggered_shield", False):
                        self.engine.combat_resolver.gain_shield(run, "p0", 0)
                    has_heal_gem = "gem_heal_add_2" in card.gems
                    if has_heal_gem and not run.node_data.get("card_played_triggered_heal", False):
                        self.engine.combat_resolver.heal_target(run, "p0", 0)
                    has_dmg_gem = "gem_dmg_add_2" in card.gems
                    if has_dmg_gem and not run.node_data.get("card_played_triggered_dmg", False):
                        dmg_target = target
                        if not dmg_target or not dmg_target.startswith("e"):
                            dmg_target = self.engine._get_first_alive_enemy(run)
                        if dmg_target and dmg_target != "0" and dmg_target != "e0":
                            self.engine.combat_resolver.damage_target(run, dmg_target, 0, source="p0", damage_type="effect")
        finally:
            run.node_data["current_playing_card_id"] = ""
            run.node_data["current_playing_card_cid"] = ""
            run.node_data.pop("current_playing_card_hand_idx", None)
            run.node_data.pop("split_to_ten_active", None)

        if not suspend_post_play:
            played_count = run.node_data.get("cards_played_this_turn", 0)
            played_evt = CardPlayedEvent(run, card, target, res)
            self.engine.event_bus.dispatch(played_evt)
            res = played_evt.feedback

            if hasattr(card, "gems") and card.gems:
                for g in card.gems:
                    if g == "gem_gain_a_1":
                        p.actions += 1
                        self.engine._log_event(run, "💎 [劫掠青金石] 触发，获得 1A！")
                    elif g == "gem_gain_a_1_ba_1":
                        p.actions += 1
                        p.bonus_actions += 1
                        self.engine._log_event(run, "💎 [神圣白钻] 触发，获得 1A 1BA！")
                    elif g == "gem_vuln_1":
                        if target and target.startswith("e"):
                            try:
                                idx = int(target[1:]) - 1
                                if idx < 0: idx = 0
                            except ValueError:
                                idx = 0
                            if idx < len(run.enemies):
                                self.engine.combat_resolver.add_buff_to(run.enemies[idx], "vulnerable", "易伤", "受到的伤害增加50%", 1)
                                self.engine._log_event(run, f"💎 [易伤尖晶石] 触发，对【{run.enemies[idx].name}】施加 1 层易伤！")
                    elif g == "gem_weak_2":
                        if target and target.startswith("e"):
                            try:
                                idx = int(target[1:]) - 1
                                if idx < 0: idx = 0
                            except ValueError:
                                idx = 0
                            if idx < len(run.enemies):
                                self.engine.combat_resolver.add_buff_to(run.enemies[idx], "weak", "虚弱", "造成的伤害减少50%", 2)
                                self.engine._log_event(run, f"💎 [虚弱玛瑙] 触发，对【{run.enemies[idx].name}】施加 2 层虚弱！")

            copy_count = 0
            if not cid.no_copy:
                if hasattr(card, "copy") and card.copy > 0:
                    copy_count = card.copy
                if hasattr(card, "gems") and card.gems and "gem_copy_1" in card.gems:
                    copy_count = max(copy_count, 1)
            if copy_count > 0:
                import copy
                copy_cid = copy.copy(cid)
                copy_cid.gems = [g for g in copy_cid.gems if g != "gem_copy_1"]
                copy_cid.no_copy = True
                max_hand = 9 if "mask_of_void" in p.relics else 12
                added = 0
                for _ in range(copy_count):
                    if len(p.hand) < max_hand:
                        p.hand.append(copy_cid)
                        added += 1
                if added > 0:
                    run.node_data["extra_copy_msg"] = f"\n✨ [复制] 【{card.name}】打出后往手牌中添加了 {added} 张复制品！"

            extra_msgs = run.node_data.pop("extra_play_msgs", [])
            if len(extra_msgs) > 10:
                res += f"x {len(extra_msgs)}次"
            else:
                res += "".join(extra_msgs)

            extra_return_msg = run.node_data.pop("extra_return_msg", "")
            if extra_return_msg:
                res += extra_return_msg
            extra_copy_msg = run.node_data.pop("extra_copy_msg", "")
            if extra_copy_msg:
                res += extra_copy_msg

            run.node_data["cards_played_this_turn"] = played_count + 1
            self.engine.save_manager.save_save(run.user_id, run)
        else:
            self.engine.save_manager.save_save(run.user_id, run)
            return self.engine._append_logs_to_res(run, res)
        has_damaged = False
        for idx, e in enumerate(run.enemies):
            if idx < len(initial_status):
                old_hp, old_shield = initial_status[idx]
                if e.hp < old_hp or e.shield < old_shield:
                    has_damaged = True
                    break
        if has_damaged and run.node_data.get("extra_turns_left", 0) > 0:
            end_turn_res = self.end_turn(run)
            res += f"\n⏳ [时间停止] 额外回合中对敌人造成了伤害，当前额外回合提前结束！\n{end_turn_res}"
        for enemy in run.enemies:
            self.engine._sync_enemy_intents(enemy)
        self._reindex_minions(p)
        return self.engine._append_logs_to_res(run, res)

    def play_special_action(self, run: GameRun, hand_idx: int, target: Optional[str] = None) -> str:
        initial_status = [(e.hp, e.shield) for e in run.enemies]
        p = run.player
        if run.node_type != "battle":
            return "❌ 只有在战斗中才能使用卡牌的特殊行动。"
        if hand_idx < 1 or hand_idx > len(p.hand):
            return "❌ 无效的手牌序号。"
        c_state = p.hand[hand_idx - 1]
        card = ALL_CARDS.get(c_state)
        if not card:
            return "❌ 卡牌不存在。"
        if getattr(card, "unplayable", False):
            return "❌ 该卡牌不能被打出。"
        
        req_a = card.cost_a
        req_ba = card.cost_ba
        real_x_a = 0
        real_x_ba = 0
        if req_a == -1:
            real_x_a = p.actions
            req_a = p.actions
        if req_ba == -1:
            real_x_ba = p.bonus_actions
            req_ba = p.bonus_actions

        if "chemical_x" in p.relics:
            if card.cost_a == -1:
                real_x_a += 2
            if card.cost_ba == -1:
                real_x_ba += 2

        run.node_data["last_x_cost_a"] = real_x_a
        run.node_data["last_x_cost_ba"] = real_x_ba

        if p.actions < req_a or p.bonus_actions < req_ba:
            return f"❌ 你的动作资源不足（需要 {req_a}A {req_ba}BA，当前 {p.actions}A {p.bonus_actions}BA）。"
        if target is None:
            p0_spells = {"first_aid", "get_ready", "adrenaline", "mana_potion", "mass_healing_word", "refresh_spirit", "shield", "misty_step", "arcane_intellect", "calculated_gamble", "time_warp", "time_stop", "archmage_wish"}
            if card.id in p0_spells:
                target = "p0"
            else:
                target = self.engine._get_first_alive_enemy(run)
        if target == "0" or target == "e0":
            target = "e1"
        elif target == "p":
            target = "p0"
        p.actions -= req_a
        p.bonus_actions -= req_ba
        p.hand.pop(hand_idx - 1)
        run.node_data["current_playing_card_cid"] = c_state
        self._handle_card_post_play(run, card, c_state, source="played")
        run.node_data["current_playing_card_id"] = card.id
        try:
            res = card.special_action(run, target)
        finally:
            run.node_data["current_playing_card_id"] = ""
            run.node_data["current_playing_card_cid"] = ""
        self.engine.save_manager.save_save(run.user_id, run)
        has_damaged = False
        for idx, e in enumerate(run.enemies):
            if idx < len(initial_status):
                old_hp, old_shield = initial_status[idx]
                if e.hp < old_hp or e.shield < old_shield:
                    has_damaged = True
                    break
        if has_damaged and run.node_data.get("extra_turns_left", 0) > 0:
            end_turn_res = self.end_turn(run)
            res += f"\n⏳ [时间停止] 额外回合中对敌人造成了伤害，当前额外回合提前结束！\n{end_turn_res}"
        for enemy in run.enemies:
            self.engine._sync_enemy_intents(enemy)
        self._reindex_minions(p)
        return self.engine._append_logs_to_res(run, res)

    def minion_attack(self, run: GameRun, my_grid: str, opp_grid: Optional[str] = None) -> str:
        initial_status = [(e.hp, e.shield) for e in run.enemies]
        p = run.player
        if run.node_type != "battle":
            return "❌ 只有在战斗中才能控制随从攻击。"
        if my_grid not in p.minions:
            return f"❌ 我方格子 [{my_grid}] 没有随从。"
        m = p.minions[my_grid]
        if m.attack_actions < 1:
            return "❌ 该随从本回合已经没有可用的攻击动作（AA）点。"
        if opp_grid is None:
            opp_grid = self.engine._get_first_alive_enemy(run)
        m.attack_actions -= 1
        try:
            opp_idx = int(opp_grid.replace("e", "")) - 1
            if opp_idx < 0:
                opp_idx = 0
        except ValueError:
            opp_idx = 0
        if opp_idx < 0 or opp_idx >= len(run.enemies):
            return f"❌ 敌方格子 [{opp_grid}] 没有合法的敌人目标。"
        enemy = run.enemies[opp_idx]
        opp_grid = f"e{opp_idx+1}"
        self.engine._damage_target(run, opp_grid, m.atk, source=f"p{my_grid}", damage_type="bludgeoning")
        res = f"我方随从【{m.name}】攻击了敌人【{enemy.name}】。"
        self.engine.save_manager.save_save(run.user_id, run)
        has_damaged = False
        for idx, e in enumerate(run.enemies):
            if idx < len(initial_status):
                old_hp, old_shield = initial_status[idx]
                if e.hp < old_hp or e.shield < old_shield:
                    has_damaged = True
                    break
        if has_damaged and run.node_data.get("extra_turns_left", 0) > 0:
            end_turn_res = self.end_turn(run)
            res += f"\n⏳ [时间停止] 额外回合中对敌人造成了伤害，当前额外回合提前结束！\n{end_turn_res}"
        for enemy in run.enemies:
            self.engine._sync_enemy_intents(enemy)
        self._reindex_minions(p)
        return self.engine._append_logs_to_res(run, res)

    def minion_skill(self, run: GameRun, my_grid: str, skill_idx: int = 1, target: Optional[str] = None) -> str:
        initial_status = [(e.hp, e.shield) for e in run.enemies]
        p = run.player
        if run.node_type != "battle":
            return "❌ 只有在战斗中才能发动随从技能。"
        if my_grid not in p.minions:
            return f"❌ 我方格子 [{my_grid}] 没有随从。"
        m = p.minions[my_grid]
        if m.id not in ALL_MINIONS:
            return f"❌ 随从【{m.name}】没有任何可用技能。"
        template = ALL_MINIONS[m.id]
        skills_list = template.skills
        if skill_idx < 1 or skill_idx > len(skills_list):
            skills_desc = "\n".join([f" [{idx}] {s.name}: {s.desc}" for idx, s in enumerate(skills_list, 1)])
            return f"❌ 无效的技能序号。随从【{m.name}】的可用技能有：\n{skills_desc}"
        skill = skills_list[skill_idx - 1]
        cost_a = skill.cost_a
        cost_ba = skill.cost_ba
        if m.actions < cost_a or m.bonus_actions < cost_ba:
            return f"❌ 随从资源不足（需要 {cost_a}A {cost_ba}BA，当前 {m.actions}A {m.bonus_actions}BA）。"
        needs_target = False
        base_id = m.id.rstrip("+")
        if base_id == "mercenary" and skill_idx == 1:
            needs_target = True
        elif base_id == "shield_guard" and skill_idx == 2:
            needs_target = True
        elif base_id == "water_elemental" and skill_idx == 2:
            needs_target = True
        if needs_target:
            if target is None:
                target = self.engine._get_first_alive_enemy(run)
            if isinstance(target, str) and target.isdigit():
                target = f"e{target}"
            if target == "0" or target == "e0":
                target = "e1"
            if target.startswith("e"):
                try:
                    idx = int(target[1:]) - 1
                except ValueError:
                    idx = 0
                if idx < 0 or idx >= len(run.enemies):
                    return f"❌ 敌方目标 [{target}] 不存在。"
            else:
                return "❌ 无效的目标。该技能只能对敌方目标释放。"
        m.actions -= cost_a
        m.bonus_actions -= cost_ba
        msg = f"随从【{m.name}】发动了技能【{skill.name}】！"
        run.node_data["current_acting_minion_grid"] = my_grid
        try:
            effect_msg = skill.execute(run, my_grid, target, self.engine)
        finally:
            run.node_data.pop("current_acting_minion_grid", None)
        msg += effect_msg
        if "archmage_robe" in p.relics:
            self.engine.combat_resolver.gain_shield(run, "p0", 2)
            self.engine._log_event(run, "💎 [魔法师法袍] 触发！随从释放技能使玩家获得 2 点护盾！")
        self.engine.save_manager.save_save(run.user_id, run)
        has_damaged = False
        for idx, e in enumerate(run.enemies):
            if idx < len(initial_status):
                old_hp, old_shield = initial_status[idx]
                if e.hp < old_hp or e.shield < old_shield:
                    has_damaged = True
                    break
        if has_damaged and run.node_data.get("extra_turns_left", 0) > 0:
            end_turn_res = self.end_turn(run)
            msg += f"\n⏳ [时间停止] 额外回合中对敌人造成了伤害，当前额外回合提前结束！\n{end_turn_res}"
        for enemy in run.enemies:
            self.engine._sync_enemy_intents(enemy)
        self._reindex_minions(p)
        return self.engine._append_logs_to_res(run, msg)

    def end_turn(self, run: GameRun) -> str:
        if run.node_type != "battle":
            return "❌ 只有在战斗中才能结束回合。"
        p = run.player
        evt_end = TurnEndEvent(run, is_player=True)
        self.engine.event_bus.dispatch(evt_end)

        retained = []
        temp_retains = list(run.node_data.get("temp_retain_cards", []))
        for c_state in p.hand:
            card = ALL_CARDS.get(c_state)
            if card and (getattr(card, "retain", False) or (hasattr(card, "gems") and card.gems and "gem_retain" in card.gems)):
                retained.append(c_state)
            elif c_state in temp_retains:
                retained.append(c_state)
                temp_retains.remove(c_state)
            elif card and card.id == "curse_dimensional_tear":
                p.exhaust_pile.append(c_state)
                self.engine._log_event(run, f"💥 [空间撕裂] 手牌中的【{card.name}】在回合结束时发生坍缩，被消耗并对【{run.player.name}】造成 3 点真实伤害！")
                self.engine.combat_resolver.damage_target(run, "p0", 3, source="curse", damage_type="true")
                exhaust_evt = CardExhaustEvent(run, c_state, "curse_dimensional_tear")
                self.engine.event_bus.dispatch(exhaust_evt)
            elif card and getattr(card, "ethereal", False):
                p.exhaust_pile.append(c_state)
                self.engine._log_event(run, f"✨ [虚无] 【{card.name}】在回合结束时被消耗。")
                exhaust_evt = CardExhaustEvent(run, c_state, "ethereal")
                self.engine.event_bus.dispatch(exhaust_evt)
            else:
                p.discard_pile.append(c_state)
        p.hand = retained
        run.node_data["temp_retain_cards"] = []
        for ak, av in list(p.amulets.items()):
            base_id = av.id[:-1] if av.id.endswith("+") else av.id
            template = ALL_AMULETS.get(base_id)
            if template:
                template.on_end_turn(run, ak, self.engine)
            av.countdown -= 1
            if av.countdown <= 0:
                del p.amulets[ak]
                p.minion_graveyard.append(av.id)
                lw_msg = ""
                if template:
                    is_upgraded = av.id.endswith("+")
                    lw_msg = template.on_death(run, ak, is_upgraded, self.engine)
                if lw_msg:
                    self.engine._log_event(run, f"🔔 [谢幕曲] 我方【{av.name}】吟唱结束进入墓地：{lw_msg}")
                else:
                    self.engine._log_event(run, f"🔔 我方【{av.name}】吟唱结束进入墓地。")
        if self.engine.is_battle_won(run):
            self.handle_battle_win(run)
            self._reindex_minions(p)
            return self.engine._append_logs_to_res(run, "战斗胜利！敌方单位已被全部击败。")
        extra_turns = run.node_data.get("extra_turns_left", 0)
        if extra_turns > 0:
            run.node_data["extra_turns_left"] = extra_turns - 1
            enemy_actions = f"⏳ [时间停止] 额外回合进行中（剩余 {extra_turns - 1} 个额外回合），敌人全部陷入静止。"
        else:
            enemy_actions = self.engine._enemy_turn(run)
        if self.engine.is_battle_won(run):
            self.handle_battle_win(run)
            self._reindex_minions(p)
            return self.engine._append_logs_to_res(run, f"{enemy_actions}\n🎉 战斗胜利！敌方单位已被全部击败。")
        if p.hp <= 0:
            settle_msg = self.engine.save_manager.settle_game_and_delete(run.user_id, run, is_victory=False)
            return f"{enemy_actions}\n💀 冒险结束。你被击败了！存档已被清除。\n{settle_msg}"
        decay_msgs = []
        has_barricade = any(b.id.startswith("barricade") for b in p.buffs)
        if p.shield > 0 and not has_barricade:
            lost = p.shield - (p.shield // 2)
            p.shield = p.shield // 2
            if lost > 0:
                decay_msgs.append(f"【{p.name}】失去 {lost} 点护盾")
                from ...models.events import ShieldDecayEvent
                self.engine.event_bus.dispatch(ShieldDecayEvent(run, "p0", lost))
        elif p.shield > 0 and has_barricade:
            pass
        else:
            p.shield = 0
        decay_info = ""
        if decay_msgs:
            decay_info = "🛡️ 护盾流失：" + "，".join(decay_msgs) + "\n"
        p.actions = 2
        p.bonus_actions = 1
        evt_start = TurnStartEvent(run, is_player=True)
        self.engine.event_bus.dispatch(evt_start)
        if getattr(p, "subclass", "") == "时序法师":
            if random.random() < 0.25:
                p.bonus_actions += 1
                self.engine._log_event(run, "⏳ [时序被动] 触发时间跳跃，本回合额外获得 1 个附赠动作（BA）！")
        for mk, mv in p.minions.items():
            mv.actions += 1
            mv.attack_actions = 1
            if mv.id == "mercenary":
                mv.atk = 4
            elif mv.id == "mercenary+":
                mv.atk = 5
            elif mv.id == "arcane_golem":
                mv.atk = 6
            elif mv.id == "arcane_golem+":
                mv.atk = 8
        if run.enemies and any(e.name == "腐化之心" for e in run.enemies):
            run.node_data["heart_turn"] = run.node_data.get("heart_turn", 1) + 1
        if run.enemies and any(e.name == "Icerainboww" for e in run.enemies):
            run.node_data["icerainboww_turn"] = run.node_data.get("icerainboww_turn", 1) + 1
        if run.enemies and any(e.name == "雷霆领主" for e in run.enemies):
            run.node_data["thunder_lord_turn"] = run.node_data.get("thunder_lord_turn", 1) + 1
        draw_count = 6
        if run.node_data.get("draw_penalty_next_turn"):
            draw_count = max(0, draw_count - run.node_data["draw_penalty_next_turn"])
            run.node_data.pop("draw_penalty_next_turn", None)
        self.draw_cards(p, draw_count, run, ignore_focus=True)
        discard_buff = next((b for b in p.buffs if b.id == "discard_next_turn"), None)
        if discard_buff:
            count = discard_buff.stacks
            discarded_names = []
            for _ in range(count):
                if p.hand:
                    discarded = p.hand.pop(random.randint(0, len(p.hand) - 1))
                    card_name = ALL_CARDS[discarded].name if discarded in ALL_CARDS else "未知卡牌"
                    discarded_names.append(f"【{card_name}】")
                    self.engine._discard_card(run, discarded)
            p.buffs.remove(discard_buff)
            if discarded_names:
                self.engine._log_event(run, f"💨 [回合开始弃牌] 由于受到怪物的干扰，你被迫丢弃了手牌：{', '.join(discarded_names)}。")

        self.engine._roll_enemy_intent(run)
        run.node_data["cards_played_this_turn"] = 0
        run.node_data["action_surge_turn_used"] = False
        self._reindex_minions(p)
        run.node_data["turn_count"] = run.node_data.get("turn_count", 1) + 1
        self.engine.save_manager.save_save(run.user_id, run)
        return self.engine._append_logs_to_res(run, f"{enemy_actions}\n{decay_info}进入【{p.name}】回合。已重置动作并抽取手牌。")

    def handle_battle_win(self, run: GameRun):
        p = run.player
        p.buffs.clear()
        p.hp = min(p.max_hp, p.hp)
        evt_win = BattleWinEvent(run)
        self.engine.event_bus.dispatch(evt_win)
        if run.node_data.get("corpse_battle"):
            self.handle_corpse_win(run)
            return
        if run.node_data.get("is_town_combat"):
            self.engine.save_manager.save_save(run.user_id, run)
            return
        if run.node_data.get("no_reward"):
            run.node_type = "reward"
            run.node_data = {"cards": [], "no_reward": True}
            self.engine.save_manager.save_save(run.user_id, run)
            return
        difficulty = run.node_data.get("difficulty", "normal")
        quest = run.node_data.get("quest")
        quest_bonus = ""
        items = []
        if quest == "knight_cave":
            items.append({
                "type": "quest_card",
                "card_id": "shield_guard",
                "taken": False,
                "bind_group": "quest_knight_cave"
            })
            items.append({
                "type": "quest_relic",
                "relic_id": "heavy_armor",
                "taken": False,
                "bind_group": "quest_knight_cave"
            })
            quest_bonus = "\n🗡️ 任务完成！你帮奥术骑士夺回了长剑。作为谢礼，你获得了卡牌【盾卫】与遗物【重装甲片】！"
        elif quest == "maze_fight":
            got_relic = random.choice(["whetstone", "ready_pack", "arcane_rune"])
            items.append({
                "type": "relic",
                "relic_id": got_relic,
                "taken": False
            })
            quest_bonus = f"\n🔥 任务完成！你击败了火元素守卫，在石门后获得稀有遗物【{get_relic_name(got_relic)}】！"
        
        elite_relic_map = {
            "地精百夫长": "centurion_mail",
            "石像鬼祭司": "priest_charm",
            "狂暴兽王": "beastmaster_claw",
            "黑曜石巨灵": "djinn_shard",
            "幽灵大魔法师": "archmage_robe",
            "暗影影魔": "shadow_tentacle",
            "夺心魔": "mindflayer_brain",
            "末日守卫": "doomsday_core",
            "亡灵巫师": "necromancer_skull",
            "夺心魔奥术师": "arcanist_hand",
            "吉斯洋基至高指挥官": "commander_medal",
            "虚空潜伏者": "stalker_eye",
            "冷蛛": "leng_spider_venom",
            "米·戈": "migo_lightning_gun",
            "修格斯": "shoggoth_slime",
            "星之精": "star_vampire_proboscis",
            "克苏鲁之星之眷族": "starspawn_core"
        }
        
        if difficulty == "elite":
            reward_gold = 25 + random.randint(10, 20)
            elite_name = run.node_data.get("elite_name", "")
            if elite_name in elite_relic_map:
                rid = elite_relic_map[elite_name]
                if rid not in p.relics:
                    items.append({
                        "type": "relic",
                        "relic_id": rid,
                        "taken": False
                    })
                    quest_bonus += f"\n🏆 击败精英【{elite_name}】，获得了它的专属遗物：【{get_relic_name(rid)}】！"
        else:
            reward_gold = 10 + random.randint(5, 15)
            
        items.append({
            "type": "gold",
            "amount": reward_gold,
            "taken": False
        })
        
        potion_chance = 0.66 if difficulty == "elite" else 0.33
        if random.random() < potion_chance:
            from ...data.potion_data import roll_potion
            tmp_stats = self.engine.save_manager.load_stats(run.user_id)
            p_class = getattr(tmp_stats, "selected_class", "法师")
            pid = roll_potion(p_class)
            items.append({
                "type": "potion",
                "potion_id": pid,
                "taken": False
            })
        
        stats = self.engine.save_manager.load_stats(run.user_id)
        has_gatekey = getattr(stats, "unlocked_gatekey", False)
        if p.stage == MapConfig.FINAL_BOSS_STAGE:
            run.node_type = "victory"
            stats.yog_sothoth_kill_count = getattr(stats, "yog_sothoth_kill_count", 0) + 1
            self.engine.save_manager.save_stats(run.user_id, stats)
        elif p.stage == MapConfig.GATE_BOSS_STAGE and not has_gatekey:
            run.node_type = "victory"
            if run.node_data.get("boss_name") == "Icerainboww":
                stats.killed_icerainboww = True
                self.engine.save_manager.save_stats(run.user_id, stats)
        elif p.stage == MapConfig.GATE_BOSS_STAGE and has_gatekey:
            run.node_type = "boss_chest"
            p_class = getattr(stats, "selected_class", "法师")
            class_mythic_cards = ["neutral_plane_shift", "neutral_omega"]
            if getattr(stats, "yog_sothoth_kill_count", 0) > 0:
                class_mythic_cards.append("neutral_button_magic")
            if p_class == "战士":
                class_mythic_cards.append("warrior_hematopoiesis")
            else:
                class_mythic_cards.append("wizard_split_to_ten")
            
            mythic_relics = ["infinite_hourglass"]
            available_relics = [r for r in mythic_relics if r not in p.relics]
            
            options = []
            if available_relics:
                relic_choice = random.choice(available_relics)
                options.append({"type": "relic", "id": relic_choice})
            
            needed = 3 - len(options)
            chosen_cards = random.sample(class_mythic_cards, min(needed, len(class_mythic_cards)))
            for c in chosen_cards:
                options.append({"type": "card", "id": c})
                
            items = []
            for opt in options:
                items.append({
                    "type": "boss_relic" if opt["type"] == "relic" else "boss_card",
                    "id": opt["id"],
                    "taken": False,
                    "group_id": "boss_chest_group"
                })
            from ...models.events import RewardGenerateEvent
            evt = RewardGenerateEvent(run, items)
            self.engine.event_bus.dispatch(evt)
            run.node_data = {
                "title": "🏆 BOSS 战利品：神话宝箱",
                "desc": "你击败了第二阶段的守护者！在它的身后，一尊散发着七彩神圣微光的【神话宝箱】缓缓升起。\n请选择你要继承的一件神话秘宝：",
                "options": options,
                "items": items
            }
            self.engine.save_manager.save_save(run.user_id, run)
        else:
            run.node_type = "reward"
            card_pool = list(ALL_CARDS.keys())
            p_class = getattr(stats, "selected_class", "法师")
            target_color = "warrior" if p_class == "战士" else "wizard"
            from ...entities.cards.market import is_card_available
            normal_cards = [
                cid for cid in card_pool
                if ALL_CARDS[cid].rarity not in ("legendary", "mythic", "artifact")
                and not cid.startswith("curse_")
                and not cid.startswith("duel_")
                and ALL_CARDS[cid].color in (target_color, "neutral")
                and is_card_available(cid, stats)
            ]
            reward_cards = random.sample(normal_cards, 3)
            final_reward_cards = []
            for cid in reward_cards:
                cid = check_and_replace_fireball(run, cid)
                if p.subclass == "秘钥学者" and ALL_CARDS.get(cid) and ALL_CARDS[cid].color == "wizard" and ALL_CARDS[cid].rarity not in ("legendary", "mythic", "artifact"):
                    if random.random() < 0.35:
                        cid = "key_resonance"
                final_reward_cards.append(cid)
            
            items.append({
                "type": "card_reward",
                "cards": final_reward_cards,
                "taken": False,
                "force": False
            })
            
            pending_gems = run.node_data.get("pending_gems", [])
            if pending_gems:
                for gid in pending_gems:
                    items.append({
                        "type": "gem",
                        "gem_id": gid,
                        "taken": False
                    })
            
            from ...models.events import RewardGenerateEvent
            evt = RewardGenerateEvent(run, items)
            self.engine.event_bus.dispatch(evt)
            
            is_town = run.node_data.get("is_town_combat", False)
            npc_n = run.node_data.get("npc_name", "")
            run.node_data = {"items": items, "quest_bonus": quest_bonus}
            if is_town:
                run.node_data["is_town_combat"] = True
                run.node_data["npc_name"] = npc_n
            self.engine.save_manager.save_save(run.user_id, run)

    def handle_corpse_win(self, run: GameRun):
        corpse_id = run.node_data.get("corpse_id")
        dead_name = str(run.node_data.get("corpse_dead_name", "玩家"))
        cause = str(run.node_data.get("corpse_cause", "死因不明"))
        corpse = self.engine.save_manager.corpses.claim(corpse_id, run.user_id)
        map_engine = getattr(self.engine, "map_engine", None)
        if not corpse:
            if map_engine is not None:
                map_engine.return_to_map_select(run)
                run.node_data["notice"] = "❌ 这具尸体已经被其他玩家搜刮，尸体节点消失了。"
            else:
                run.node_type = "map_select"
                run.node_data = {}
            self.engine.save_manager.save_save(run.user_id, run)
            return
        gp_reward = int(corpse.get("gp_reward", 0))
        stats = self.engine.save_manager.load_stats(run.user_id)
        stats.gp += gp_reward
        self.engine.save_manager.save_stats(run.user_id, stats)
        deck = list(corpse.get("deck", []))
        cards = random.sample(deck, min(CorpseConfig.REWARD_CARD_POOL, len(deck))) if deck else []
        run.node_type = "corpse_reward"
        run.enemies.clear()
        run.node_data = {
            "corpse_reward": True,
            "corpse_id": corpse_id,
            "dead_name": dead_name,
            "cause": cause,
            "gp": gp_reward,
            "cards": cards,
            "picks_left": CorpseConfig.REWARD_CARD_PICKS,
            "picked": [],
            "notice": (
                f"你击败了【冤魂·{dead_name}】，从尸体中搜刮到 {gp_reward} GP。\n"
                f"死因：{cause}。你可以从死者卡组中挑选 {CorpseConfig.REWARD_CARD_PICKS} 张卡牌，每次都可以跳过。"
            ),
        }
        self.engine.save_manager.save_save(run.user_id, run)
        self.engine.save_manager.corpses.remove(corpse_id)

    def _reindex_minions(self, p: PlayerState):
        self.engine._reindex_minions(p)
