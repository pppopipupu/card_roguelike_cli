import random

from ...models.state import EnemyIntentState, ensure_card_state
from ...entities.cards.base import ALL_CARDS
from ...data.card_data import CARD_CONFIG
from ...data.card_upgrade_data import CARD_UPGRADE_CONFIG
from ...data.locale_data import get_locale_text
from .base import EnemyTemplate


class GhostEnemyTemplate(EnemyTemplate):
    def roll_intents(self, run, engine, enemy):
        deck = run.node_data.get("ghost_deck", [])
        if deck:
            index = random.randrange(len(deck))
            state = ensure_card_state(deck[index])
            card = ALL_CARDS.get(state)
            card_name = card.name if card else state.id
            return [
                EnemyIntentState(
                    type=f"ghost_card:{index}",
                    val=0,
                    desc=get_locale_text("i18n_enemy_misc.ghost.intent_play_card", card_name=card_name),
                    cost_a=1,
                    cost_ba=0,
                )
            ]
        damage = 5 + int(getattr(run.player, "stage", 0))
        return [
            EnemyIntentState(
                type="attack",
                val=damage,
                desc=get_locale_text("i18n_enemy_misc.ghost.intent_attack", damage=damage),
                cost_a=1,
                cost_ba=0,
            )
        ]

    def execute_intent(self, run, engine, enemy, intent, logs=None):
        if logs is None:
            logs = []
        if intent.type.startswith("ghost_card:"):
            try:
                index = int(intent.type.split(":", 1)[1])
            except ValueError:
                index = -1
            deck = run.node_data.get("ghost_deck", [])
            if 0 <= index < len(deck):
                state = ensure_card_state(deck[index])
                card = ALL_CARDS.get(state)
                if card is not None:
                    self._resolve_card(run, engine, enemy, state, card, logs)
                    return
        super().execute_intent(run, engine, enemy, intent, logs)

    def _resolve_card(self, run, engine, enemy, state, card, logs):
        base_cfg = CARD_CONFIG.get(state.id, {})
        upgrade_cfg = CARD_UPGRADE_CONFIG.get(state.id, {}) if state.upgraded else {}
        damage = int(upgrade_cfg.get("base_dmg", base_cfg.get("base_dmg", 0)) or 0)
        count = int(upgrade_cfg.get("count", base_cfg.get("count", 1)) or 1)
        damage *= max(1, count)
        heal = int(upgrade_cfg.get("heal_amount", base_cfg.get("heal_amount", 0)) or 0)
        shield = int(upgrade_cfg.get("shield_amount", base_cfg.get("shield_amount", 0)) or 0)
        if card.type in ("amulet", "ability") and shield <= 0:
            shield = 5
        if card.type == "minion" and shield <= 0:
            shield = 4
        if damage <= 0 and heal <= 0 and shield <= 0:
            if card.type == "minion":
                damage = int(upgrade_cfg.get("minion_atk", base_cfg.get("minion_atk", 4)) or 4)
            elif card.type == "spell":
                cost = int(getattr(card, "cost_a", 1) or 1)
                damage = max(3, cost * 3 + (2 if state.upgraded else 0))
            else:
                shield = 3
        damage = engine.combat_resolver._apply_gem_dmg(card, damage)
        card_name = card.name
        if damage > 0:
            damage_type = getattr(card, "damage_type", "effect") or "effect"
            engine.combat_resolver.damage_target(
                run,
                "p0",
                damage,
                source=f"enemy:{enemy.name}",
                damage_type=damage_type,
                card=card,
            )
            logs.append(get_locale_text("i18n_enemy_misc.ghost.damage", name=enemy.name, card_name=card_name, damage=damage))
        if heal > 0:
            if enemy in run.enemies:
                engine._heal_target(run, f"e{run.enemies.index(enemy)+1}", heal)
            logs.append(get_locale_text("i18n_enemy_misc.ghost.heal", name=enemy.name, card_name=card_name, heal=heal))
        if shield > 0:
            if enemy in run.enemies:
                engine._gain_shield(run, f"e{run.enemies.index(enemy)+1}", shield)
            logs.append(get_locale_text("i18n_enemy_misc.ghost.shield", name=enemy.name, card_name=card_name, shield=shield))
        if damage <= 0 and heal <= 0 and shield <= 0:
            if enemy in run.enemies:
                engine._gain_shield(run, f"e{run.enemies.index(enemy)+1}", 3)
            logs.append(get_locale_text("i18n_enemy_misc.ghost.shield_fallback", name=enemy.name, card_name=card_name))
