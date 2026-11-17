import random

from ...models.state import EnemyIntentState, EnemyState, PlayerState, ensure_card_state
from ...entities.cards.base import ALL_CARDS
from ...core.inventory.deck_service import DeckService
from ...data.corpse_config import CorpseConfig
from ...data.locale_data import get_locale_text
from .base import EnemyTemplate


class GhostEnemyTemplate(EnemyTemplate):
    def roll_intents(self, run, engine, enemy):
        deck = run.node_data.get("ghost_deck", [])
        intents = self._roll_card_intents(deck, enemy)
        if intents:
            return intents
        return self._roll_fallback_intents(run, enemy)

    def _roll_card_intents(self, deck, enemy):
        entries = []
        for index, raw in enumerate(deck):
            state = ensure_card_state(raw)
            card = ALL_CARDS.get(state)
            if card is None or getattr(card, "unplayable", False):
                continue
            entries.append((index, state, card))
        random.shuffle(entries)
        budget_a = max(0, int(getattr(enemy, "actions", 0) or 0))
        budget_ba = max(0, int(getattr(enemy, "bonus_actions", 0) or 0))
        intents = []
        for index, state, card in entries:
            if len(intents) >= int(CorpseConfig.GHOST_MAX_CARDS_PER_TURN):
                break
            cost_a = int(getattr(card, "cost_a", 1) or 0)
            cost_ba = int(getattr(card, "cost_ba", 0) or 0)
            if cost_a < 0:
                cost_a = 1
            if cost_ba < 0:
                cost_ba = 1
            if cost_a > budget_a or cost_ba > budget_ba:
                continue
            budget_a -= cost_a
            budget_ba -= cost_ba
            intents.append(
                EnemyIntentState(
                    type=f"ghost_card:{index}",
                    val=0,
                    desc=get_locale_text("i18n_enemy_misc.ghost.intent_play_card", card_name=card.name),
                    cost_a=cost_a,
                    cost_ba=cost_ba,
                )
            )
        return intents

    def _roll_fallback_intents(self, run, enemy):
        stage_bonus = int(getattr(run.player, "stage", 0))
        budget_a = max(0, int(getattr(enemy, "actions", 0) or 0))
        budget_ba = max(0, int(getattr(enemy, "bonus_actions", 0) or 0))
        intents = []
        if budget_a >= 1:
            damage = 5 + stage_bonus
            intents.append(
                EnemyIntentState(
                    type="attack",
                    val=damage,
                    desc=get_locale_text("i18n_enemy_misc.ghost.intent_attack", damage=damage),
                    cost_a=1,
                    cost_ba=0,
                )
            )
        if budget_ba >= 1:
            shield = 5 + stage_bonus
            intents.append(
                EnemyIntentState(
                    type="defend",
                    val=shield,
                    desc=get_locale_text("i18n_entity_wiring.enemy_base.intent_defend", val=shield),
                    cost_a=0,
                    cost_ba=1,
                )
            )
        return intents

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
                    self._execute_card(
                        run,
                        engine,
                        enemy,
                        index,
                        state,
                        card,
                        int(intent.cost_a),
                        int(intent.cost_ba),
                        logs,
                    )
                    return
            self._perform_attack(run, engine, enemy, 5 + int(getattr(run.player, "stage", 0)), logs)
            return
        super().execute_intent(run, engine, enemy, intent, logs)

    def _execute_card(self, run, engine, enemy, deck_index, state, card, cost_a, cost_ba, logs):
        humans = [
            (uid, player)
            for uid, player in (run.players or {}).items()
            if player is not None and not player.downed and player.hp > 0
        ]
        if not humans and run.player is not None and run.player.hp > 0:
            humans = [(run.user_id, run.player)]
        if not humans:
            self._perform_attack(run, engine, enemy, 5 + int(getattr(run.player, "stage", 0)), logs)
            return

        original_player = run.player
        original_enemies = run.enemies
        original_players = run.players
        original_party_order = run.party_order
        original_node_data = run.node_data
        original_user_id = run.user_id

        proxies = []
        for _uid, human in humans:
            proxies.append(
                (
                    human,
                    EnemyState(
                        name=human.name,
                        hp=int(human.hp),
                        max_hp=int(human.max_hp),
                        shield=int(human.shield),
                        buffs=list(human.buffs),
                        actions=int(human.actions),
                        bonus_actions=int(human.bonus_actions),
                        max_actions=max(1, int(human.actions)),
                        max_bonus_actions=max(0, int(human.bonus_actions)),
                    ),
                )
            )

        deck_states = [ensure_card_state(raw) for raw in (run.node_data.get("ghost_deck", []) or [])]
        draw_states = [
            DeckService.clone_state(card_state)
            for index, card_state in enumerate(deck_states)
            if index != deck_index
        ]
        ghost_player = PlayerState(
            hp=int(enemy.hp),
            max_hp=int(enemy.max_hp),
            shield=int(enemy.shield),
            gold=0,
            stage=int(getattr(original_player, "stage", 0)),
            name=enemy.name,
            deck=[DeckService.clone_state(card_state) for card_state in deck_states],
            draw_pile=draw_states,
            hand=[DeckService.clone_state(state)],
            actions=int(enemy.actions),
            bonus_actions=int(enemy.bonus_actions),
            buffs=list(enemy.buffs),
            relics=[],
            selected_class=getattr(original_player, "selected_class", "法师"),
            subclass=getattr(original_player, "subclass", ""),
            sp=0,
            max_sp=0,
        )

        temp_node_data = dict(original_node_data)
        temp_node_data["battle_logs"] = original_node_data.setdefault("battle_logs", [])
        temp_node_data["battle_log_owners"] = original_node_data.setdefault("battle_log_owners", [])
        temp_node_data["current_playing_card_cid"] = DeckService.clone_state(state)
        temp_node_data["current_playing_card_id"] = card.id
        temp_node_data["current_playing_card_hand_idx"] = 0
        temp_node_data["last_x_cost_a"] = cost_a
        temp_node_data["last_x_cost_ba"] = cost_ba

        run.player = ghost_player
        run.enemies = [proxy for _, proxy in proxies]
        run.players = {run.user_id: ghost_player}
        run.party_order = [run.user_id]
        run.node_data = temp_node_data

        target = "p0" if getattr(card, "target_type", "enemy") in ("self", "any_other") else "e1"
        failed = False
        result = ""
        try:
            result = engine._execute_card_effect(run, card, target)
            tag_result = card.execute_tags(run, target, engine)
            if tag_result:
                logs.append(tag_result)
        except Exception:
            failed = True
        finally:
            run.player = original_player
            run.enemies = original_enemies
            run.players = original_players
            run.party_order = original_party_order
            run.node_data = original_node_data
            run.user_id = original_user_id

        for human, proxy in proxies:
            human.hp = max(0, int(proxy.hp))
            human.max_hp = max(1, int(proxy.max_hp))
            human.shield = max(0, int(proxy.shield))
            human.buffs = list(proxy.buffs)
            human.actions = max(0, int(proxy.actions))
            human.bonus_actions = max(0, int(proxy.bonus_actions))
            if human.hp <= 0:
                from ...core.battle.party_battle import mark_downed
                mark_downed(engine, run, human)

        enemy.hp = max(0, int(ghost_player.hp))
        enemy.max_hp = max(1, int(ghost_player.max_hp))
        enemy.shield = max(0, int(ghost_player.shield))
        enemy.buffs = list(ghost_player.buffs)
        enemy.actions = max(0, int(ghost_player.actions))
        enemy.bonus_actions = max(0, int(ghost_player.bonus_actions))

        for minion in ghost_player.minions.values():
            if minion.hp <= 0:
                continue
            run.enemies.append(
                EnemyState(
                    name=minion.name,
                    hp=int(minion.hp),
                    max_hp=max(1, int(minion.max_hp)),
                    shield=0,
                    actions=1,
                    bonus_actions=0,
                    max_actions=1,
                    max_bonus_actions=0,
                    buffs=list(minion.buffs),
                    is_summon=True,
                )
            )

        logs.append(get_locale_text("i18n_enemy_misc.ghost.play_card", name=enemy.name, card_name=card.name))
        if failed:
            logs.append(get_locale_text("i18n_enemy_misc.ghost.card_failed", name=enemy.name, card_name=card.name))
            if enemy.hp > 0:
                self._perform_attack(run, engine, enemy, 5 + int(getattr(run.player, "stage", 0)), logs)
        elif result:
            logs.append(str(result))
