import random
from ...core.battle.vanish import vanish_cards
from ...data.anna_card_config import ANNE_SKILL_CONFIG
from ...data.locale_data import get_locale_text
from .minion_base import BaseMinionSkill


class AnneVanishSkill(BaseMinionSkill):
    def execute(self, run, my_grid, target, engine) -> str:
        cfg = ANNE_SKILL_CONFIG
        vanished = vanish_cards(run, cfg["vanish_count"], engine)
        shares = {}
        alive = [i + 1 for i, e in enumerate(run.enemies) if e.hp > 0]
        for _ in range(cfg["fire_damage_total"]):
            if not alive:
                break
            idx = random.choice(alive)
            shares[idx] = shares.get(idx, 0) + 1
        for idx in sorted(shares, reverse=True):
            engine._damage_target(run, f"e{idx}", shares[idx], damage_type=cfg["attack_damage_type"])
        name = run.player.minions[my_grid].name
        if not vanished:
            return get_locale_text(
                "i18n_cards_anna.skill_result_empty",
                name=name,
                damage=cfg["fire_damage_total"],
            )
        joiner = get_locale_text("i18n_cards_anna.names_joiner")
        return get_locale_text(
            "i18n_cards_anna.skill_result",
            name=name,
            cards=joiner.join(vanished),
            damage=cfg["fire_damage_total"],
        )
