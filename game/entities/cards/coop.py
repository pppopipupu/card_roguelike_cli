from typing import Optional

from ...models.state import Card
from ...data.locale_data import get_locale_text
from .registry import register_card


def _current_uid(run):
    return run.uid_for(run.player)


def _alive_uids(run):
    return [
        uid
        for uid in run.party_order
        if uid in run.players and run.players[uid].hp > 0 and not run.players[uid].downed
    ]


def _target_ref(run, uid, grid=None):
    if uid == _current_uid(run):
        return "p0" if grid is None else f"p{grid}"
    index = run.party_order.index(uid) + 1
    return f"a{index}" if grid is None else f"a{index}p{grid}"


def _resolve_ally(run, target, allow_self=False):
    current = _current_uid(run)
    alive = _alive_uids(run)
    if target:
        text = str(target).strip().lower()
        if text.startswith("t"):
            text = "a" + text[1:]
        if not text.startswith("a"):
            return None
        rest = text[1:]
        grid = None
        if "p" in rest:
            index_text, grid = rest.split("p", 1)
            if not grid.isdigit():
                return None
        else:
            index_text = rest
        if not index_text.isdigit():
            return None
        index = int(index_text) - 1
        if index < 0 or index >= len(run.party_order):
            return None
        uid = run.party_order[index]
        player = run.players.get(uid)
        if player is None or uid not in alive:
            return None
        if uid == current and not allow_self:
            return None
        if grid is not None and grid not in player.minions:
            return None
        return uid, player, grid
    candidates = [uid for uid in alive if uid != current]
    if len(candidates) == 1:
        return candidates[0], run.players[candidates[0]], None
    if not candidates and allow_self and current in alive:
        return current, run.players[current], None
    return None


def _draw_for(engine, run, player, count):
    engine.card_player.draw_cards(player, count, run, ignore_focus=True)


@register_card("coop_tactical_command")
class CoopTacticalCommand(Card):
    def execute(self, run, target, engine) -> str:
        resolved = _resolve_ally(run, target)
        if not resolved:
            return get_locale_text("i18n_cards_neutral.coop.target_required")
        uid, player, grid = resolved
        minion = player.minions.get(grid) if grid else None
        gain_a = getattr(self, "gain_a", 1)
        draw_count = getattr(self, "draw_count", 1)
        if self.upgraded:
            gain_ba = getattr(self, "gain_ba", 2)
            if minion:
                minion.actions += gain_a
                minion.bonus_actions += gain_ba
            else:
                player.actions += gain_a
                player.bonus_actions += gain_ba
            _draw_for(engine, run, player, draw_count)
            _draw_for(engine, run, run.player, draw_count)
            target_name = minion.name if minion else player.name
            return get_locale_text("i18n_cards_neutral.coop.tactical_command.result_upgraded", target_name=target_name, player_name=player.name)
        gain_ba = getattr(self, "gain_ba", 1)
        if minion:
            minion.actions += gain_a
            minion.bonus_actions += gain_ba
            _draw_for(engine, run, player, draw_count)
            return get_locale_text("i18n_cards_neutral.coop.tactical_command.result_minion", minion_name=minion.name)
        player.actions += gain_a
        player.bonus_actions += gain_ba
        _draw_for(engine, run, player, draw_count)
        return get_locale_text("i18n_cards_neutral.coop.tactical_command.result_player", player_name=player.name)


@register_card("coop_phalanx_bulwark")
class CoopPhalanxBulwark(Card):
    def execute(self, run, target, engine) -> str:
        resolved = _resolve_ally(run, target, allow_self=self.upgraded)
        if not resolved:
            return get_locale_text("i18n_cards_neutral.coop.target_required")
        uid, player, grid = resolved
        if grid is not None:
            return get_locale_text("i18n_cards_neutral.coop.phalanx_bulwark.minion_not_allowed")
        resolver = engine.combat_resolver
        shield = getattr(self, "shield_amount", 10 if self.upgraded else 8)
        buff_stacks = getattr(self, "buff_stacks", 1)
        if self.upgraded:
            for member in _alive_uids(run):
                resolver.gain_shield(run, _target_ref(run, member), shield)
        else:
            resolver.gain_shield(run, "p0", shield)
            resolver.gain_shield(run, _target_ref(run, uid, grid), shield)
        resolver.add_buff_to(
            player,
            "coop_aegis",
            get_locale_text("i18n_cards_neutral.neutral.buffs.aegis.name"),
            get_locale_text("i18n_cards_neutral.neutral.buffs.aegis.desc"),
            buff_stacks,
        )
        if self.upgraded:
            return get_locale_text("i18n_cards_neutral.coop.phalanx_bulwark.result_upgraded", shield=shield, player_name=player.name)
        return get_locale_text("i18n_cards_neutral.coop.phalanx_bulwark.result", shield=shield, player_name=player.name)


@register_card("coop_resonance_hymn")
class CoopResonanceHymn(Card):
    def execute(self, run, target, engine) -> str:
        resolved = _resolve_ally(run, target, allow_self=self.upgraded)
        if not resolved:
            return get_locale_text("i18n_cards_neutral.coop.target_required")
        uid, player, grid = resolved
        resolver = engine.combat_resolver
        strength_stacks = getattr(self, "strength_gain", 2)
        charge_stacks = getattr(self, "buff_stacks", 1)
        if self.upgraded:
            members = _alive_uids(run)
            for member in members:
                ally = run.players[member]
                resolver.add_buff_to(ally, "strength", get_locale_text("i18n_cards_neutral.neutral.buffs.strength.name"), get_locale_text("i18n_cards_neutral.neutral.buffs.strength.desc"), strength_stacks)
                resolver.add_buff_to(ally, "arcane_charge", get_locale_text("i18n_cards_neutral.neutral.buffs.arcane_charge.name"), get_locale_text("i18n_cards_neutral.neutral.buffs.arcane_charge.desc"), charge_stacks)
            draw_count = getattr(self, "draw_count", 1)
            _draw_for(engine, run, run.player, draw_count)
            return get_locale_text("i18n_cards_neutral.coop.resonance_hymn.result_upgraded", count=len(members))
        target_entity = player.minions.get(grid) if grid else player
        resolver.add_buff_to(target_entity, "strength", get_locale_text("i18n_cards_neutral.neutral.buffs.strength.name"), get_locale_text("i18n_cards_neutral.neutral.buffs.strength.desc"), strength_stacks)
        resolver.add_buff_to(target_entity, "arcane_charge", get_locale_text("i18n_cards_neutral.neutral.buffs.arcane_charge.name"), get_locale_text("i18n_cards_neutral.neutral.buffs.arcane_charge.desc"), charge_stacks)
        target_name = target_entity.name if target_entity is not player else player.name
        return get_locale_text("i18n_cards_neutral.coop.resonance_hymn.result", target_name=target_name)


@register_card("coop_soul_link")
class CoopSoulLink(Card):
    def execute(self, run, target, engine) -> str:
        resolved = _resolve_ally(run, target)
        if not resolved:
            return get_locale_text("i18n_cards_neutral.coop.target_required")
        uid, player, grid = resolved
        if grid is not None:
            return get_locale_text("i18n_cards_neutral.coop.soul_link.minion_not_allowed")
        if self.upgraded:
            heal = getattr(self, "heal_amount", 9)
            stacks = getattr(self, "buff_stacks", 3)
            bonus = getattr(self, "bonus_damage", 6)
            restore = getattr(self, "restore_amount", 3)
        else:
            heal = getattr(self, "heal_amount", 6)
            stacks = getattr(self, "buff_stacks", 2)
            bonus = getattr(self, "bonus_damage", 4)
            restore = getattr(self, "restore_amount", 2)
        engine.combat_resolver.heal_target(run, _target_ref(run, uid, grid), heal)
        engine.combat_resolver.add_buff_to(
            player,
            "coop_soul_resonance",
            get_locale_text("i18n_cards_neutral.coop.soul_link.buff_name"),
            get_locale_text("i18n_cards_neutral.coop.soul_link.buff_desc", stacks=stacks, bonus=bonus, restore=restore),
            stacks,
        )
        for buff in player.buffs:
            if buff.id == "coop_soul_resonance":
                buff.source_uid = _current_uid(run)
                buff.stacks2 = bonus
        return get_locale_text("i18n_cards_neutral.coop.soul_link.result", player_name=player.name, heal=heal, stacks=stacks, bonus=bonus, restore=restore)


@register_card("coop_unison_crusade")
class CoopUnisonCrusade(Card):
    def execute(self, run, target, engine) -> str:
        alive = _alive_uids(run)
        count = max(1, len(alive))
        draw_count = getattr(self, "draw_count", 2 if self.upgraded else 1)
        gain_a = getattr(self, "gain_a", 1)
        gain_ba = getattr(self, "gain_ba", 1)
        for member in alive:
            ally = run.players[member]
            _draw_for(engine, run, ally, draw_count)
            if self.upgraded:
                ally.actions += gain_a
            else:
                ally.bonus_actions += gain_ba
        enemy_target = target
        if not enemy_target or not str(enemy_target).startswith("e"):
            enemy_target = engine._get_first_alive_enemy(run)
        try:
            index = int(str(enemy_target)[1:]) - 1
        except ValueError:
            index = 0
        if index < 0 or index >= len(run.enemies):
            return get_locale_text("i18n_cards_neutral.coop.unison_crusade.no_target")
        target_enemy = run.enemies[index]
        target_name = target_enemy.name
        damage_per_member = getattr(self, "base_dmg", 12 if self.upgraded else 8)
        damage = count * damage_per_member
        engine.combat_resolver.damage_target(run, f"e{index + 1}", damage, source="p0", damage_type="force")
        buff_id = "vulnerable" if self.upgraded else "minor_vulnerable"
        buff_name = get_locale_text("i18n_cards_neutral.neutral.buffs.vulnerable.name") if self.upgraded else get_locale_text("i18n_cards_neutral.neutral.buffs.minor_vulnerable.name")
        if any(enemy is target_enemy for enemy in run.enemies) and target_enemy.hp > 0:
            engine.combat_resolver.add_buff_to(
                target_enemy,
                buff_id,
                buff_name,
                get_locale_text("i18n_cards_neutral.neutral.buffs.vulnerable.desc") if self.upgraded else get_locale_text("i18n_cards_neutral.neutral.buffs.minor_vulnerable.desc"),
                count,
            )
        action_text = "1A" if self.upgraded else "1BA"
        if self.upgraded:
            return get_locale_text("i18n_cards_neutral.coop.unison_crusade.result_upgraded", count=count, draw_count=draw_count, action_text=action_text, target_name=target_name, damage=damage, buff_name=buff_name)
        return get_locale_text("i18n_cards_neutral.coop.unison_crusade.result", count=count, draw_count=draw_count, action_text=action_text, target_name=target_name, damage=damage, buff_name=buff_name)
