from ...models.state import Card
from ...data.locale_data import get_locale_text
from .registry import register_card
from .neutral_cards_base import (
    TacticalFocusCard,
    IronWillCard,
    MistyStepCard,
    ArcaneIntellectCard,
    CalculatedGambleCard,
    ManaPotionCard,
    MassHealingWordCard,
    RefreshSpiritCard,
    KeyResonanceCard,
    MasterKeyCard,
)

@register_card("unmined_gem")
class UnminedGemCard(Card):
    def execute(self, run, target, engine) -> str:
        import random
        from .base import ALL_CARDS
        if run.player.hand:
            idx = random.randint(0, len(run.player.hand) - 1)
            from ...models.state import ensure_card_state
            target_cid = ensure_card_state(run.player.hand[idx])
            val = getattr(self, "replay_amount", 4 if self.upgraded else 3)
            old_val = target_cid.replay
            new_val = old_val + val
            import copy
            new_cid = copy.copy(target_cid)
            new_cid.replay = new_val
            run.player.hand[idx] = new_cid
            card_name = ALL_CARDS.get(new_cid).name
            if old_val > 0:
                return get_locale_text("i18n_cards_neutral.neutral.cards.unmined_gem.result_stacked", name=self.name, card_name=card_name, val=val, new_val=new_val)
            else:
                return get_locale_text("i18n_cards_neutral.neutral.cards.unmined_gem.result", name=self.name, card_name=card_name, val=val)
        else:
            return get_locale_text("i18n_cards_neutral.neutral.cards.unmined_gem.result_empty", name=self.name)

@register_card("neutral_omega")
class NeutralOmegaCard(Card):
    def execute(self, run, target, engine) -> str:
        p = run.player
        import copy
        import random
        from .base import ALL_CARDS
        hand_copies = [copy.deepcopy(cid) for cid in p.hand]
        random.shuffle(hand_copies)
        
        for copy_cid in hand_copies:
            if engine.is_battle_won(run):
                break
            card_obj = ALL_CARDS.get(copy_cid)
            if not card_obj or getattr(card_obj, "unplayable", False):
                continue
            card_target = None
            if card_obj.type == "spell":
                if card_obj.target_type == "self":
                    card_target = "p0"
                else:
                    card_target = engine._get_first_alive_enemy(run)
            extra_res = engine._execute_card_effect(run, card_obj, card_target)
            from ...models.events import CardPlayedEvent
            played_evt = CardPlayedEvent(run, card_obj, card_target, extra_res, is_extra=True)
            engine.event_bus.dispatch(played_evt)
            run.node_data.setdefault("extra_play_msgs", []).append(get_locale_text("i18n_cards_neutral.neutral.cards.neutral_omega.extra_play", feedback=played_evt.feedback))
            if hasattr(card_obj, "execute_tags"):
                card_obj.execute_tags(run, card_target, engine)
                
        return get_locale_text("i18n_cards_neutral.neutral.cards.neutral_omega.result")

@register_card("neutral_power_word_kill")
class NeutralPowerWordKillCard(Card):
    def execute(self, run, target, engine) -> str:
        name = engine._get_target_name(run, target)
        target_enemy = None
        if target and target.startswith("e"):
            try:
                idx = int(target[1:]) - 1
                if 0 <= idx < len(run.enemies):
                    target_enemy = run.enemies[idx]
            except ValueError:
                pass
        
        threshold = getattr(self, "threshold", 100 if self.upgraded else 60)
        if target_enemy and target_enemy.hp < threshold:
            engine._damage_target(run, target, target_enemy.hp, damage_type="true", card=self)
            return get_locale_text("i18n_cards_neutral.neutral.cards.power_word_kill.success", target=name)
        
        if self.upgraded and target_enemy:
            fail_damage = getattr(self, "fail_damage", 40)
            engine._damage_target(run, target, fail_damage, damage_type="true", card=self)
            return get_locale_text("i18n_cards_neutral.neutral.cards.power_word_kill.upgraded_fail", target=name)
        
        return get_locale_text("i18n_cards_neutral.neutral.cards.power_word_kill.fail", threshold=threshold)

@register_card("neutral_power_word_stun")
class NeutralPowerWordStunCard(Card):
    def execute(self, run, target, engine) -> str:
        name = engine._get_target_name(run, target)
        target_enemy = None
        if target and target.startswith("e"):
            try:
                idx = int(target[1:]) - 1
                if 0 <= idx < len(run.enemies):
                    target_enemy = run.enemies[idx]
            except ValueError:
                pass
        
        threshold = getattr(self, "threshold", 150 if self.upgraded else 100)
        if target_enemy and target_enemy.hp < threshold:
            stun_turns = getattr(self, "buff_turns", 1)
            engine._add_buff_to(target_enemy, "stun", get_locale_text("i18n_cards_neutral.neutral.cards.power_word_stun.buff_name"), get_locale_text("i18n_cards_neutral.neutral.cards.power_word_stun.buff_desc"), stun_turns)
            return get_locale_text("i18n_cards_neutral.neutral.cards.power_word_stun.success", target=name)
        
        if self.upgraded and target_enemy:
            fail_damage = getattr(self, "fail_damage", 15)
            engine._damage_target(run, target, fail_damage, damage_type="force", card=self)
            target_enemy.actions = max(0, target_enemy.actions - 1)
            return get_locale_text("i18n_cards_neutral.neutral.cards.power_word_stun.upgraded_fail", target=name)
            
        return get_locale_text("i18n_cards_neutral.neutral.cards.power_word_stun.fail", threshold=threshold)

@register_card("neutral_power_word_pain")
class NeutralPowerWordPainCard(Card):
    def execute(self, run, target, engine) -> str:
        name = engine._get_target_name(run, target)
        target_enemy = None
        if target and target.startswith("e"):
            try:
                idx = int(target[1:]) - 1
                if 0 <= idx < len(run.enemies):
                    target_enemy = run.enemies[idx]
            except ValueError:
                pass
        
        threshold = getattr(self, "threshold", 180 if self.upgraded else 120)
        bleed_layers = getattr(self, "buff_stacks", 4 if self.upgraded else 3)
        weak_layers = getattr(self, "buff_turns", 3 if self.upgraded else 2)
        
        if target_enemy and target_enemy.hp < threshold:
            engine._add_buff_to(target_enemy, "bleed", get_locale_text("i18n_cards_neutral.neutral.cards.power_word_pain.bleed_name"), get_locale_text("i18n_cards_neutral.neutral.cards.power_word_pain.bleed_desc"), bleed_layers)
            engine._add_buff_to(target_enemy, "weak", get_locale_text("i18n_cards_neutral.neutral.cards.power_word_pain.weak_name"), get_locale_text("i18n_cards_neutral.neutral.cards.power_word_pain.weak_desc"), weak_layers)
            return get_locale_text("i18n_cards_neutral.neutral.cards.power_word_pain.success", target=name, bleed_layers=bleed_layers, weak_layers=weak_layers)
            
        if self.upgraded and target_enemy:
            fail_damage = getattr(self, "fail_damage", 12)
            engine._damage_target(run, target, fail_damage, damage_type="slashing", card=self)
            return get_locale_text("i18n_cards_neutral.neutral.cards.power_word_pain.upgraded_fail", target=name)
            
        return get_locale_text("i18n_cards_neutral.neutral.cards.power_word_pain.fail", threshold=threshold)

@register_card("neutral_plane_shift")
class NeutralPlaneShiftCard(Card):
    def execute(self, run, target, engine) -> str:
        forbidden_stages = getattr(self, "forbidden_stages", (32,) if self.upgraded else (25, 32))
        if run.player.stage in forbidden_stages:
            return get_locale_text("i18n_cards_neutral.neutral.cards.plane_shift.forbidden")
        
        run.enemies.clear()
        if self.upgraded:
            gp_reward = getattr(self, "gp_reward", 40)
            run.player.gp += gp_reward
            return get_locale_text("i18n_cards_neutral.neutral.cards.plane_shift.result_upgraded")
        else:
            run.node_data["no_reward"] = True
            return get_locale_text("i18n_cards_neutral.neutral.cards.plane_shift.result")

@register_card("neutral_emperor_eye")
class NeutralEmperorEyeCard(Card):
    def execute(self, run, target, engine) -> str:
        p = run.player
        if target is not None:
            try:
                keep_idx = int(target)
                hand_idx = run.node_data.get("current_playing_card_hand_idx", 0) + 1
                if keep_idx == hand_idx:
                    return get_locale_text("i18n_cards_neutral.neutral.cards.emperor_eye.self_selected")
                if keep_idx < hand_idx:
                    remaining_idx = keep_idx - 1
                else:
                    remaining_idx = keep_idx - 2
                if 0 <= remaining_idx < len(p.hand):
                    return engine.execute_emperor_eye_resolve(run, remaining_idx, self.upgraded)
                else:
                    return get_locale_text("i18n_cards_neutral.neutral.cards.emperor_eye.out_of_range", keep_idx=keep_idx, hand_count=len(p.hand) + 1)
            except ValueError:
                return get_locale_text("i18n_cards_neutral.neutral.cards.emperor_eye.invalid_arg")
        if not p.hand:
            return engine.execute_emperor_eye_resolve(run, -1, self.upgraded)
        run.node_data.setdefault("state_stack", []).append({
            "type": "overload_star_select",
            "upgraded": self.upgraded
        })
        from .base import ALL_CARDS
        hand_list = "\n".join(f"{i+1}. {ALL_CARDS[c].name}" for i, c in enumerate(p.hand))
        return get_locale_text("i18n_cards_neutral.neutral.cards.emperor_eye.prompt", hand_list=hand_list)

@register_card("neutral_astral_strike")
class AstralStrikeCard(Card):
    def execute(self, run, target, engine) -> str:
        p = run.player
        dmg = getattr(self, "base_dmg", 32 if self.upgraded else 24)
        if not target:
            target = "e1"
        if not target.startswith("e"):
            return get_locale_text("i18n_cards_neutral.neutral.cards.astral_strike.invalid_target")
        res = engine.combat_resolver.damage_target(run, target, dmg, source="p0", damage_type="force", card=self)
        return get_locale_text("i18n_cards_neutral.neutral.cards.astral_strike.result", res=res)

@register_card("neutral_hero_anthem")
class HeroAnthemCard(Card):
    def execute(self, run, target, engine) -> str:
        p = run.player
        shield = getattr(self, "shield_amount", 10 if self.upgraded else 6)
        draw_count = getattr(self, "draw_count", 1)
        engine._gain_shield(run, "p0", shield)
        engine._draw_cards(p, draw_count, run)
        return get_locale_text("i18n_cards_neutral.neutral.cards.hero_anthem.result", shield=shield)

@register_card("elder_guidance")
class ElderGuidanceCard(Card):
    def execute(self, run, target, engine) -> str:
        p = run.player
        resonance_stacks = getattr(self, "buff_stacks", 1)
        engine._add_buff_to(p, "all_resonance", get_locale_text("i18n_cards_neutral.neutral.buffs.all_resonance.name"), get_locale_text("i18n_cards_neutral.neutral.buffs.all_resonance.desc"), resonance_stacks)
        removed = []
        for b in list(p.buffs):
            from ..buffs import is_debuff
            if is_debuff(b.id):
                p.buffs.remove(b)
                removed.append(b.name)
        draw_count = getattr(self, "draw_count", 3)
        engine._draw_cards(p, draw_count, run)
        clean_msg = get_locale_text("i18n_cards_neutral.neutral.cards.elder_guidance.cleanse", removed="、".join(removed)) if removed else ""
        return get_locale_text("i18n_cards_neutral.neutral.cards.elder_guidance.result", clean_msg=clean_msg)

@register_card("ironclad_rampart")
class IroncladRampartCard(Card):
    def execute(self, run, target, engine) -> str:
        p = run.player
        resonance_stacks = getattr(self, "buff_stacks", 1)
        shield_amount = getattr(self, "shield_amount", 30)
        dmg = getattr(self, "base_dmg", 15)
        engine._add_buff_to(p, "all_resonance", get_locale_text("i18n_cards_neutral.neutral.buffs.all_resonance.name"), get_locale_text("i18n_cards_neutral.neutral.buffs.all_resonance.desc"), resonance_stacks)
        engine._gain_shield(run, "p0", shield_amount)
        if not target or not target.startswith("e"):
            if run.enemies:
                target = "e1"
            else:
                return get_locale_text("i18n_cards_neutral.neutral.cards.ironclad_rampart.no_target")
        before_len = len(run.node_data.get("battle_logs", []))
        engine._damage_target(run, target, dmg, damage_type="bludgeoning", card=self)
        after_logs = run.node_data.get("battle_logs", [])
        dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
        return get_locale_text("i18n_cards_neutral.neutral.cards.ironclad_rampart.result", dmg_msg=dmg_msg)

@register_card("neutral_button_magic")
class NeutralButtonMagicCard(Card):
    def _effect_param(self, key, default):
        return (getattr(self, "effect_params", {}) or {}).get(key, default)

    def execute(self, run, target, engine) -> str:
        X = run.node_data.get("last_x_cost_a", 0)
        bonus_x = getattr(self, "hit_count", 2)
        X_eff = X + bonus_x if self.upgraded else X
        max_count = getattr(self, "max_count", 10)
        if X_eff > max_count:
            X_eff = max_count
        if X_eff <= 0:
            return get_locale_text("i18n_cards_neutral.neutral.cards.button_magic.no_effect")
            
        import random
        from ...models.state import ensure_card_state
        from ...entities import ALL_CARDS
        
        logs = []
        
        if not self.upgraded:
            def eff1():
                for e in run.enemies:
                    e.hp = self._effect_param("base_enemy_hp", 1)
                return get_locale_text("i18n_cards_neutral.neutral.cards.button_magic.eff1")
            
            def eff2():
                self_damage = self._effect_param("base_self_damage", 10)
                engine._damage_target(run, "p0", self_damage, damage_type="true", card=self)
                return get_locale_text("i18n_cards_neutral.neutral.cards.button_magic.eff2")
            
            def eff3():
                divisor = self._effect_param("base_hp_divisor", 2)
                for e in run.enemies:
                    e.max_hp = max(1, e.max_hp // divisor)
                    if e.hp > e.max_hp:
                        e.hp = e.max_hp
                return get_locale_text("i18n_cards_neutral.neutral.cards.button_magic.eff3")
            
            def eff4():
                shield_amount = self._effect_param("base_shield", 30)
                buffer_stacks = self._effect_param("base_buffer", 5)
                engine._gain_shield(run, "p0", shield_amount)
                engine._add_buff_to(run.player, "buffer", get_locale_text("i18n_cards_neutral.neutral.buffs.buffer.name"), get_locale_text("i18n_cards_neutral.neutral.buffs.buffer.desc"), buffer_stacks)
                return get_locale_text("i18n_cards_neutral.neutral.cards.button_magic.eff4")
            
            def eff5():
                shield_amount = self._effect_param("base_enemy_shield", 30)
                strength_stacks = self._effect_param("base_enemy_strength", 2)
                buffer_stacks = self._effect_param("base_enemy_buffer", 2)
                for idx in range(len(run.enemies)):
                    engine._gain_shield(run, f"e{idx+1}", shield_amount)
                    engine._add_buff_to(run.enemies[idx], "strength", get_locale_text("i18n_cards_neutral.neutral.buffs.strength.name"), get_locale_text("i18n_cards_neutral.neutral.buffs.strength.desc"), strength_stacks)
                    engine._add_buff_to(run.enemies[idx], "buffer", get_locale_text("i18n_cards_neutral.neutral.buffs.buffer.name"), get_locale_text("i18n_cards_neutral.neutral.buffs.buffer.desc"), buffer_stacks)
                return get_locale_text("i18n_cards_neutral.neutral.cards.button_magic.eff5")
            
            def eff6():
                strength_stacks = self._effect_param("base_player_strength", 5)
                double_tap_stacks = self._effect_param("base_player_double_tap", 2)
                engine._add_buff_to(run.player, "strength", get_locale_text("i18n_cards_neutral.neutral.buffs.strength.name"), get_locale_text("i18n_cards_neutral.neutral.buffs.strength.desc"), strength_stacks)
                engine._add_buff_to(run.player, "double_tap_buff", get_locale_text("i18n_cards_neutral.neutral.buffs.double_tap.name"), get_locale_text("i18n_cards_neutral.neutral.buffs.double_tap.desc"), double_tap_stacks)
                return get_locale_text("i18n_cards_neutral.neutral.cards.button_magic.eff6")
            
            def eff7():
                weak_stacks = self._effect_param("base_player_weak", 3)
                vulnerable_stacks = self._effect_param("base_player_vulnerable", 3)
                engine._add_buff_to(run.player, "weak", get_locale_text("i18n_cards_neutral.neutral.buffs.weak.name"), get_locale_text("i18n_cards_neutral.neutral.buffs.weak.desc"), weak_stacks)
                engine._add_buff_to(run.player, "vulnerable", get_locale_text("i18n_cards_neutral.neutral.buffs.vulnerable.name"), get_locale_text("i18n_cards_neutral.neutral.buffs.vulnerable.desc"), vulnerable_stacks)
                return get_locale_text("i18n_cards_neutral.neutral.cards.button_magic.eff7")
            
            def eff8():
                draw_count = self._effect_param("base_draw", 5)
                gain_a = self._effect_param("base_gain_a", 2)
                gain_ba = self._effect_param("base_gain_ba", 2)
                engine._draw_cards(run.player, draw_count, run)
                run.player.actions += gain_a
                run.player.bonus_actions += gain_ba
                return get_locale_text("i18n_cards_neutral.neutral.cards.button_magic.eff8")
            
            def eff9():
                free_grid = engine._get_free_grid(run.player)
                if free_grid is not None:
                    minion_hp = self._effect_param("base_minion_hp", 30)
                    minion_atk = self._effect_param("base_minion_atk", 6)
                    engine._summon_minion(run, "gate_guard", get_locale_text("i18n_cards_neutral.neutral.cards.button_magic.gate_guard_name"), minion_hp, minion_atk, 0)
                    return get_locale_text("i18n_cards_neutral.neutral.cards.button_magic.eff9")
                else:
                    return get_locale_text("i18n_cards_neutral.neutral.cards.button_magic.eff9_full")
            
            def eff10():
                p = run.player
                old_shield = p.shield
                p.shield = 0
                lost = old_shield
                min_damage = self._effect_param("base_lost_min_damage", 10)
                lost_multiplier = self._effect_param("base_lost_multiplier", 1)
                dmg = max(min_damage, lost * lost_multiplier)
                engine._damage_target(run, "p0", dmg, damage_type="true", card=self)
                return get_locale_text("i18n_cards_neutral.neutral.cards.button_magic.eff10", dmg=dmg)
            
            effects_pool = [eff1, eff2, eff3, eff4, eff5, eff6, eff7, eff8, eff9, eff10]
            
        else:
            def eff1():
                for e in run.enemies:
                    e.hp = self._effect_param("up_enemy_hp", 1)
                double_tap_stacks = self._effect_param("up_double_tap", 3)
                engine._add_buff_to(run.player, "double_tap_buff", get_locale_text("i18n_cards_neutral.neutral.buffs.double_tap.name"), get_locale_text("i18n_cards_neutral.neutral.buffs.double_tap.desc"), double_tap_stacks)
                return get_locale_text("i18n_cards_neutral.neutral.cards.button_magic.eff11")
            
            def eff2():
                self_damage = self._effect_param("up_self_damage", 5)
                engine._damage_target(run, "p0", self_damage, damage_type="true", card=self)
                return get_locale_text("i18n_cards_neutral.neutral.cards.button_magic.eff12")
            
            def eff3():
                divisor = self._effect_param("up_hp_divisor", 4)
                for e in run.enemies:
                    e.max_hp = max(1, e.max_hp // divisor)
                    if e.hp > e.max_hp:
                        e.hp = e.max_hp
                return get_locale_text("i18n_cards_neutral.neutral.cards.button_magic.eff13")
            
            def eff4():
                shield_amount = self._effect_param("up_shield", 60)
                buffer_stacks = self._effect_param("up_buffer", 10)
                engine._gain_shield(run, "p0", shield_amount)
                engine._add_buff_to(run.player, "buffer", get_locale_text("i18n_cards_neutral.neutral.buffs.buffer.name"), get_locale_text("i18n_cards_neutral.neutral.buffs.buffer.desc"), buffer_stacks)
                return get_locale_text("i18n_cards_neutral.neutral.cards.button_magic.eff14")
            
            def eff5():
                shield_amount = self._effect_param("up_enemy_shield", 60)
                strength_stacks = self._effect_param("up_enemy_strength", 4)
                buffer_stacks = self._effect_param("up_enemy_buffer", 4)
                for idx in range(len(run.enemies)):
                    engine._gain_shield(run, f"e{idx+1}", shield_amount)
                    engine._add_buff_to(run.enemies[idx], "strength", get_locale_text("i18n_cards_neutral.neutral.buffs.strength.name"), get_locale_text("i18n_cards_neutral.neutral.buffs.strength.desc"), strength_stacks)
                    engine._add_buff_to(run.enemies[idx], "buffer", get_locale_text("i18n_cards_neutral.neutral.buffs.buffer.name"), get_locale_text("i18n_cards_neutral.neutral.buffs.buffer.desc"), buffer_stacks)
                return get_locale_text("i18n_cards_neutral.neutral.cards.button_magic.eff15")
            
            def eff6():
                strength_stacks = self._effect_param("up_player_strength", 10)
                double_tap_stacks = self._effect_param("up_player_double_tap", 5)
                engine._add_buff_to(run.player, "strength", get_locale_text("i18n_cards_neutral.neutral.buffs.strength.name"), get_locale_text("i18n_cards_neutral.neutral.buffs.strength.desc"), strength_stacks)
                engine._add_buff_to(run.player, "double_tap_buff", get_locale_text("i18n_cards_neutral.neutral.buffs.double_tap.name"), get_locale_text("i18n_cards_neutral.neutral.buffs.double_tap.desc"), double_tap_stacks)
                return get_locale_text("i18n_cards_neutral.neutral.cards.button_magic.eff16")
            
            def eff7():
                weak_stacks = self._effect_param("up_player_weak", 5)
                vulnerable_stacks = self._effect_param("up_player_vulnerable", 5)
                engine._add_buff_to(run.player, "weak", get_locale_text("i18n_cards_neutral.neutral.buffs.weak.name"), get_locale_text("i18n_cards_neutral.neutral.buffs.weak.desc"), weak_stacks)
                engine._add_buff_to(run.player, "vulnerable", get_locale_text("i18n_cards_neutral.neutral.buffs.vulnerable.name"), get_locale_text("i18n_cards_neutral.neutral.buffs.vulnerable.desc"), vulnerable_stacks)
                return get_locale_text("i18n_cards_neutral.neutral.cards.button_magic.eff17")
            
            def eff8():
                draw_count = self._effect_param("up_draw", 8)
                gain_a = self._effect_param("up_gain_a", 5)
                gain_ba = self._effect_param("up_gain_ba", 5)
                engine._draw_cards(run.player, draw_count, run)
                run.player.actions += gain_a
                run.player.bonus_actions += gain_ba
                return get_locale_text("i18n_cards_neutral.neutral.cards.button_magic.eff18")
            
            def eff9():
                free_grid_1 = engine._get_free_grid(run.player)
                summoned = 0
                minion_hp = self._effect_param("up_minion_hp", 45)
                minion_atk = self._effect_param("up_minion_atk", 8)
                if free_grid_1 is not None:
                    engine._summon_minion(run, "gate_guard+", get_locale_text("i18n_cards_neutral.neutral.cards.button_magic.gate_guard_upgraded_name"), minion_hp, minion_atk, 0)
                    summoned += 1
                    free_grid_2 = engine._get_free_grid(run.player)
                    if free_grid_2 is not None:
                        engine._summon_minion(run, "gate_guard+", get_locale_text("i18n_cards_neutral.neutral.cards.button_magic.gate_guard_upgraded_name"), minion_hp, minion_atk, 0)
                        summoned += 1
                if summoned == 2:
                    return get_locale_text("i18n_cards_neutral.neutral.cards.button_magic.eff19")
                elif summoned == 1:
                    return get_locale_text("i18n_cards_neutral.neutral.cards.button_magic.eff20")
                else:
                    return get_locale_text("i18n_cards_neutral.neutral.cards.button_magic.eff21")
            
            def eff10():
                p = run.player
                old_shield = p.shield
                p.shield = 0
                lost = old_shield
                min_damage = self._effect_param("up_lost_min_damage", 30)
                lost_multiplier = self._effect_param("up_lost_multiplier", 2)
                dmg = max(min_damage, lost * lost_multiplier)
                engine._damage_target(run, "p0", dmg, damage_type="true", card=self)
                return get_locale_text("i18n_cards_neutral.neutral.cards.button_magic.eff22", dmg=dmg)
                
            def eff11():
                force_damage = self._effect_param("up_force_damage", 99)
                buffer_stacks = self._effect_param("up_force_buffer", 3)
                for idx in range(len(run.enemies) - 1, -1, -1):
                    engine._damage_target(run, f"e{idx+1}", force_damage, damage_type="force", card=self)
                engine._add_buff_to(run.player, "buffer", get_locale_text("i18n_cards_neutral.neutral.buffs.buffer.name"), get_locale_text("i18n_cards_neutral.neutral.buffs.buffer.desc"), buffer_stacks)
                return get_locale_text("i18n_cards_neutral.neutral.cards.button_magic.eff23")
                
            def eff12():
                draw_count = self._effect_param("up_time_draw", 5)
                gain_a = self._effect_param("up_time_gain_a", 3)
                gain_ba = self._effect_param("up_time_gain_ba", 3)
                engine._draw_cards(run.player, draw_count, run)
                run.player.actions += gain_a
                run.player.bonus_actions += gain_ba
                return get_locale_text("i18n_cards_neutral.neutral.cards.button_magic.eff24")
                
            def eff13():
                p = run.player
                lost_hand_count = len(p.hand)
                p.hand.clear()
                removed_names = []
                remove_count = self._effect_param("up_remove_count", 2)
                non_mythic_deck_cards = [c for c in p.deck if getattr(ALL_CARDS.get(ensure_card_state(c).id), "rarity", "common") != "mythic"]
                if len(non_mythic_deck_cards) >= remove_count:
                    to_remove = random.sample(non_mythic_deck_cards, remove_count)
                else:
                    to_remove = non_mythic_deck_cards
                for c in to_remove:
                    if c in p.deck:
                        p.deck.remove(c)
                        card_name = getattr(ALL_CARDS.get(ensure_card_state(c).id), "name", str(c))
                        removed_names.append(card_name)
                removed_str = "、".join(removed_names) if removed_names else get_locale_text("i18n_cards_neutral.neutral.cards.button_magic.no_removed")
                return get_locale_text("i18n_cards_neutral.neutral.cards.button_magic.eff25", lost_hand_count=lost_hand_count, removed_str=removed_str)
                
            def eff14():
                p = run.player
                true_damage = self._effect_param("up_doom_damage", 999)
                for idx in range(len(run.enemies) - 1, -1, -1):
                    engine._damage_target(run, f"e{idx+1}", true_damage, damage_type="true", card=self)
                for grid in list(p.minions.keys()):
                    engine._damage_target(run, f"p{grid}", true_damage, damage_type="true", card=self)
                return get_locale_text("i18n_cards_neutral.neutral.cards.button_magic.eff26")
                
            def eff15():
                p = run.player
                hp_multiplier = self._effect_param("up_hp_multiplier", 2)
                shield_amount = self._effect_param("up_truth_shield", 100)
                p.max_hp = p.max_hp * hp_multiplier
                p.hp = p.hp * hp_multiplier
                engine._gain_shield(run, "p0", shield_amount)
                return get_locale_text("i18n_cards_neutral.neutral.cards.button_magic.eff27", max_hp=p.max_hp)
                
            effects_pool = [eff1, eff2, eff3, eff4, eff5, eff6, eff7, eff8, eff9, eff10, eff11, eff12, eff13, eff14, eff15]
            
        for i in range(X_eff):
            eff_fn = random.choice(effects_pool)
            res = eff_fn()
            logs.append(get_locale_text("i18n_cards_neutral.neutral.cards.button_magic.log_line", index=i+1, result=res))
            
        return get_locale_text("i18n_cards_neutral.neutral.cards.button_magic.result_prefix") + "\n".join(logs)
