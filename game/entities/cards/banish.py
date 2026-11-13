import random

from ...data.enemy_data import ENEMY_CONFIG
from ...data.locale_data import get_locale_text
from ...models.state import Card
from .registry import register_card


def _card_config(card):
    from ...data.card_upgrade_data import CARD_UPGRADE_CONFIG
    from ...data.neutral_card_data import NEUTRAL_CARD_CONFIG

    base_id = str(getattr(card, "id", "")).replace("+", "")
    cfg = dict(NEUTRAL_CARD_CONFIG.get(base_id, {}))
    if getattr(card, "upgraded", False):
        cfg.update(CARD_UPGRADE_CONFIG.get(base_id, {}))
    return cfg


def _target_enemy(run, target):
    if not target or not isinstance(target, str) or not target.startswith("e"):
        return None
    try:
        idx = int(target[1:]) - 1
    except ValueError:
        return None
    if 0 <= idx < len(run.enemies):
        return run.enemies[idx]
    return None


def _enemy_base_name(name):
    from ...core.battle.reward_builder import base_enemy_name

    return base_enemy_name(str(name))


def _remove_buff(entity, buff_id):
    entity.buffs = [b for b in entity.buffs if b.id != buff_id]


def _bump(run, key):
    run.node_data[key] = int(run.node_data.get(key, 0) or 0) + 1


def _is_mist_form(enemy):
    mist_prefix = get_locale_text("i18n_enemy_boss.cthulhu_mist_name")
    if mist_prefix and enemy.name.startswith(mist_prefix):
        return True
    return any(b.id == "cthulhu_mist_immune" for b in enemy.buffs)


@register_card("neutral_banish_slash")
class BanishSlashCard(Card):
    def execute(self, run, target, engine) -> str:
        cfg = _card_config(self)
        dmg = int(getattr(self, "base_dmg", cfg.get("base_dmg", 0)) or 0)
        if not target:
            target = engine._get_first_alive_enemy(run)
        enemy = _target_enemy(run, target)
        if enemy is not None:
            target_name = enemy.name
        elif target:
            target_name = engine._get_target_name(run, target)
        else:
            target_name = get_locale_text("i18n_battle_misc.target_unknown_enemy")
        fail_key = "i18n_cards_neutral.neutral.cards.banish_slash.banish_fail"
        if enemy is None:
            return get_locale_text(fail_key, target=target_name, dmg=dmg)
        if _is_mist_form(enemy):
            enemy.hp = 0
            _remove_buff(enemy, "cthulhu_mist_immune")
            return get_locale_text("i18n_cards_neutral.neutral.cards.banish_slash.banish_boss_success")
        engine._damage_target(run, target, dmg, source="p0", damage_type="force")
        if enemy.hp <= 0:
            return get_locale_text(fail_key, target=target_name, dmg=dmg)
        enemy_cfg = ENEMY_CONFIG.get(_enemy_base_name(target_name), {})
        chance = float(cfg.get("banish_chance", 0) or 0)
        if enemy_cfg.get("type") != "boss" and random.random() < chance:
            enemy.hp = 0
            _bump(run, "banished_enemy_count")
            _bump(run, "banished_total")
            return get_locale_text(
                "i18n_cards_neutral.neutral.cards.banish_slash.banish_success",
                target=target_name,
            )
        return get_locale_text(fail_key, target=target_name, dmg=dmg)


@register_card("special_rlyeh_astrolabe")
class RlyehAstrolabeCard(Card):
    def execute(self, run, target, engine) -> str:
        run.node_data.setdefault("state_stack", []).append({
            "type": "cthulhu_puzzle_choice",
            "stage": run.node_data.get("cthulhu_seal_stage", 1),
        })
        return get_locale_text("i18n_cards_neutral.neutral.cards.rlyeh_astrolabe.feedback")
