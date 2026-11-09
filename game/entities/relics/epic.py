import re
from ...data.relic_data import RELIC_CONFIG
from ...data.locale_data import get_locale_text
from .base import RelicImpl
from .registry import register_relic

class AncientPageRelic(RelicImpl):
    def __init__(self, relic_id: str):
        super().__init__(relic_id)
        cfg = RELIC_CONFIG.get(relic_id, {})
        self.hp_loss = cfg.get("hp_loss", 4)
        self.spark_count = cfg.get("spark_count", 2)
        self.max_hand = cfg.get("max_hand", 12)
        self.void_mask_max_hand = cfg.get("void_mask_max_hand", 9)

    def on_battle_start(self, run, engine):
        p = run.player
        loss = min(self.hp_loss, p.hp - 1) if p.hp > 1 else 0
        if loss > 0:
            engine._damage_target(run, "p0", loss, source="self", damage_type="true")
        engine._log_event(run, get_locale_text("i18n_relics_amulets.epic.ancient_page.hp_loss", hp_loss=self.hp_loss))
        max_hand = self.void_mask_max_hand if "mask_of_void" in p.relics else self.max_hand
        spark_added = 0
        from ...core.deck_service import DeckService
        for _ in range(self.spark_count):
            if len(p.hand) < max_hand:
                DeckService.add_card_to_hand(p, "arcane_spark")
                spark_added += 1
        if spark_added > 0:
            engine._log_event(run, get_locale_text("i18n_relics_amulets.epic.ancient_page.add_sparks", spark_added=spark_added))

class HeavyArmorRelic(RelicImpl):
    def __init__(self, relic_id: str):
        super().__init__(relic_id)
        cfg = RELIC_CONFIG.get(relic_id, {})
        self.shield_gain = cfg.get("shield_gain", 8)

    def on_battle_start(self, run, engine):
        engine._gain_shield(run, "p0", self.shield_gain)
        engine._log_event(run, get_locale_text("i18n_relics_amulets.epic.heavy_armor.trigger", shield_gain=self.shield_gain))

class GreedyContractRelic(RelicImpl):
    def __init__(self, relic_id: str):
        super().__init__(relic_id)
        cfg = RELIC_CONFIG.get(relic_id, {})
        self.hp_loss = cfg.get("hp_loss", 3)

    def on_battle_start(self, run, engine):
        loss = min(self.hp_loss, run.player.hp - 1) if run.player.hp > 1 else 0
        if loss > 0:
            engine._damage_target(run, "p0", loss, source="self", damage_type="true")
        engine._log_event(run, get_locale_text("i18n_relics_amulets.epic.greedy_contract.trigger", hp_loss=self.hp_loss))

class AncientEyeRelic(RelicImpl):
    def __init__(self, relic_id: str):
        super().__init__(relic_id)
        cfg = RELIC_CONFIG.get(relic_id, {})
        self.draw_bonus = cfg.get("draw_bonus", 2)

    def on_battle_start(self, run, engine):
        engine._log_event(run, get_locale_text("i18n_relics_amulets.epic.ancient_eye.trigger", draw_bonus=self.draw_bonus))

    def modify_initial_draw(self, run, draw_count: int, engine) -> int:
        return draw_count + self.draw_bonus

class DragonBloodRelic(RelicImpl):
    def __init__(self, relic_id: str):
        super().__init__(relic_id)
        cfg = RELIC_CONFIG.get(relic_id, {})
        self.heal_amount = cfg.get("heal_amount", 5)

    def on_battle_win(self, run, engine):
        engine._heal_target(run, "p0", self.heal_amount)
        engine._log_event(run, get_locale_text("i18n_relics_amulets.epic.dragon_blood.trigger", heal_amount=self.heal_amount))

class UnstableCrystalRelic(RelicImpl):
    def __init__(self, relic_id: str):
        super().__init__(relic_id)
        cfg = RELIC_CONFIG.get(relic_id, {})
        self.spell_dmg_bonus = cfg.get("spell_dmg_bonus", 1)
        self.turn_ba_bonus = cfg.get("turn_ba_bonus", 1)
        self.recoil_damage = cfg.get("recoil_damage", 1)

    def on_damage_calculate(self, event, run, engine):
        is_spell = getattr(event.card, "type", "") == "spell" if event.card is not None else event.damage_type == "spell"
        if is_spell and event.source == "p0":
            event.modified_damage += self.spell_dmg_bonus

    def on_turn_start(self, event, run, engine):
        if event.is_player:
            run.player.bonus_actions += self.turn_ba_bonus

    def on_card_played(self, event, run, engine):
        if event.card.type == "spell":
            engine._damage_target(run, "p0", self.recoil_damage)
            engine._log_event(run, get_locale_text("i18n_relics_amulets.epic.unstable_crystal.trigger", recoil_damage=self.recoil_damage))

class VampiricTouchRelic(RelicImpl):
    def __init__(self, relic_id: str):
        super().__init__(relic_id)
        cfg = RELIC_CONFIG.get(relic_id, {})
        self.heal_amount = cfg.get("heal_amount", 1)

    def on_card_played(self, event, run, engine):
        if event.card.type == "spell" and event.card.id in (
            "dagger_throw", "fire_bolt", "fireball", "thunderwave",
            "magic_missile", "quick_strike", "arcane_spark", "doomsday_judgment", "meteor_swarm"
        ):
            old_hp = run.player.hp
            engine._heal_target(run, "p0", self.heal_amount)
            if run.player.hp > old_hp:
                engine._log_event(run, get_locale_text("i18n_relics_amulets.epic.vampiric_touch.trigger", heal_amount=self.heal_amount))

class MarkOfFuryRelic(RelicImpl):
    def __init__(self, relic_id: str):
        super().__init__(relic_id)
        cfg = RELIC_CONFIG.get(relic_id, {})
        self.spell_bonus = cfg.get("spell_bonus", 2)

    def on_damage_calculate(self, event, run, engine):
        is_spell = getattr(event.card, "type", "") == "spell" if event.card is not None else event.damage_type == "spell"
        if is_spell and event.source == "p0":
            event.modified_damage += self.spell_bonus

class EnergyCoreRelic(RelicImpl):
    def __init__(self, relic_id: str):
        super().__init__(relic_id)
        cfg = RELIC_CONFIG.get(relic_id, {})
        self.action_bonus = cfg.get("action_bonus", 1)

    def on_turn_start(self, event, run, engine):
        if event.is_player:
            run.player.actions += self.action_bonus

class PortalFragmentRelic(RelicImpl):
    def __init__(self, relic_id: str):
        super().__init__(relic_id)
        cfg = RELIC_CONFIG.get(relic_id, {})
        self.max_hand = cfg.get("max_hand", 12)
        self.void_mask_max_hand = cfg.get("void_mask_max_hand", 9)

    def on_battle_start(self, run, engine):
        import random
        p = run.player
        max_hand = self.void_mask_max_hand if "mask_of_void" in p.relics else self.max_hand
        if len(p.hand) < max_hand:
            chosen = random.choice(["key_resonance", "gate_guard", "master_key", "void_beacon", "ancient_wisdom"])
            p.hand.append(chosen)
            from ...data.card_data import CARD_CONFIG
            name = CARD_CONFIG.get(chosen, {}).get("name", chosen)
            engine._log_event(run, get_locale_text("i18n_relics_amulets.epic.portal_fragment.trigger", name=name))

class AncientKeyringRelic(RelicImpl):
    pass

class AbyssGazeRelic(RelicImpl):
    def __init__(self, relic_id: str):
        super().__init__(relic_id)
        cfg = RELIC_CONFIG.get(relic_id, {})
        self.spell_bonus = cfg.get("spell_bonus", 4)
        self.recoil_damage = cfg.get("recoil_damage", 2)

    def on_damage_calculate(self, event, run, engine):
        if event.damage_type == "spell" and event.source == "p0":
            event.modified_damage += self.spell_bonus

    def on_damage_take(self, event, run, engine):
        if event.target == "p0" and event.amount > 0 and event.source != "abyss_gaze":
            engine._damage_target(run, "p0", self.recoil_damage, source="abyss_gaze", damage_type="true")
            engine._log_event(run, get_locale_text("i18n_relics_amulets.epic.abyss_gaze.trigger"))

class GlacierArmorRelic(RelicImpl):
    def __init__(self, relic_id: str):
        super().__init__(relic_id)
        cfg = RELIC_CONFIG.get(relic_id, {})
        self.shield_gain = cfg.get("shield_gain", 12)

    def on_battle_start(self, run, engine):
        engine._gain_shield(run, "p0", self.shield_gain)
        engine._log_event(run, get_locale_text("i18n_relics_amulets.epic.glacier_armor.trigger"))

class AbyssWhisperRelic(RelicImpl):
    def __init__(self, relic_id: str):
        super().__init__(relic_id)
        cfg = RELIC_CONFIG.get(relic_id, {})
        self.stun_stacks = cfg.get("stun_stacks", 1)

    def on_battle_start(self, run, engine):
        if run.enemies:
            import random
            enemy = random.choice(run.enemies)
            engine._add_buff_to(enemy, "stun", get_locale_text("i18n_relics_amulets.epic.abyss_whisper.buff_name"), get_locale_text("i18n_relics_amulets.epic.abyss_whisper.buff_desc"), self.stun_stacks)
            engine._log_event(run, get_locale_text("i18n_relics_amulets.epic.abyss_whisper.trigger", name=enemy.name))

class FrostBladeRelic(RelicImpl):
    def __init__(self, relic_id: str):
        super().__init__(relic_id)
        cfg = RELIC_CONFIG.get(relic_id, {})
        self.cold_damage_bonus = cfg.get("cold_damage_bonus", 4)

    def on_damage_calculate(self, event, run, engine):
        dtype_str = event.damage_type.value if hasattr(event.damage_type, "value") else str(event.damage_type)
        if dtype_str == "cold" and event.source == "p0":
            event.modified_damage += self.cold_damage_bonus

class AbyssContractRelic(RelicImpl):
    def __init__(self, relic_id: str):
        super().__init__(relic_id)
        cfg = RELIC_CONFIG.get(relic_id, {})
        self.draw_count = cfg.get("draw_count", 1)

    def on_damage_take(self, event, run, engine):
        dtype_str = event.damage_type.value if hasattr(event.damage_type, "value") else str(event.damage_type)
        if event.target == "p0" and dtype_str == "true" and event.amount > 0:
            engine._draw_cards(run.player, self.draw_count, run)
            engine._log_event(run, get_locale_text("i18n_relics_amulets.epic.abyss_contract.trigger"))

class GlacierCoreRelic(RelicImpl):
    def __init__(self, relic_id: str):
        super().__init__(relic_id)
        cfg = RELIC_CONFIG.get(relic_id, {})
        self.damage_ratio = cfg.get("damage_ratio", 0.5)

    def on_shield_decay(self, event, run, engine):
        if event.target == "p0" and event.amount > 0:
            lost = event.amount
            dmg = int(lost * self.damage_ratio)
            if dmg > 0:
                feedback_parts = []
                for idx in range(len(run.enemies) - 1, -1, -1):
                    enemy = run.enemies[idx]
                    engine._damage_target(run, f"e{idx+1}", dmg, damage_type="cold", source="glacier_core")
                    feedback_parts.append(get_locale_text("i18n_relics_amulets.epic.glacier_core.feedback", name=enemy.name, dmg=dmg))
                if feedback_parts:
                    engine._log_event(run, get_locale_text("i18n_relics_amulets.epic.glacier_core.trigger", feedback="，".join(feedback_parts)))

class DoomsdayCoreRelic(RelicImpl):
    def __init__(self, relic_id: str):
        super().__init__(relic_id)
        cfg = RELIC_CONFIG.get(relic_id, {})
        self.play_threshold = cfg.get("play_threshold", 3)
        self.draw_count = cfg.get("draw_count", 1)

    def on_turn_end(self, event, run, engine):
        if event.is_player:
            played_count = run.node_data.get("cards_played_this_turn", 0)
            if played_count >= self.play_threshold:
                engine._draw_cards(run.player, self.draw_count, run)
                engine._log_event(run, get_locale_text("i18n_relics_amulets.epic.doomsday_core.trigger"))

class NecromancerSkullRelic(RelicImpl):
    def __init__(self, relic_id: str):
        super().__init__(relic_id)
        cfg = RELIC_CONFIG.get(relic_id, {})
        self.heal_amount = cfg.get("heal_amount", 2)

    def on_minion_death(self, event, run, engine):
        engine._heal_target(run, "p0", self.heal_amount)
        engine._log_event(run, get_locale_text("i18n_relics_amulets.epic.necromancer_skull.trigger"))

class ArcanistHandRelic(RelicImpl):
    def __init__(self, relic_id: str):
        super().__init__(relic_id)
        cfg = RELIC_CONFIG.get(relic_id, {})
        self.damage = cfg.get("damage", 3)
        self.cost_threshold = cfg.get("cost_threshold", 0)

    def on_card_played(self, event, run, engine):
        if event.card.cost_a == self.cost_threshold and event.card.cost_ba == self.cost_threshold:
            alive = [e for e in run.enemies if e.hp > 0]
            if alive:
                target_enemy = alive[0]
                idx = run.enemies.index(target_enemy) + 1
                engine._log_event(run, get_locale_text("i18n_relics_amulets.epic.arcanist_hand.trigger", name=target_enemy.name))
                engine.combat_resolver.damage_target(run, f"e{idx}", self.damage, source="relic:arcanist_hand", damage_type="force")

class CommanderMedalRelic(RelicImpl):
    def __init__(self, relic_id: str):
        super().__init__(relic_id)
        cfg = RELIC_CONFIG.get(relic_id, {})
        self.action_bonus = cfg.get("action_bonus", 1)
        self.bonus_action_bonus = cfg.get("bonus_action_bonus", 1)

    def on_battle_start(self, run, engine):
        for m in run.player.minions.values():
            m.actions += self.action_bonus
            m.bonus_actions += self.bonus_action_bonus
        engine._log_event(run, get_locale_text("i18n_relics_amulets.epic.commander_medal.trigger"))

class StalkerEyeRelic(RelicImpl):
    def __init__(self, relic_id: str):
        super().__init__(relic_id)
        cfg = RELIC_CONFIG.get(relic_id, {})
        self.damage_bonus = cfg.get("damage_bonus", 4)
        self.shield_bonus = cfg.get("shield_bonus", 4)

    def on_damage_calculate(self, event, run, engine):
        if event.source == "p0" and event.card and getattr(event.card, "exhaust", False):
            event.modified_damage += self.damage_bonus
            engine._log_event(run, get_locale_text("i18n_relics_amulets.epic.stalker_eye.damage_trigger", name=event.card.name))

    def on_shield_gain(self, event, run, engine):
        if event.target == "p0":
            from ...entities import ALL_CARDS
            playing_cid = run.node_data.get("current_playing_card_id", "")
            card = ALL_CARDS.get(playing_cid)
            if card and getattr(card, "exhaust", False):
                event.modified_amount += self.shield_bonus
                engine._log_event(run, get_locale_text("i18n_relics_amulets.epic.stalker_eye.shield_trigger", name=card.name))
class GladiatorBeltRelic(RelicImpl):
    def __init__(self, relic_id: str):
        super().__init__(relic_id)
        cfg = RELIC_CONFIG.get(relic_id, {})
        self.shield_gain = cfg.get("shield_gain", 2)

    def on_turn_start(self, event, run, engine):
        if event.is_player and run.player.minions:
            engine._gain_shield(run, "p0", self.shield_gain)
            engine._log_event(run, get_locale_text("i18n_relics_amulets.epic.gladiator_belt.trigger"))

class ShieldBatteryRelic(RelicImpl):
    def __init__(self, relic_id: str):
        super().__init__(relic_id)
        cfg = RELIC_CONFIG.get(relic_id, {})
        self.proc_chance = cfg.get("proc_chance", 0.5)
        self.shield_gain = cfg.get("shield_gain", 2)

    def on_shield_gain(self, event, run, engine):
        if event.target == "p0":
            import random
            if random.random() < self.proc_chance:
                event.modified_amount += self.shield_gain
                engine._log_event(run, get_locale_text("i18n_relics_amulets.epic.shield_battery.trigger"))

class CrimsonHeartRelic(RelicImpl):
    def __init__(self, relic_id: str):
        super().__init__(relic_id)
        cfg = RELIC_CONFIG.get(relic_id, {})
        self.hp_threshold = cfg.get("hp_threshold", 0.3)
        self.damage_multiplier = cfg.get("damage_multiplier", 2)
        self.heal_amount = cfg.get("heal_amount", 2)

    def on_damage_calculate(self, event, run, engine):
        p = run.player
        if event.source == "p0" and p.hp / p.max_hp < self.hp_threshold:
            event.modified_damage = int(event.modified_damage * self.damage_multiplier)
            engine._log_event(run, get_locale_text("i18n_relics_amulets.epic.crimson_heart.low_hp_trigger"))

    def on_card_played(self, event, run, engine):
        p = run.player
        if p.hp / p.max_hp < self.hp_threshold:
            old_hp = p.hp
            engine._heal_target(run, "p0", self.heal_amount)
            if p.hp > old_hp:
                engine._log_event(run, get_locale_text("i18n_relics_amulets.epic.crimson_heart.heal_trigger", heal=p.hp - old_hp))

@register_relic("espresso_relic")
class EspressoRelic(RelicImpl):
    def __init__(self, relic_id: str):
        super().__init__(relic_id)
        cfg = RELIC_CONFIG.get(relic_id, {})
        self.action_bonus = cfg.get("action_bonus", 1)

    def on_turn_start(self, event, run, engine):
        if event.is_player:
            run.player.actions += self.action_bonus
            engine._log_event(run, get_locale_text("i18n_relics_amulets.epic.espresso.trigger"))

@register_relic("anthem_relic_3")
class AnthemRelic3(RelicImpl):
    def __init__(self, relic_id: str):
        super().__init__(relic_id)
        cfg = RELIC_CONFIG.get(relic_id, {})
        self.shield_gain = cfg.get("shield_gain", 2)

    def on_battle_start(self, run, engine):
        p = run.player
        engine._gain_shield(run, "p0", self.shield_gain)
        engine._log_event(run, get_locale_text("i18n_relics_amulets.epic.anthem.trigger"))
        if "anthem_relic_3" in p.relics:
            p.relics.remove("anthem_relic_3")
            p.relics.append("anthem_relic_2")

@register_relic("anthem_relic_2")
class AnthemRelic2(RelicImpl):
    def __init__(self, relic_id: str):
        super().__init__(relic_id)
        cfg = RELIC_CONFIG.get(relic_id, {})
        self.shield_gain = cfg.get("shield_gain", 2)

    def on_battle_start(self, run, engine):
        p = run.player
        engine._gain_shield(run, "p0", self.shield_gain)
        engine._log_event(run, get_locale_text("i18n_relics_amulets.epic.anthem.trigger"))
        if "anthem_relic_2" in p.relics:
            p.relics.remove("anthem_relic_2")
            p.relics.append("anthem_relic_1")

@register_relic("anthem_relic_1")
class AnthemRelic1(RelicImpl):
    def __init__(self, relic_id: str):
        super().__init__(relic_id)
        cfg = RELIC_CONFIG.get(relic_id, {})
        self.shield_gain = cfg.get("shield_gain", 2)

    def on_battle_start(self, run, engine):
        p = run.player
        engine._gain_shield(run, "p0", self.shield_gain)
        engine._log_event(run, get_locale_text("i18n_relics_amulets.epic.anthem.exhausted_trigger"))
        if "anthem_relic_1" in p.relics:
            p.relics.remove("anthem_relic_1")

class TimeSandBlessingRelic(RelicImpl):
    def __init__(self, relic_id: str):
        super().__init__(relic_id)
        cfg = RELIC_CONFIG.get(relic_id, {})
        self.bonus_actions = cfg.get("bonus_actions", 2)

    def on_turn_start(self, event, run, engine):
        if event.is_player:
            run.player.bonus_actions += self.bonus_actions
            engine._log_event(run, get_locale_text("i18n_relics_amulets.epic.time_sand_blessing.trigger"))

class StarspawnCoreRelic(RelicImpl):
    def __init__(self, relic_id: str):
        super().__init__(relic_id)
        cfg = RELIC_CONFIG.get(relic_id, {})
        self.damage = cfg.get("damage", 10)
        self.ba_threshold = cfg.get("ba_threshold", 1)

    def on_turn_end(self, event, run, engine):
        if event.is_player and run.player.bonus_actions >= self.ba_threshold:
            alive = [e for e in run.enemies if e.hp > 0]
            if alive:
                import random
                target_enemy = random.choice(alive)
                idx = run.enemies.index(target_enemy) + 1
                engine._log_event(run, get_locale_text("i18n_relics_amulets.epic.starspawn_core.trigger", name=target_enemy.name))
                engine.combat_resolver.damage_target(run, f"e{idx}", self.damage, source="relic:starspawn_core", damage_type="force")


for name, obj in list(globals().items()):
    if isinstance(obj, type) and issubclass(obj, RelicImpl) and obj is not RelicImpl:
        snake = re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()
        if snake.endswith('_relic'):
            relic_id = snake[:-6]
            register_relic(relic_id)(obj)
