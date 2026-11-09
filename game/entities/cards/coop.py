from typing import Optional

from ...models.state import Card
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
            return "❌ 请指定一名存活队友，例如：使用 1 a2。"
        uid, player, grid = resolved
        minion = player.minions.get(grid) if grid else None
        if self.upgraded:
            if minion:
                minion.actions += 1
                minion.bonus_actions += 2
            else:
                player.actions += 1
                player.bonus_actions += 2
            _draw_for(engine, run, player, 1)
            _draw_for(engine, run, run.player, 1)
            target_name = minion.name if minion else player.name
            return (
                f"🎯 【战术指挥+】指挥【{target_name}】获得 1A 与 2BA，"
                f"你与【{player.name}】各抽 1 张牌。"
            )
        if minion:
            minion.actions += 1
            minion.bonus_actions += 1
            _draw_for(engine, run, player, 1)
            return f"🎯 【战术指挥】指挥随从【{minion.name}】获得 1A 与 1BA，其主人抽取 1 张牌。"
        player.actions += 1
        player.bonus_actions += 1
        _draw_for(engine, run, player, 1)
        return f"🎯 【战术指挥】指挥【{player.name}】获得 1A 与 1BA，并抽取 1 张牌。"


@register_card("coop_phalanx_bulwark")
class CoopPhalanxBulwark(Card):
    def execute(self, run, target, engine) -> str:
        resolved = _resolve_ally(run, target, allow_self=self.upgraded)
        if not resolved:
            return "❌ 请指定一名存活队友，例如：使用 1 a2。"
        uid, player, grid = resolved
        if grid is not None:
            return "❌ 【方阵掩护】只能指定队友本人，不能指定随从。"
        resolver = engine.combat_resolver
        if self.upgraded:
            shield = 10
            for member in _alive_uids(run):
                resolver.gain_shield(run, _target_ref(run, member), shield)
        else:
            shield = 8
            resolver.gain_shield(run, "p0", shield)
            resolver.gain_shield(run, _target_ref(run, uid, grid), shield)
        resolver.add_buff_to(
            player,
            "coop_aegis",
            "援护",
            "本回合受到的单体攻击伤害降低 25%，回合开始时移除。",
            1,
        )
        if self.upgraded:
            return f"🛡️ 【方阵掩护+】你与全体存活队友各获得 {shield} 点护盾，【{player.name}】获得 1 层【援护】。"
        return f"🛡️ 【方阵掩护】你与【{player.name}】各获得 {shield} 点护盾，【{player.name}】获得 1 层【援护】。"


@register_card("coop_resonance_hymn")
class CoopResonanceHymn(Card):
    def execute(self, run, target, engine) -> str:
        resolved = _resolve_ally(run, target, allow_self=self.upgraded)
        if not resolved:
            return "❌ 请指定一名存活队友，例如：使用 1 a2。"
        uid, player, grid = resolved
        resolver = engine.combat_resolver
        if self.upgraded:
            members = _alive_uids(run)
            for member in members:
                ally = run.players[member]
                resolver.add_buff_to(ally, "strength", "力量", "造成的伤害增加", 2)
                resolver.add_buff_to(ally, "arcane_charge", "奥术充能", "法术伤害 +3", 1)
            _draw_for(engine, run, run.player, 1)
            return f"🎵 【共鸣圣歌+】全体 {len(members)} 名存活队友获得 2 层【力量】与 1 层【奥术充能】，你抽取 1 张牌。"
        target_entity = player.minions.get(grid) if grid else player
        resolver.add_buff_to(target_entity, "strength", "力量", "造成的伤害增加", 2)
        resolver.add_buff_to(target_entity, "arcane_charge", "奥术充能", "法术伤害 +3", 1)
        target_name = target_entity.name if target_entity is not player else player.name
        return f"🎵 【共鸣圣歌】为【{target_name}】付与 2 层【力量】与 1 层【奥术充能】。"


@register_card("coop_soul_link")
class CoopSoulLink(Card):
    def execute(self, run, target, engine) -> str:
        resolved = _resolve_ally(run, target)
        if not resolved:
            return "❌ 请指定一名存活队友，例如：使用 1 a2。"
        uid, player, grid = resolved
        if grid is not None:
            return "❌ 【灵魂链接】只能指定队友本人，不能指定随从。"
        if self.upgraded:
            heal = 9
            stacks = 3
            bonus = 6
            restore = 3
        else:
            heal = 6
            stacks = 2
            bonus = 4
            restore = 2
        engine.combat_resolver.heal_target(run, _target_ref(run, uid, grid), heal)
        engine.combat_resolver.add_buff_to(
            player,
            "coop_soul_resonance",
            "灵魂共鸣",
            f"下 {stacks} 次打出的攻击或法术牌伤害额外 +{bonus}，每次触发为链接者恢复 {restore} 点生命。",
            stacks,
        )
        for buff in player.buffs:
            if buff.id == "coop_soul_resonance":
                buff.source_uid = _current_uid(run)
                buff.stacks2 = bonus
        return (
            f"🔗 【灵魂链接】为【{player.name}】恢复 {heal} 点生命，"
            f"并赋予 {stacks} 层【灵魂共鸣】（伤害 +{bonus}，每次触发为你恢复 {restore} 点生命）。"
        )


@register_card("coop_unison_crusade")
class CoopUnisonCrusade(Card):
    def execute(self, run, target, engine) -> str:
        alive = _alive_uids(run)
        count = max(1, len(alive))
        draw_count = 2 if self.upgraded else 1
        for member in alive:
            ally = run.players[member]
            _draw_for(engine, run, ally, draw_count)
            if self.upgraded:
                ally.actions += 1
            else:
                ally.bonus_actions += 1
        enemy_target = target
        if not enemy_target or not str(enemy_target).startswith("e"):
            enemy_target = engine._get_first_alive_enemy(run)
        try:
            index = int(str(enemy_target)[1:]) - 1
        except ValueError:
            index = 0
        if index < 0 or index >= len(run.enemies):
            return "❌ 敌方目标不存在。"
        target_enemy = run.enemies[index]
        target_name = target_enemy.name
        damage = count * (12 if self.upgraded else 8)
        engine.combat_resolver.damage_target(run, f"e{index + 1}", damage, source="p0", damage_type="force")
        buff_id = "vulnerable" if self.upgraded else "minor_vulnerable"
        buff_name = "易伤" if self.upgraded else "轻度易伤"
        if any(enemy is target_enemy for enemy in run.enemies) and target_enemy.hp > 0:
            engine.combat_resolver.add_buff_to(
                target_enemy,
                buff_id,
                buff_name,
                "受到的所有类型伤害翻倍" if self.upgraded else "受到的所有类型伤害增加 50%",
                count,
            )
        action_text = "1A" if self.upgraded else "1BA"
        return (
            f"⚔️ 【同心协力{'+' if self.upgraded else ''}】全体 {count} 名存活队友各抽 {draw_count} 张牌并获得 {action_text}，"
            f"对【{target_name}】造成 {damage} 点力场伤害，"
            f"并施加 {count} 层【{buff_name}】。"
        )
