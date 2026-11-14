import random
from ...data.anna_card_config import EXCELLENT_CRIT_CONFIG, EXCELLENT_CRIT_ID
from ...data.locale_data import get_locale_text
from ...models.state import Card
from ...core.battle.vanish import count_cards_in_piles
from .neutral_base import SummonMinionCard
from .registry import register_card


@register_card("manaeria_queen_anne")
class AnneMinionCard(SummonMinionCard):
    pass


@register_card(EXCELLENT_CRIT_ID)
class ExcellentCritCard(Card):
    def can_play_error(self, run, target, engine):
        if isinstance(target, str):
            lowered = target.strip().lower()
            if lowered == "p0" or lowered.startswith("p") or lowered.startswith("a"):
                return None
        return get_locale_text("i18n_cards_anna.crit_need_ally_target")

    def execute(self, run, target, engine) -> str:
        cfg = EXCELLENT_CRIT_CONFIG
        pile_total = count_cards_in_piles(run)
        damage = self._pick_damage(pile_total, cfg)
        force_type, true_type = cfg["damage_types"]
        ally_name = engine._get_target_name(run, target)
        engine._damage_target(run, target, damage["force"], damage_type=force_type)
        engine._damage_target(run, target, damage["true"], damage_type=true_type)
        enemy_target = self._random_enemy(run)
        if enemy_target is None:
            return get_locale_text(
                "i18n_cards_anna.crit_result_no_enemy",
                card=self.name,
                ally=ally_name,
                force=damage["force"],
                true=damage["true"],
                pile=pile_total,
            )
        enemy_name = engine._get_target_name(run, enemy_target)
        engine._damage_target(run, enemy_target, damage["force"], damage_type=force_type)
        engine._damage_target(run, enemy_target, damage["true"], damage_type=true_type)
        return get_locale_text(
            "i18n_cards_anna.crit_result",
            card=self.name,
            ally=ally_name,
            enemy=enemy_name,
            force=damage["force"],
            true=damage["true"],
            pile=pile_total,
        )

    @staticmethod
    def _pick_damage(pile_total, cfg):
        for tier in cfg["tiers"]:
            if tier["op"] == "eq" and pile_total == tier["value"]:
                return tier
            if tier["op"] == "lt" and pile_total < tier["value"]:
                return tier
        return cfg["base"]

    @staticmethod
    def _random_enemy(run):
        alive = [f"e{i + 1}" for i, e in enumerate(run.enemies) if e.hp > 0]
        return random.choice(alive) if alive else None
