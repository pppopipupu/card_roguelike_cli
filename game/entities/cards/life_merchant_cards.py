import math

from ...core.progress.achievement_service import AchievementService
from ...data.card_data import CARD_CONFIG
from ...data.locale_data import get_locale_text
from ...models.events import EnemyBeforeDeathEvent, MinionDeathEvent
from ...models.state import Card, ensure_card_state
from .registry import register_card


def _resolve_any_target(run, target, engine):
    if not target or not isinstance(target, str):
        return None
    t = target.strip()
    if t.lower().startswith("a"):
        resolved = engine.combat_resolver.resolve_ally(run, t)
        if not resolved:
            return None
        uid, player, grid = resolved
        if grid is not None:
            if grid not in player.minions:
                return None
            m = player.minions[grid]
            return ("ally_minion", (uid, player, grid), m, f"minion:{uid}:{grid}", m.name)
        if player.downed or player.hp <= 0:
            return None
        return ("ally_player", (uid, player), player, f"player:{uid}", player.name)
    if t == "p0":
        return ("self", (run.uid_for(run.player), run.player), run.player, f"player:{run.uid_for(run.player)}", run.player.name)
    if t.startswith("p"):
        grid = t[1:]
        if grid in run.player.minions:
            m = run.player.minions[grid]
            uid = run.uid_for(run.player)
            return ("own_minion", (uid, run.player, grid), m, f"minion:{uid}:{grid}", m.name)
        return None
    if t.startswith("e"):
        try:
            idx = int(t[1:]) - 1
        except ValueError:
            return None
        if 0 <= idx < len(run.enemies) and run.enemies[idx].hp > 0:
            enemy = run.enemies[idx]
            return ("enemy", idx, enemy, f"enemy:{idx}:{enemy.name}", enemy.name)
        return None
    return None


def _pull_shou_hui_to_hand(player, run, engine):
    has_in_deck = any(ensure_card_state(c).id == "curse_shou_hui" for c in (player.deck or []))
    if not has_in_deck:
        has_in_piles = any(
            ensure_card_state(c).id == "curse_shou_hui"
            for pile in (player.hand, player.draw_pile, player.discard_pile, player.exhaust_pile)
            for c in (pile or [])
        )
        if not has_in_piles:
            return
    if any(ensure_card_state(c).id == "curse_shou_hui" for c in (player.hand or [])):
        return
    max_hand = 9 if "mask_of_void" in player.relics else 12
    if len(player.hand) >= max_hand:
        return
    for pile in (player.draw_pile, player.discard_pile, player.exhaust_pile):
        for idx, c in enumerate(pile):
            if ensure_card_state(c).id == "curse_shou_hui":
                card_state = pile.pop(idx)
                player.hand.append(card_state)
                engine._log_event(run, get_locale_text("i18n_cards_neutral.neutral.cards.curse_shou_hui.pulled_to_hand"))
                return


def _kill_resolved_target(kind, payload, obj, run, engine):
    if kind == "enemy":
        idx = payload
        if 0 <= idx < len(run.enemies) and run.enemies[idx] is obj:
            before_evt = EnemyBeforeDeathEvent(run, obj)
            engine.event_bus.dispatch(before_evt)
            if before_evt.cancelled:
                obj.max_hp = max(1, obj.max_hp, obj.hp)
                return False
            run.player.enemy_graveyard.append(obj.name)
            run.enemies.pop(idx)
            death_evt = MinionDeathEvent(run, obj.name, f"e{idx + 1}", obj.name, True)
            engine.event_bus.dispatch(death_evt)
            return True
    elif kind in ("own_minion", "ally_minion"):
        _, owner, grid = payload
        if grid in owner.minions and owner.minions[grid] is obj:
            owner.minion_graveyard.append(obj.id)
            del owner.minions[grid]
            death_evt = MinionDeathEvent(run, obj.id, f"p{grid}", obj.name, False)
            engine.event_bus.dispatch(death_evt)
            engine._reindex_minions(owner)
            return True
    elif kind == "ally_player":
        _, ally_player = payload
        ally_player.hp = 0
        from ...core.battle.party_battle import mark_downed
        mark_downed(engine, run, ally_player)
        return True
    return False


def _find_alive_shou_hui_target(run, my_key, engine):
    sources = run.node_data.get("shou_lai_sources", {}).get(my_key, [])
    if not sources:
        return None
    for idx, enemy in enumerate(run.enemies, 1):
        if enemy.hp > 0:
            key = f"enemy:{idx - 1}:{enemy.name}"
            if key in sources or enemy.name in sources:
                return f"e{idx}"
    for idx, uid in enumerate(getattr(run, "party_order", []) or [], 1):
        player = run.players.get(uid)
        if player is None or player.downed or player.hp <= 0:
            continue
        if f"player:{uid}" in sources and uid != run.uid_for(run.player):
            return f"a{idx}"
    return None


@register_card("neutral_fusion")
class NeutralFusionCard(Card):
    def can_play_error(self, run, target, engine):
        if run.player.max_hp <= 1:
            return get_locale_text("i18n_cards_neutral.neutral.cards.neutral_fusion.err_min_hp")
        return None

    def execute(self, run, target, engine) -> str:
        p = run.player
        if p.max_hp <= 1:
            return get_locale_text("i18n_cards_neutral.neutral.cards.neutral_fusion.err_min_hp")
        ratio = float(getattr(self, "hp_cost_ratio", 0.10 if self.upgraded else 0.15))
        cost = min(p.max_hp - 1, max(1, math.ceil(p.max_hp * ratio)))
        p.max_hp -= cost
        p.hp = min(p.hp, p.max_hp)
        p.actions *= 2
        p.bonus_actions *= 2
        if p.actions >= 10:
            AchievementService(engine.save_manager).record_stat(
                run.user_id,
                "fusion_overclocks",
                1,
                run=run,
                battle_engine=engine,
            )
        return get_locale_text(
            "i18n_cards_neutral.neutral.cards.neutral_fusion.result",
            cost=cost,
            actions=p.actions,
            bonus_actions=p.bonus_actions,
        )


@register_card("neutral_shou_lai")
class NeutralShouLaiCard(Card):
    def can_play_error(self, run, target, engine):
        chosen = target or engine._get_first_alive_enemy(run)
        resolved = _resolve_any_target(run, chosen, engine)
        if resolved is None:
            return get_locale_text("i18n_cards_neutral.neutral.cards.neutral_shou_lai.err_no_target")
        kind, payload, _, _, _ = resolved
        if kind == "self":
            return get_locale_text("i18n_cards_neutral.neutral.cards.neutral_shou_lai.err_self_target")
        if kind == "ally_player" and payload[0] == run.uid_for(run.player):
            return get_locale_text("i18n_cards_neutral.neutral.cards.neutral_shou_lai.err_self_target")
        return None

    def execute(self, run, target, engine) -> str:
        p = run.player
        chosen = target or engine._get_first_alive_enemy(run)
        resolved = _resolve_any_target(run, chosen, engine)
        if resolved is None:
            return get_locale_text("i18n_cards_neutral.neutral.cards.neutral_shou_lai.err_no_target")
        kind, payload, obj, target_key, target_name = resolved
        if kind == "self" or (kind == "ally_player" and payload[0] == run.uid_for(p)):
            return get_locale_text("i18n_cards_neutral.neutral.cards.neutral_shou_lai.err_self_target")
        absorb = int(getattr(self, "absorb_amount", 8 if self.upgraded else 6))
        if kind == "ally_player":
            actual = min(absorb, max(0, obj.max_hp - 1))
        else:
            actual = min(absorb, max(0, obj.max_hp))
        obj.max_hp -= actual
        obj.hp = min(obj.hp, obj.max_hp)
        p.max_hp += actual
        p.hp += actual

        caster_key = f"player:{run.uid_for(p)}"
        sources = run.node_data.setdefault("shou_lai_sources", {})
        sources.setdefault(target_key, [])
        if caster_key not in sources[target_key]:
            sources[target_key].append(caster_key)

        if kind == "ally_player":
            _pull_shou_hui_to_hand(obj, run, engine)

        if kind != "ally_player" and (obj.max_hp <= 0 or obj.hp <= 0):
            killed = _kill_resolved_target(kind, payload, obj, run, engine)
            if killed:
                return get_locale_text(
                    "i18n_cards_neutral.neutral.cards.neutral_shou_lai.result_killed",
                    target_name=target_name,
                    self_max_hp=p.max_hp,
                )

        return get_locale_text(
            "i18n_cards_neutral.neutral.cards.neutral_shou_lai.result",
            target_name=target_name,
            gain=actual,
            target_max_hp=obj.max_hp,
            self_max_hp=p.max_hp,
        )


@register_card("curse_shou_hui")
class CurseShouHuiCard(Card):
    def can_play_error(self, run, target, engine):
        if target is None:
            return None
        my_key = f"player:{run.uid_for(run.player)}"
        auto_target = _find_alive_shou_hui_target(run, my_key, engine)
        if auto_target is None:
            return None
        resolved = _resolve_any_target(run, target, engine)
        if resolved is None:
            return get_locale_text("i18n_battle_core.invalid_target")
        _, _, _, target_key, target_name = resolved
        sources = run.node_data.get("shou_lai_sources", {}).get(my_key, [])
        if target_key not in sources and target_name not in sources:
            return get_locale_text(
                "i18n_cards_neutral.neutral.cards.curse_shou_hui.err_not_source",
                target_name=target_name,
            )
        return None

    def execute(self, run, target, engine) -> str:
        p = run.player
        my_key = f"player:{run.uid_for(p)}"
        sources = run.node_data.get("shou_lai_sources", {}).get(my_key, [])
        chosen = target
        if not chosen or _find_alive_shou_hui_target(run, my_key, engine) is None:
            chosen = _find_alive_shou_hui_target(run, my_key, engine)
        if not chosen:
            return get_locale_text("i18n_cards_neutral.neutral.cards.curse_shou_hui.no_valid_target")
        resolved = _resolve_any_target(run, chosen, engine)
        if resolved is None:
            return get_locale_text("i18n_cards_neutral.neutral.cards.curse_shou_hui.no_valid_target")
        kind, payload, obj, target_key, target_name = resolved
        if target_key not in sources and target_name not in sources:
            return get_locale_text(
                "i18n_cards_neutral.neutral.cards.curse_shou_hui.err_not_source",
                target_name=target_name,
            )

        if target_key in sources:
            sources.remove(target_key)
        elif target_name in sources:
            sources.remove(target_name)

        cap = int(getattr(self, "target_hp_cap", 5))
        old_max_hp = int(getattr(obj, "max_hp", 0))
        if old_max_hp < cap:
            _kill_resolved_target(kind, payload, obj, run, engine)
            AchievementService(engine.save_manager).record_stat(
                run.user_id,
                "shou_hui_kills",
                1,
                run=run,
                battle_engine=engine,
            )
            return get_locale_text(
                "i18n_cards_neutral.neutral.cards.curse_shou_hui.result_kill",
                target_name=target_name,
                cap=cap,
            )

        gain = max(0, old_max_hp - cap)
        obj.max_hp = cap
        obj.hp = min(obj.hp, cap)
        p.max_hp += gain
        p.hp += gain
        return get_locale_text(
            "i18n_cards_neutral.neutral.cards.curse_shou_hui.result_drain",
            target_name=target_name,
            cap=cap,
            gain=gain,
        )


@register_card("neutral_tau")
class NeutralTauCard(Card):
    def execute(self, run, target, engine) -> str:
        p = run.player
        cfg = CARD_CONFIG.get(self.id.replace("+", ""), {})
        minion_id = f"{self.id}+" if self.upgraded else self.id
        grid = engine._summon_minion(run, minion_id, self.name, self.minion_hp, self.minion_atk, 0)
        if not grid:
            return cfg.get("feedback_fail", get_locale_text("i18n_cards_neutral.neutral.base.summon_minion.fail"))

        tau = p.minions[grid]
        tau.actions = 0
        tau.bonus_actions = 0
        tau.attack_actions = 0

        from ..relics.base import RelicImpl, get_relic_impl

        relic_count = 0
        for rid in list(p.relics):
            impl = get_relic_impl(rid)
            if impl and type(impl).on_battle_start is not RelicImpl.on_battle_start:
                impl.on_battle_start(run, engine)
                relic_count += 1
        if relic_count > 0:
            engine._log_event(
                run,
                get_locale_text("i18n_cards_neutral.neutral.cards.neutral_tau.relic_header", count=relic_count),
            )

        from ..minions import ALL_MINIONS

        skill_count = 0
        for m_grid, minion in list(p.minions.items()):
            if m_grid == grid:
                continue
            template = ALL_MINIONS.get(minion.id)
            if not template or not template.skills:
                continue
            skill = template.skills[0]
            skill_target = engine._get_first_alive_enemy(run)
            run.node_data["current_acting_minion_grid"] = m_grid
            try:
                effect_msg = skill.execute(run, m_grid, skill_target, engine)
            finally:
                run.node_data.pop("current_acting_minion_grid", None)
            skill_count += 1
            engine._log_event(
                run,
                get_locale_text(
                    "i18n_cards_neutral.neutral.cards.neutral_tau.skill_entry",
                    minion=minion.name,
                    skill=skill.name,
                    effect=effect_msg,
                ),
            )

        if relic_count >= 2 and skill_count >= 2:
            AchievementService(engine.save_manager).record_stat(
                run.user_id,
                "tau_conducts",
                1,
                run=run,
                battle_engine=engine,
            )

        return get_locale_text("i18n_cards_neutral.neutral.cards.neutral_tau.result", grid=grid)
