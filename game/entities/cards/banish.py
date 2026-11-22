import random
from typing import Optional

from ...data.enemies.enemy_data import ENEMY_CONFIG
from ...data.text.locale_data import get_locale_text
from ...models.state import Card
from .registry import register_card


def _card_config(card):
    from ...data.cards.card_upgrade_data import CARD_UPGRADE_CONFIG
    from ...data.cards.neutral.neutral_card_data import NEUTRAL_CARD_CONFIG

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
    def get_selection_spec(self, run, engine) -> Optional[dict]:
        from ...core.battle.selection import ChoiceOption, choose_one_spec
        stage = int(run.node_data.get("cthulhu_seal_stage", 1) or 1)
        max_option = 2 if stage >= 3 else 3
        options = [
            ChoiceOption(
                id=str(idx),
                label_key=f"i18n_cli_core.cthulhu_puzzle_stage{stage}_option{idx}",
                value=str(idx),
            )
            for idx in range(1, max_option + 1)
        ]
        return choose_one_spec(
            options,
            step_id="cthulhu_choice",
            prompt_key="i18n_cli_core.cthulhu_puzzle_prompt",
            error_key="i18n_cli_core.err_cthulhu_puzzle_invalid",
            invalid_index_key="i18n_cli_core.err_cthulhu_puzzle_invalid",
            cancel_key="i18n_cli_core.cthulhu_puzzle_cancelled",
        )

    def execute_with_selections(self, run, selections: dict, engine) -> str:
        from ...core.battle.selection import SelectionResult
        from ...entities.enemies.boss.cthulhu_boss import resolve_cthulhu_puzzle
        choice = SelectionResult.from_raw(selections).choice("cthulhu_choice")
        if choice is None:
            return get_locale_text("i18n_cli_core.err_cthulhu_puzzle_invalid")
        return resolve_cthulhu_puzzle(run, engine, int(choice), run.player)

    def execute(self, run, target, engine) -> str:
        from ...entities.enemies.boss.cthulhu_boss import resolve_cthulhu_puzzle
        stage = int(run.node_data.get("cthulhu_seal_stage", 1) or 1)
        option = 2 if stage == 2 else 1
        return resolve_cthulhu_puzzle(run, engine, option, run.player)
