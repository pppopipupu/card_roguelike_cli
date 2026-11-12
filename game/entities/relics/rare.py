import re
from ...data.relic_data import RELIC_CONFIG
from ...data.locale_data import get_locale_text
from ...data.damage_type_data import is_physical_damage, is_spell_card_damage
from .base import RelicImpl
from .registry import register_relic

class ReadyPackRelic(RelicImpl):
    def __init__(self, relic_id: str):
        super().__init__(relic_id)
        cfg = RELIC_CONFIG.get(relic_id, {})
        self.draw_bonus = cfg.get("draw_bonus", 1)
        self.ba_bonus = cfg.get("ba_bonus", 1)

    def on_battle_start(self, run, engine):
        run.player.bonus_actions += self.ba_bonus
        engine._log_event(run, get_locale_text("i18n_relics_amulets.rare.ready_pack.trigger", ba_bonus=self.ba_bonus))

    def modify_initial_draw(self, run, draw_count: int, engine) -> int:
        return draw_count + self.draw_bonus

class WhetstoneRelic(RelicImpl):
    def __init__(self, relic_id: str):
        super().__init__(relic_id)
        cfg = RELIC_CONFIG.get(relic_id, {})
        self.attack_bonus = cfg.get("attack_bonus", 1)

    def on_damage_calculate(self, event, run, engine):
        if event.source.startswith("p") and event.source != "p0" and event.damage_type == "attack":
            event.modified_damage += self.attack_bonus

class ArcaneRuneRelic(RelicImpl):
    def __init__(self, relic_id: str):
        super().__init__(relic_id)
        cfg = RELIC_CONFIG.get(relic_id, {})
        self.spell_bonus = cfg.get("spell_bonus", 1)

    def on_damage_calculate(self, event, run, engine):
        if is_spell_card_damage(event) and event.source == "p0":
            event.modified_damage += self.spell_bonus

class ChemicalXRelic(RelicImpl):
    pass

class AncientCompassRelic(RelicImpl):
    def __init__(self, relic_id: str):
        super().__init__(relic_id)
        cfg = RELIC_CONFIG.get(relic_id, {})
        self.action_reduction = cfg.get("action_reduction", 1)

    def on_battle_start(self, run, engine):
        for e in run.enemies:
            e.actions = max(0, e.actions - self.action_reduction)
        engine._log_event(run, get_locale_text("i18n_relics_amulets.rare.ancient_compass.trigger"))

class VoidLensRelic(RelicImpl):
    def __init__(self, relic_id: str):
        super().__init__(relic_id)
        cfg = RELIC_CONFIG.get(relic_id, {})
        self.damage_bonus = cfg.get("damage_bonus", 2)
        self.shield_bonus = cfg.get("shield_bonus", 2)

    def on_damage_calculate(self, event, run, engine):
        if event.card and event.card.color == "neutral" and event.source == "p0":
            event.modified_damage += self.damage_bonus

    def on_shield_gain(self, event, run, engine):
        curr_cid = run.node_data.get("current_playing_card_id", "")
        if curr_cid:
            from ..cards.base import ALL_CARDS
            card = ALL_CARDS.get(curr_cid)
            if card and card.color == "neutral":
                event.modified_amount += self.shield_bonus

class CenturionMailRelic(RelicImpl):
    def __init__(self, relic_id: str):
        super().__init__(relic_id)
        cfg = RELIC_CONFIG.get(relic_id, {})
        self.damage_reduction = cfg.get("damage_reduction", 2)

    def on_damage_calculate(self, event, run, engine):
        if event.target == "p0" and is_physical_damage(event.damage_type):
            event.modified_damage = max(0, event.modified_damage - self.damage_reduction)

class PriestCharmRelic(RelicImpl):
    def __init__(self, relic_id: str):
        super().__init__(relic_id)
        cfg = RELIC_CONFIG.get(relic_id, {})
        self.shield_gain = cfg.get("shield_gain", 3)

    def on_heal(self, event, run, engine):
        if event.target == "p0":
            engine._gain_shield(run, "p0", self.shield_gain)

class BeastmasterClawRelic(RelicImpl):
    def __init__(self, relic_id: str):
        super().__init__(relic_id)
        cfg = RELIC_CONFIG.get(relic_id, {})
        self.atk_bonus = cfg.get("atk_bonus", 1)

    def on_battle_start(self, run, engine):
        for m in run.player.minions.values():
            m.atk += self.atk_bonus

    def on_minion_summon(self, event, run, engine):
        event.minion_state.atk += self.atk_bonus

class DjinnShardRelic(RelicImpl):
    def __init__(self, relic_id: str):
        super().__init__(relic_id)
        cfg = RELIC_CONFIG.get(relic_id, {})
        self.damage = cfg.get("damage", 5)

    def on_turn_start(self, event, run, engine):
        if event.is_player:
            run.node_data["djinn_shard_fired"] = False

    def on_card_played(self, event, run, engine):
        if not run.node_data.get("djinn_shard_fired", False) and event.card.type == "spell":
            run.node_data["djinn_shard_fired"] = True
            alive = [e for e in run.enemies if e.hp > 0]
            if alive:
                import random
                target_enemy = random.choice(alive)
                idx = run.enemies.index(target_enemy) + 1
                engine._log_event(run, get_locale_text("i18n_relics_amulets.rare.djinn_shard.trigger", name=target_enemy.name))
                engine.combat_resolver.damage_target(run, f"e{idx}", self.damage, source="relic:djinn_shard", damage_type="force")

class ArchmageRobeRelic(RelicImpl):
    pass

class ShadowTentacleRelic(RelicImpl):
    pass

class MindflayerBrainRelic(RelicImpl):
    pass

class LengSpiderVenomRelic(RelicImpl):
    def __init__(self, relic_id: str):
        super().__init__(relic_id)
        cfg = RELIC_CONFIG.get(relic_id, {})
        self.proc_chance = cfg.get("proc_chance", 0.5)
        self.vulnerable_stacks = cfg.get("vulnerable_stacks", 1)

    def on_damage_take(self, event, run, engine):
        if event.source == "p0" and event.target.startswith("e"):
            dtype = event.damage_type
            if is_physical_damage(dtype):
                import random
                if random.random() < self.proc_chance:
                    try:
                        idx = int(event.target[1:]) - 1
                        if 0 <= idx < len(run.enemies):
                            enemy = run.enemies[idx]
                            engine._add_buff_to(enemy, "minor_vulnerable", get_locale_text("i18n_relics_amulets.rare.leng_spider_venom.buff_name"), get_locale_text("i18n_relics_amulets.rare.leng_spider_venom.buff_desc"), self.vulnerable_stacks)
                            engine._log_event(run, get_locale_text("i18n_relics_amulets.rare.leng_spider_venom.trigger", name=enemy.name))
                    except ValueError:
                        pass

class MigoLightningGunRelic(RelicImpl):
    def __init__(self, relic_id: str):
        super().__init__(relic_id)
        cfg = RELIC_CONFIG.get(relic_id, {})
        self.damage = cfg.get("damage", 5)

    def on_battle_start(self, run, engine):
        engine._log_event(run, get_locale_text("i18n_relics_amulets.rare.migo_lightning_gun.trigger"))
        for idx in range(len(run.enemies) - 1, -1, -1):
            target_str = f"e{idx+1}"
            engine.combat_resolver.damage_target(run, target_str, self.damage, source="relic:migo_lightning_gun", damage_type="lightning")

class ShoggothSlimeRelic(RelicImpl):
    def __init__(self, relic_id: str):
        super().__init__(relic_id)
        cfg = RELIC_CONFIG.get(relic_id, {})
        self.shield_gain = cfg.get("shield_gain", 4)

    def on_damage_take(self, event, run, engine):
        if event.target == "p0" and event.amount > 0:
            is_true = (event.damage_type == "true" or event.damage_type == "TRUE")
            last_shield = run.node_data.get("last_shield_before_dmg", 0)
            if is_true or event.amount > last_shield:
                engine._log_event(run, get_locale_text("i18n_relics_amulets.rare.shoggoth_slime.trigger"))
                engine._gain_shield(run, "p0", self.shield_gain)

class StarVampireProboscisRelic(RelicImpl):
    def __init__(self, relic_id: str):
        super().__init__(relic_id)
        cfg = RELIC_CONFIG.get(relic_id, {})
        self.heal_amount = cfg.get("heal_amount", 2)

    def on_card_played(self, event, run, engine):
        card = event.card
        if getattr(card, "exhaust", False) or getattr(card, "id", "") == "curse_dimensional_tear":
            engine._log_event(run, get_locale_text("i18n_relics_amulets.rare.star_vampire_proboscis.trigger"))
            engine._heal_target(run, "p0", self.heal_amount)



for name, obj in list(globals().items()):
    if isinstance(obj, type) and issubclass(obj, RelicImpl) and obj is not RelicImpl:
        snake = re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()
        if snake.endswith('_relic'):
            relic_id = snake[:-6]
            register_relic(relic_id)(obj)
