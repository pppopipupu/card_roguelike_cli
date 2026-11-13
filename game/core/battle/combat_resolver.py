import random
from typing import Optional
from ...data.locale_data import get_locale_text
from ...data.damage_type_data import is_physical_damage
from ...models.state import GameRun, PlayerState, EnemyState, MinionState, Card, BuffState
from ...models.events import (
    BeforeDamageApplyEvent, DamageCalculateEvent, DamageTakeEvent, HealEvent, MinionDeathEvent, MinionSummonEvent, ShieldGainEvent, HealCalculateEvent, EnemyBeforeDeathEvent
)

DAMAGE_TYPE_KEYS = {
    "acid": "i18n_battle_misc.damage_type_acid",
    "bludgeoning": "i18n_battle_misc.damage_type_bludgeoning",
    "bludgeoning_magic": "i18n_battle_misc.damage_type_bludgeoning_magic",
    "cold": "i18n_battle_misc.damage_type_cold",
    "fire": "i18n_battle_misc.damage_type_fire",
    "force": "i18n_battle_misc.damage_type_force",
    "lightning": "i18n_battle_misc.damage_type_lightning",
    "necrotic": "i18n_battle_misc.damage_type_necrotic",
    "piercing": "i18n_battle_misc.damage_type_piercing",
    "piercing_magic": "i18n_battle_misc.damage_type_piercing_magic",
    "poison": "i18n_battle_misc.damage_type_poison",
    "psychic": "i18n_battle_misc.damage_type_psychic",
    "radiant": "i18n_battle_misc.damage_type_radiant",
    "slashing": "i18n_battle_misc.damage_type_slashing",
    "slashing_magic": "i18n_battle_misc.damage_type_slashing_magic",
    "thunder": "i18n_battle_misc.damage_type_thunder",
    "true": "i18n_battle_misc.damage_type_true",
    "attack": "i18n_battle_misc.damage_type_attack",
    "effect": "i18n_battle_misc.damage_type_effect",
    "spell": "i18n_battle_misc.damage_type_spell"
}

class CombatResolver:
    def __init__(self, engine):
        self.engine = engine

    def resolve_ally(self, run: GameRun, target: Optional[str]):
        if not run or not target:
            return None
        text = str(target).strip().lower()
        if not text.startswith("a"):
            return None
        rest = text[1:]
        grid = None
        if "m" in rest:
            index_part, grid = rest.split("m", 1)
            if not grid.isdigit():
                return None
        else:
            index_part = rest
        if not index_part.isdigit():
            return None
        index = int(index_part) - 1
        if index < 0 or index >= len(run.party_order):
            return None
        uid = run.party_order[index]
        player = run.players.get(uid)
        if player is None:
            return None
        return uid, player, grid

    def _redirect_ally(self, run: GameRun, target: str, operation) -> bool:
        resolved = self.resolve_ally(run, target)
        if not resolved:
            return False
        uid, player, grid = resolved
        if player is run.player:
            inner = "p0" if grid is None else f"p{grid}"
            operation(inner)
            return True
        previous = run.player
        previous_user = run.user_id
        run.player = player
        run.user_id = uid
        try:
            inner = "p0" if grid is None else f"p{grid}"
            operation(inner)
        finally:
            run.player = previous
            run.user_id = previous_user
        return True

    def get_target_name(self, run: GameRun, target: Optional[str]) -> str:
        if not target:
            return get_locale_text("i18n_battle_misc.target_none")
        resolved = self.resolve_ally(run, target)
        if resolved:
            uid, player, grid = resolved
            if grid is None:
                return player.name
            if grid in player.minions:
                return player.minions[grid].name
            return get_locale_text("i18n_battle_misc.target_ally_minion")
        if target == "p0":
            return run.player.name
        if target.startswith("e"):
            try:
                idx = int(target[1:]) - 1
                if idx < 0: idx = 0
            except ValueError:
                idx = 0
            if 0 <= idx < len(run.enemies):
                return run.enemies[idx].name
            return get_locale_text("i18n_battle_misc.target_unknown_enemy")
        if target.startswith("p"):
            grid = target[1:]
            if grid in run.player.minions:
                return run.player.minions[grid].name
            return get_locale_text("i18n_battle_misc.target_own_minion")
        return get_locale_text("i18n_battle_misc.target_unknown")

    def get_source_name(self, run: GameRun, source: str) -> str:
        if not source:
            return get_locale_text("i18n_battle_misc.source_unknown")
        if source.startswith("enemy:"):
            return source[6:]
        if source.startswith("e"):
            try:
                idx = int(source[1:]) - 1
            except ValueError:
                idx = -1
            if 0 <= idx < len(run.enemies):
                return run.enemies[idx].name
        if source in ("p0", "player", "effect"):
            return get_locale_text("i18n_battle_misc.source_self")
        if source.startswith("a"):
            resolved = self.resolve_ally(run, source)
            if resolved:
                _, ally_player, ally_grid = resolved
                if ally_grid is not None and ally_grid in ally_player.minions:
                    return ally_player.minions[ally_grid].name
                return ally_player.name
        if source.startswith("relic:"):
            return get_locale_text("i18n_battle_misc.source_relic")
        if source == "curse":
            return get_locale_text("i18n_battle_misc.source_curse")
        return source

    def get_first_alive_enemy(self, run: GameRun) -> str:
        for idx, enemy in enumerate(run.enemies, 1):
            if enemy.hp > 0:
                return f"e{idx}"
        return "e1"

    def get_free_grid(self, p: PlayerState) -> Optional[str]:
        for i in range(1, 7):
            s = str(i)
            if s not in p.minions and s not in p.amulets:
                return s
        return None

    def _apply_gem_dmg(self, card: Optional[Card], dmg: int) -> int:
        if card and hasattr(card, "gems") and card.gems:
            add_val = 0
            mul_val = 1
            for g in card.gems:
                if g == "gem_dmg_add_2":
                    add_val += 2
                elif g == "gem_dmg_mul_2":
                    mul_val *= 2
                elif g == "gem_dmg_mul_3":
                    mul_val *= 3
            return (dmg + add_val) * mul_val
        return dmg

    def get_modified_spell_damage(self, run: GameRun, card: Card, damage: int) -> int:
        damage = self._apply_gem_dmg(card, damage)
        dtype = getattr(card, "damage_type", "spell")
        calc_evt = DamageCalculateEvent(run, card, "p0", "e1", dtype, damage, damage)
        self.engine.event_bus.dispatch(calc_evt)
        return calc_evt.modified_damage

    def add_buff_to(self, entity, buff_id: str, buff_name: str, desc: str, count: int = 1, count2: Optional[int] = None, run=None):
        for b in entity.buffs:
            if b.id == buff_id:
                b.stacks += count
                if count2 is not None:
                    if b.stacks2 is None:
                        b.stacks2 = 0
                    b.stacks2 += count2
                if buff_id == "stun" and isinstance(entity, EnemyState):
                    self.engine._sync_enemy_intents(entity)
                self._check_shadow_tentacle(entity, buff_id, run)
                return
        entity.buffs.append(BuffState(buff_id, buff_name, count, count2, desc))
        if buff_id == "stun" and isinstance(entity, EnemyState):
            self.engine._sync_enemy_intents(entity)
        self._check_shadow_tentacle(entity, buff_id, run)

    def _check_shadow_tentacle(self, entity, buff_id: str, run=None):
        from ...models.state import EnemyState
        if run is None:
            run = getattr(self.engine, "current_run", None)
        if not run:
            return
        if isinstance(entity, EnemyState):
            is_negative = buff_id in ("stun", "weak", "electrified", "poison", "agony", "bleed", "void_weakness") or "vulnerable" in buff_id
            if is_negative and run.player and "shadow_tentacle" in run.player.relics:
                self.gain_shield(run, "p0", 2)
                self.engine._log_event(run, get_locale_text("i18n_battle_misc.shadow_tentacle_trigger"))

    def gain_shield(self, run: GameRun, target: str, amount: int):
        if self._redirect_ally(run, target, lambda inner: self.gain_shield(run, inner, amount)):
            return
        if target == "p0":
            cid = run.node_data.get("current_playing_card_cid")
            if cid:
                from ...entities.cards.base import ALL_CARDS
                card = ALL_CARDS.get(cid)
                if card and hasattr(card, "gems") and card.gems:
                    for g in card.gems:
                        if g == "gem_shield_add_3":
                            amount += 3
                        elif g == "gem_shield_add_8":
                            amount += 8
        if run.node_data.get("current_playing_card_cid"):
            run.node_data["card_played_triggered_shield"] = True
        evt = ShieldGainEvent(run, target, amount, amount)
        self.engine.event_bus.dispatch(evt)
        final_amount = evt.modified_amount
        if final_amount <= 0:
            return
        if target == "p0":
            run.player.shield += final_amount
        elif target.startswith("e"):
            try:
                idx = int(target[1:]) - 1
                if idx < 0: idx = 0
            except ValueError:
                idx = 0
            if 0 <= idx < len(run.enemies):
                run.enemies[idx].shield += final_amount

    def heal_target(self, run: GameRun, target: str, heal: int):
        if self._redirect_ally(run, target, lambda inner: self.heal_target(run, inner, heal)):
            return
        if target == "p0" or target.startswith("p"):
            cid = run.node_data.get("current_playing_card_cid")
            if cid:
                from ...entities.cards.base import ALL_CARDS
                card = ALL_CARDS.get(cid)
                if card and hasattr(card, "gems") and card.gems:
                    for g in card.gems:
                        if g == "gem_heal_add_2":
                            heal += 2
        if run.node_data.get("current_playing_card_cid"):
            run.node_data["card_played_triggered_heal"] = True
        heal_evt = HealEvent(run, target, heal)
        self.engine.event_bus.dispatch(heal_evt)
        if heal_evt.cancelled:
            return
        heal = heal_evt.amount
        p = run.player
        if target == "p0":
            calc_evt = HealCalculateEvent(run, "p0", p.max_hp, p.max_hp)
            self.engine.event_bus.dispatch(calc_evt)
            cur_max_hp = calc_evt.modified_max_hp
            p.hp = min(cur_max_hp, p.hp + heal)
        elif target.startswith("p"):
            grid = target[1:]
            if grid in p.minions:
                p.minions[grid].hp = min(p.minions[grid].max_hp, p.minions[grid].hp + heal)
        elif target.startswith("e"):
            try:
                idx = int(target[1:]) - 1
                if idx < 0: idx = 0
            except ValueError:
                idx = 0
            if 0 <= idx < len(run.enemies):
                run.enemies[idx].hp = min(run.enemies[idx].max_hp, run.enemies[idx].hp + heal)

    def recall_dead_minion(self, run: GameRun, hp_limit: int) -> str:
        p = run.player
        from ...entities.cards.base import ALL_CARDS
        eligible = []
        for cid in p.minion_graveyard:
            card = ALL_CARDS.get(cid)
            if card and card.type == "minion":
                hp_val = getattr(card, "minion_hp", 999)
                if hp_val < hp_limit:
                    eligible.append(cid)
        if not eligible:
            return get_locale_text("i18n_battle_misc.recall_no_eligible")
        chosen_cid = random.choice(eligible)
        p.minion_graveyard.remove(chosen_cid)
        card = ALL_CARDS[chosen_cid]
        hp_val = getattr(card, "minion_hp", 10)
        atk_val = getattr(card, "minion_atk", 1)
        grid = self.summon_minion(run, chosen_cid, card.name, hp_val, atk_val, 0)
        if grid:
            return get_locale_text("i18n_battle_misc.recall_success", name=card.name, grid=grid)
        return get_locale_text("i18n_battle_misc.recall_battlefield_full")

    def summon_minion(self, run: GameRun, minion_id: str, name: str, hp: int, atk: int, ba: int) -> Optional[str]:
        grid = self.get_free_grid(run.player)
        if grid:
            m = MinionState(minion_id, name, hp, hp, atk, 1, ba)
            run.player.minions[grid] = m
            evt = MinionSummonEvent(run, m, grid)
            self.engine.event_bus.dispatch(evt)
            return grid
        return None

    def damage_target(self, game_run_context: GameRun, target: str, dmg: int, source: str = "effect", damage_type: str = "effect", card: Optional[Card] = None, damage_ready: bool = False, is_attack: bool = False):
        if self._redirect_ally(
            game_run_context,
            target,
            lambda inner: self.damage_target(game_run_context, inner, dmg, source, damage_type, card, damage_ready, is_attack),
        ):
            return
        target_name = self.get_target_name(game_run_context, target)
        if card is None:
            cid = game_run_context.node_data.get("current_playing_card_cid")
            if cid:
                from ...entities.cards.base import ALL_CARDS
                card = ALL_CARDS.get(cid)
        if game_run_context.node_data.get("current_playing_card_cid"):
            game_run_context.node_data["card_played_triggered_dmg"] = True
        if not damage_ready and source in ("p0", "player", "effect"):
            dmg = self._apply_gem_dmg(card, dmg)
        acting_enemy_idx = game_run_context.node_data.get("current_acting_enemy_idx")
        if acting_enemy_idx is not None and (source.startswith("enemy:") or source in ("effect", "yog_sothoth_passive")):
            source = f"e{acting_enemy_idx+1}"
        elif source.startswith("enemy:"):
            enemy_name = source[6:]
            for i, e in enumerate(game_run_context.enemies):
                if e.name == enemy_name:
                    source = f"e{i+1}"
                    break
        if damage_ready:
            final_dmg = dmg
        else:
            calc_evt = DamageCalculateEvent(game_run_context, card, source, target, damage_type, dmg, dmg, is_attack)
            self.engine.event_bus.dispatch(calc_evt)
            final_dmg = max(0, calc_evt.modified_damage)
        p = game_run_context.player
        if source in ("p0", "player", "effect"):
            resonance_buff = next((b for b in p.buffs if b.id == "all_resonance"), None)
            if resonance_buff:
                stacks = resonance_buff.stacks
                final_dmg = final_dmg * (10 ** stacks)
        if target == "p0" and any(b.id == "antimagic_immune" for b in p.buffs):
            dtype_str = damage_type.value if hasattr(damage_type, "value") else str(damage_type)
            if not is_physical_damage(dtype_str):
                final_dmg = 0
        before_apply_evt = BeforeDamageApplyEvent(game_run_context, card, source, target, damage_type, final_dmg)
        self.engine.event_bus.dispatch(before_apply_evt)
        final_dmg = max(0, before_apply_evt.final_damage)
        is_fatal = False
        is_true = False
        if damage_type == "true" or damage_type == "TRUE":
            is_true = True
        elif hasattr(damage_type, "value") and (damage_type.value == "true" or damage_type.value == "TRUE"):
            is_true = True
        if target == "p0" and final_dmg > 0:
            source_name = self.get_source_name(game_run_context, source)
            game_run_context.node_data["last_damage_source"] = source_name
            game_run_context.node_data["last_damage_type"] = (
                damage_type.value if hasattr(damage_type, "value") else str(damage_type)
            )
        shield_dmg = 0
        hp_dmg = 0
        if target.startswith("e"):
            try:
                idx = int(target[1:]) - 1
                if idx < 0: idx = 0
            except ValueError:
                idx = 0
            if 0 <= idx < len(game_run_context.enemies):
                e = game_run_context.enemies[idx]
                if is_true:
                    hp_dmg = final_dmg
                    e.hp -= final_dmg
                else:
                    if e.shield >= final_dmg:
                        e.shield -= final_dmg
                        shield_dmg = final_dmg
                    else:
                        shield_dmg = e.shield
                        hp_dmg = final_dmg - e.shield
                        e.hp -= hp_dmg
                        e.shield = 0
                if e.hp <= 0:
                    before_death_evt = EnemyBeforeDeathEvent(game_run_context, e)
                    self.engine.event_bus.dispatch(before_death_evt)
                    if before_death_evt.cancelled:
                        pass
                    else:
                        is_fatal = True
                        p.enemy_graveyard.append(e.name)
                        game_run_context.enemies.pop(idx)
                        death_evt = MinionDeathEvent(game_run_context, e.name, target, e.name, True)
                        self.engine.event_bus.dispatch(death_evt)
                take_evt = DamageTakeEvent(game_run_context, source, target, final_dmg, is_fatal, damage_type)
                self.engine.event_bus.dispatch(take_evt)
        elif target == "p0":
            was_alive = p.hp > 0
            game_run_context.node_data["last_shield_before_dmg"] = p.shield
            if final_dmg > 0:
                game_run_context.node_data["player_damaged_this_turn"] = True
            if is_true:
                hp_dmg = final_dmg
                p.hp -= final_dmg
            else:
                if p.shield >= final_dmg:
                    p.shield -= final_dmg
                    shield_dmg = final_dmg
                else:
                    shield_dmg = p.shield
                    hp_dmg = final_dmg - p.shield
                    p.hp -= hp_dmg
                    p.shield = 0
            if p.hp <= 0:
                is_fatal = True
                if was_alive:
                    killer = self.get_source_name(game_run_context, source)
                    if killer == get_locale_text("i18n_battle_misc.source_self"):
                        game_run_context.node_data["death_cause"] = get_locale_text("i18n_battle_misc.death_cause_self")
                    else:
                        game_run_context.node_data["death_cause"] = get_locale_text("i18n_battle_misc.death_cause_enemy", killer=killer)
                from .party_battle import mark_downed
                mark_downed(self.engine, game_run_context, p)
                barrier_buff = next((b for b in p.buffs if b.id in ("prismatic_barrier", "prismatic_barrier_upgraded")), None)
                if barrier_buff:
                    barrier_buff.stacks -= 1
                    is_upg = (barrier_buff.id == "prismatic_barrier_upgraded")
                    if barrier_buff.stacks <= 0:
                        p.buffs.remove(barrier_buff)
                    if source.startswith("e"):
                        ref_dmg = 5 if is_upg else 3
                        barrier_key = "i18n_battle_misc.prismatic_barrier_upgraded_name" if is_upg else "i18n_battle_misc.prismatic_barrier_name"
                        buff_prefix = get_locale_text(barrier_key)
                        self.engine._log_event(game_run_context, get_locale_text("i18n_battle_misc.prismatic_barrier_reflect", buff_prefix=buff_prefix))
                        self.damage_target(game_run_context, source, ref_dmg, source="p0", damage_type="fire")
                        self.damage_target(game_run_context, source, ref_dmg, source="p0", damage_type="cold")
                        self.damage_target(game_run_context, source, ref_dmg, source="p0", damage_type="lightning")
                        self.damage_target(game_run_context, source, ref_dmg, source="p0", damage_type="poison")
            take_evt = DamageTakeEvent(game_run_context, source, target, final_dmg, is_fatal, damage_type)
            self.engine.event_bus.dispatch(take_evt)
        elif target.startswith("p"):
            grid = target[1:]
            if grid in p.minions:
                m = p.minions[grid]
                hp_dmg = final_dmg
                m.hp -= final_dmg
                if m.hp <= 0:
                    is_fatal = True
                    p.minion_graveyard.append(m.id)
                    del p.minions[grid]
                    death_evt = MinionDeathEvent(game_run_context, m.id, target, m.name, False)
                    self.engine.event_bus.dispatch(death_evt)
                    self.engine._reindex_minions(p)
                take_evt = DamageTakeEvent(game_run_context, source, target, final_dmg, is_fatal, damage_type)
                self.engine.event_bus.dispatch(take_evt)
        damage_type_str = damage_type.value if hasattr(damage_type, "value") else str(damage_type)
        type_key = DAMAGE_TYPE_KEYS.get(damage_type_str)
        if type_key is None:
            type_key = "i18n_battle_misc.damage_type_physical" if damage_type_str == "attack" else "i18n_battle_misc.damage_type_special"
        type_name = get_locale_text(type_key)
        log_msg = get_locale_text("i18n_battle_misc.damage_log", target_name=target_name, final_dmg=final_dmg, type_name=type_name)
        if shield_dmg == 0 and hp_dmg == 0:
            log_msg += get_locale_text("i18n_battle_misc.damage_immune", target_name=target_name)
        else:
            if shield_dmg > 0:
                log_msg += get_locale_text("i18n_battle_misc.damage_shield", shield_dmg=shield_dmg)
            if hp_dmg > 0:
                log_msg += get_locale_text("i18n_battle_misc.damage_hp", hp_dmg=hp_dmg)
        self.engine._log_event(game_run_context, log_msg)
