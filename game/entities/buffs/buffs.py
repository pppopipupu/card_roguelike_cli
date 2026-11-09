from typing import List, Optional
import re
from .base import BuffImpl, is_debuff
from .registry import register_buff

class QuickenBuff(BuffImpl):
    def on_card_play(self, event, buff_state, entity):
        if entity == event.run.player and event.card.type == "spell":
            event.cost_ba = max(0, event.cost_ba - buff_state.stacks)

    def modify_spell_cost_ba(self, run, card, cost_ba: int, engine) -> int:
        if card.type == "spell":
            return max(0, cost_ba - self.stacks)
        return cost_ba

class SpellSurgeBuff(BuffImpl):
    def on_card_played(self, event, buff_state, entity):
        if entity == event.run.player and event.card.color == "wizard":
            event.engine._draw_cards(event.run.player, buff_state.stacks, event.run)

    def on_card_played_legacy(self, run, card, target: str, engine) -> str:
        if card.color == "wizard":
            engine._draw_cards(run.player, self.stacks, run)
        return ""

class ArcaneChargeBuff(BuffImpl):
    def on_damage_calculate(self, event, buff_state, entity):
        if entity == event.run.player and event.damage_type == "spell" and event.source == "p0":
            event.modified_damage += buff_state.stacks * 3

    def modify_spell_damage(self, run, card, damage: int, engine) -> int:
        return damage + self.stacks * 3

class EchoFormBuff(BuffImpl):
    def on_card_played(self, event, buff_state, entity):
        if entity != event.run.player:
            return
        if getattr(event, "is_extra", False):
            return
        played_count = event.run.node_data.get("cards_played_this_turn", 0)
        stacks = buff_state.stacks
        card_id = event.card.id
        if card_id.startswith("duel_"):
            card_id = card_id[5:]
        if card_id.startswith("echo_form"):
            stacks = max(0, stacks - 1)
        num_echoes = min(5, max(0, stacks - 5 * played_count))
        if num_echoes > 0:
            for _ in range(num_echoes):
                if event.engine.is_battle_won(event.run):
                    break
                extra_res = event.engine._execute_card_effect(event.run, event.card, event.target)
                from ...models.events import CardPlayedEvent
                played_evt = CardPlayedEvent(event.run, event.card, event.target, extra_res, is_extra=True)
                event.engine.event_bus.dispatch(played_evt)
                event.run.node_data.setdefault("extra_play_msgs", []).append(f" 🔁 [回响触发] {played_evt.feedback}")
                if hasattr(event.card, "execute_tags"):
                    event.card.execute_tags(event.run, event.target, event.engine)

    def on_card_played_legacy(self, run, card, target: str, engine) -> str:
        played_count = run.node_data.get("cards_played_this_turn", 0)
        stacks = self.stacks
        card_id = card.id
        if card_id.startswith("duel_"):
            card_id = card_id[5:]
        if card_id.startswith("echo_form"):
            stacks = max(0, stacks - 1)
        num_echoes = min(5, max(0, stacks - 5 * played_count))
        res = ""
        if num_echoes > 0:
            for _ in range(num_echoes):
                if engine.is_battle_won(run):
                    break
                extra_res = engine._execute_card_effect(run, card, target)
                run.node_data.setdefault("extra_play_msgs", []).append(f" 🔁 [回响触发] {extra_res}")
                if hasattr(card, "execute_tags"):
                    card.execute_tags(run, target, engine)
        return ""

class IronWillBuff(BuffImpl):
    def on_heal(self, event, buff_state, entity):
        if event.target == "p0":
            if buff_state.stacks2 is not None and buff_state.stacks2 > 0:
                event.amount = event.amount * 2
            p = event.run.player
            val = 15 if self.upgraded else 10
            limit = p.max_hp + buff_state.stacks * val
            if p.hp + event.amount > limit:
                event.amount = max(0, limit - p.hp)

    def on_heal_calculate(self, event, buff_state, entity):
        if event.target == "p0":
            val = 15 if self.upgraded else 10
            event.modified_max_hp = event.modified_max_hp + buff_state.stacks * val

    def on_turn_end(self, event, buff_state, entity):
        if entity == event.run.player and event.is_player:
            if buff_state.stacks2 is not None and buff_state.stacks2 > 0:
                buff_state.stacks2 -= 1

class MagicNetworkBuff(BuffImpl):
    def on_card_played(self, event, buff_state, entity):
        if entity == event.run.player and event.card.type == "spell":
            for idx, enemy in enumerate(list(event.run.enemies)):
                event.engine._damage_target(event.run, f"e{idx+1}", 3)
            event.run.player.shield += 3
            event.feedback += " ⚡ [魔网天成] 对所有敌人造成了 3 点伤害，获得了 3 点护盾。"

    def on_card_played_legacy(self, run, card, target: str, engine) -> str:
        res = ""
        if card.type == "spell":
            for enemy in list(run.enemies):
                engine._damage_target(run, f"e{run.enemies.index(enemy)+1}", 3)
            run.player.shield += 3
            res = " ⚡ [魔网天成] 对所有敌人造成了 3 点伤害，获得了 3 点护盾。"
        return res

    def on_player_turn_end(self, run, buff_state, engine):
        if buff_state in run.player.buffs:
            run.player.buffs.remove(buff_state)

    def on_turn_end(self, event, buff_state, entity):
        if entity == event.run.player:
            if buff_state in event.run.player.buffs:
                event.run.player.buffs.remove(buff_state)

class WishPowerBuff(BuffImpl):
    def on_damage_calculate(self, event, buff_state, entity):
        if entity == event.run.player and event.damage_type == "spell" and event.source == "p0":
            val = 6 if self.upgraded else 4
            event.modified_damage += buff_state.stacks * val

    def modify_spell_damage(self, run, card, damage: int, engine) -> int:
        val = 6 if self.upgraded else 4
        return damage + self.stacks * val

class StrengthBuff(BuffImpl):
    def on_damage_calculate(self, event, buff_state, entity):
        is_owner = False
        if entity == event.run.player:
            if event.source == "p0":
                is_owner = True
        elif entity in event.run.enemies:
            try:
                idx = event.run.enemies.index(entity)
                if event.source == f"e{idx+1}":
                    is_owner = True
            except ValueError:
                pass
        if is_owner:
            dtype_str = event.damage_type.value if hasattr(event.damage_type, "value") else str(event.damage_type)
            is_astral_strike = False
            if entity == event.run.player and event.card:
                card_id = event.card.id
                if card_id.startswith("duel_"):
                    card_id = card_id[5:]
                if card_id == "neutral_astral_strike":
                    is_astral_strike = True
            if dtype_str in ("slashing", "bludgeoning", "piercing") or is_astral_strike:
                mult = 1
                if entity == event.run.player and event.card:
                    card_id = event.card.id
                    if card_id.startswith("duel_"):
                        card_id = card_id[5:]
                    if card_id.startswith("heavy_blade"):
                        mult = 5 if event.card.upgraded else 3
                    elif card_id == "neutral_astral_strike":
                        mult = 5 if event.card.upgraded else 4
                event.modified_damage += buff_state.stacks * mult

class FlameBarrierBuff(BuffImpl):
    def on_damage_take_defend(self, event, buff_state, entity, engine):
        if entity == event.run.player and event.target == "p0" and event.source.startswith("e"):
            engine._damage_target(event.run, event.source, buff_state.stacks, damage_type="fire")
            engine._log_event(event.run, f"🔥 [火焰屏障] 对攻击源造成了 {buff_state.stacks} 点反弹火焰伤害。")

    def on_turn_start(self, event, buff_state, entity):
        if event.is_player == (entity == event.run.player):
            if buff_state in entity.buffs:
                entity.buffs.remove(buff_state)

class MetallicizeBuff(BuffImpl):
    def on_turn_end(self, event, buff_state, entity):
        if entity == event.run.player and event.is_player:
            shield_gain = buff_state.stacks
            event.engine._gain_shield(event.run, "p0", shield_gain)
            event.engine._log_event(event.run, f"🛡️ [金属化] 触发：玩家获得了 {shield_gain} 点额外护盾。")

class DemonFormBuff(BuffImpl):
    def on_turn_start(self, event, buff_state, entity):
        if entity == event.run.player and event.is_player:
            amount = buff_state.stacks
            event.engine._add_buff_to(entity, "strength", "力量", "造成的伤害增加", amount)
            event.engine._log_event(event.run, f"😈 [恶魔形态] 触发：玩家获得了 {amount} 点力量。")

class DoubleTapBuff(BuffImpl):
    def on_card_played(self, event, buff_state, entity):
        if entity == event.run.player:
            dtype = getattr(event.card, "damage_type", "spell")
            if dtype in ("slashing", "bludgeoning", "piercing"):
                stacks = buff_state.stacks
                for _ in range(stacks):
                    if event.engine.is_battle_won(event.run):
                        break
                    extra_res = event.engine._execute_card_effect(event.run, event.card, event.target)
                    event.run.node_data.setdefault("extra_play_msgs", []).append(f" 🔁 [双发触发] {extra_res}")
                if buff_state in event.run.player.buffs:
                    event.run.player.buffs.remove(buff_state)

    def on_turn_end(self, event, buff_state, entity):
        if entity == event.run.player and event.is_player:
            if buff_state in event.run.player.buffs:
                event.run.player.buffs.remove(buff_state)

class FuryBuff(BuffImpl):
    def on_card_played(self, event, buff_state, entity):
        if event.card.rarity in ("rare", "legendary", "mythic", "artifact"):
            event.engine._add_buff_to(entity, "strength", "力量", "造成的伤害增加", buff_state.stacks)
            event.engine._log_event(event.run, f"🔥 【{entity.name}】的【愤怒】被玩家的【{event.card.name}】激怒，力量增加了 {buff_state.stacks} 点！")

class FireGrowBuff(BuffImpl):
    def on_damage_calculate(self, event, buff_state, entity):
        if entity == event.run.player and event.damage_type == "fire" and event.source == "p0":
            event.modified_damage += buff_state.stacks

    def modify_spell_damage(self, run, card, damage: int, engine) -> int:
        if getattr(card, "damage_type", "") == "fire":
            return damage + self.stacks
        return damage

class ForgeBackfireBuff(BuffImpl):
    def on_damage_calculate(self, event, buff_state, entity):
        if entity == event.run.player and event.damage_type == "spell" and event.source == "p0":
            event.modified_damage = max(0, event.modified_damage - buff_state.stacks)

    def modify_spell_damage(self, run, card, damage: int, engine) -> int:
        return max(0, damage - self.stacks)

    def on_turn_end(self, event, buff_state, entity):
        if entity == event.run.player:
            buff_state.stacks -= 1
            if buff_state.stacks <= 0:
                event.run.player.buffs.remove(buff_state)

class TimeWarpSpellBoostBuff(BuffImpl):
    def on_damage_calculate(self, event, buff_state, entity):
        if entity == event.run.player and event.damage_type == "spell" and event.source == "p0":
            event.modified_damage += buff_state.stacks * 2

    def modify_spell_damage(self, run, card, damage: int, engine) -> int:
        return damage + self.stacks * 2

    def on_turn_end(self, event, buff_state, entity):
        if entity == event.run.player:
            if buff_state in event.run.player.buffs:
                event.run.player.buffs.remove(buff_state)

class LightningShieldBuff(BuffImpl):
    def on_damage_calculate_defend(self, event, buff_state, entity):
        if event.source == "p0" and event.modified_damage > 0:
            run = event.run
            engine = event.engine
            engine._damage_target(run, "p0", 2 * buff_state.stacks, source=f"buff:{entity.name}", damage_type="lightning")
            engine._add_buff_to(run.player, "shock", "电击", "受到的闪电和雷鸣伤害每层增加 1 点", 1)

    def on_turn_start(self, event, buff_state, entity):
        if not event.is_player and entity in event.run.enemies:
            if buff_state in entity.buffs:
                entity.buffs.remove(buff_state)

class ResistBuff(BuffImpl):
    auto_register = False
    def __init__(self, stacks: int, damage_type: str):
        super().__init__(stacks)
        self.damage_type = damage_type

    def on_damage_calculate_defend(self, event, buff_state, entity):
        dtype_str = event.damage_type.value if hasattr(event.damage_type, "value") else str(event.damage_type)
        if dtype_str == self.damage_type and dtype_str != "true":
            event.modified_damage = int(event.modified_damage * 0.5)

    def on_turn_start(self, event, buff_state, entity):
        if event.is_player == (entity == event.run.player):
            buff_state.stacks -= 1
            if buff_state.stacks <= 0:
                if buff_state in entity.buffs:
                    entity.buffs.remove(buff_state)

class ImmuneBuff(BuffImpl):
    auto_register = False
    def __init__(self, stacks: int, damage_type: str):
        super().__init__(stacks)
        self.damage_type = damage_type

    def on_damage_calculate_defend(self, event, buff_state, entity):
        dtype_str = event.damage_type.value if hasattr(event.damage_type, "value") else str(event.damage_type)
        if dtype_str == self.damage_type and dtype_str != "true":
            event.modified_damage = 0

    def on_turn_start(self, event, buff_state, entity):
        if event.is_player == (entity == event.run.player):
            buff_state.stacks -= 1
            if buff_state.stacks <= 0:
                if buff_state in entity.buffs:
                    entity.buffs.remove(buff_state)

class KeyScholarPassiveBuff(BuffImpl):
    def on_card_played(self, event, buff_state, entity):
        if entity == event.run.player and event.card.type == "amulet":
            event.engine._heal_target(event.run, "p0", 3)
            event.engine._gain_shield(event.run, "p0", 4)
            event.feedback += " 🚪 [门扉共鸣] 回复了 3 点生命值并获得了 4 点护盾。"

class AncientProtectionBuff(BuffImpl):
    def on_turn_start(self, event, buff_state, entity):
        if not event.is_player and entity.shield > 0:
            to_remove = []
            for b in entity.buffs:
                if is_debuff(b.id):
                    to_remove.append(b)
            for b in to_remove:
                entity.buffs.remove(b)
            event.engine._log_event(event.run, f"🛡️ 【{entity.name}】触发【先古庇护】：清除了所有负面效果！")

    def on_damage_calculate_defend(self, event, buff_state, entity):
        if event.modified_damage > 0 and entity.shield > 0:
            recoil_dmg = max(1, int(event.modified_damage * 0.20))
            event.engine._damage_target(event.run, "p0", recoil_dmg, source=f"buff:{entity.name}", damage_type="force")
            event.engine._log_event(event.run, f"⚡ 【{entity.name}】的反弹结界触发，对玩家反弹了 {recoil_dmg} 点力场伤害！")

class EndGatePassiveBuff(BuffImpl):
    def on_turn_start(self, event, buff_state, entity):
        if not event.is_player:
            entity.shield += 15
            to_remove = []
            for b in entity.buffs:
                if is_debuff(b.id):
                    to_remove.append(b)
            for b in to_remove:
                entity.buffs.remove(b)
            event.engine._log_event(event.run, f"🚪 【{entity.name}】触发【终焉之门】：获得 15 护盾并清除了所有负面效果！")

    def on_damage_calculate_defend(self, event, buff_state, entity):
        if event.modified_damage > 0 and entity.shield > 0:
            event.engine._damage_target(event.run, "p0", 1, source=f"buff:{entity.name}", damage_type="true")
            event.engine._log_event(event.run, f"⚡ 【{entity.name}】的终焉结界触发，对玩家反弹了 1 点真实伤害！")

class DoomsdayGatePassiveBuff(BuffImpl):
    def on_turn_start(self, event, buff_state, entity):
        if not event.is_player:
            entity.shield += 20
            event.engine._add_buff_to(entity, "strength", "力量", "造成的伤害增加", 2)
            event.engine._log_event(event.run, f"🌌 【{entity.name}】触发【终焉庇护】：获得了 20 点护盾与 2 层力量！")

    def on_damage_calculate_defend(self, event, buff_state, entity):
        if event.modified_damage > 0 and entity.shield > 0:
            event.engine._damage_target(event.run, "p0", 1, source=f"buff:{entity.name}", damage_type="true")
            event.engine._damage_target(event.run, "p0", 2, source=f"buff:{entity.name}", damage_type="force")
            event.engine._log_event(event.run, f"⚡ 【{entity.name}】的终焉结界触发，对玩家反弹了 1 点真实伤害与 2 点力场伤害！")


class AncientWisdomBuff(BuffImpl):
    def on_card_played(self, event, buff_state, entity):
        if entity == event.run.player and event.card.color == "neutral":
            coef = 3 if self.upgraded else 2
            shield_gain = buff_state.stacks * coef
            event.engine._gain_shield(event.run, "p0", shield_gain)
            event.feedback += f" 🛡️ [古老智慧] 获得了 {shield_gain} 点护盾。"

class BufferBuff(BuffImpl):
    def on_damage_calculate_defend(self, event, buff_state, entity):
        if event.modified_damage > 0:
            damage_type = event.damage_type
            is_true = False
            if damage_type == "true" or damage_type == "TRUE":
                is_true = True
            elif hasattr(damage_type, "value") and (damage_type.value == "true" or damage_type.value == "TRUE"):
                is_true = True
            if is_true or event.modified_damage > entity.shield:
                event.modified_damage = 0
                buff_state.stacks -= 1
                name = "玩家" if entity == event.run.player else getattr(entity, "name", "未知")
                event.engine._log_event(event.run, f"🛡️ 【{name}】的【缓冲】消耗了 1 层，免疫了本次伤害。")
                if buff_state.stacks <= 0:
                    if buff_state in entity.buffs:
                        entity.buffs.remove(buff_state)

class DemonContractBuff(BuffImpl):
    def on_card_played(self, event, buff_state, entity):
        if entity == event.run.player and event.card.type == "spell":
            card_id = event.card.id
            if card_id.startswith("duel_"):
                card_id = card_id[5:]
            if not card_id.startswith("demon_contract"):
                stacks = buff_state.stacks
            for _ in range(stacks):
                if event.engine.is_battle_won(event.run):
                    break
                extra_res = event.engine._execute_card_effect(event.run, event.card, event.target)
                event.run.node_data.setdefault("extra_play_msgs", []).append(f" 🔁 [契约回响] {extra_res}")
            if buff_state in event.run.player.buffs:
                event.run.player.buffs.remove(buff_state)

    def on_turn_end(self, event, buff_state, entity):
        if entity == event.run.player and event.is_player:
            if buff_state in event.run.player.buffs:
                event.run.player.buffs.remove(buff_state)

class GlacierFortressBuff(BuffImpl):
    def on_turn_end(self, event, buff_state, entity):
        if entity == event.run.player and event.is_player:
            coef = 6 if self.upgraded else 4
            shield_gain = buff_state.stacks * coef
            event.engine._gain_shield(event.run, "p0", shield_gain)
            event.engine._log_event(event.run, f"🏔️ [冰川壁垒] 触发：玩家获得了 {shield_gain} 点额外护盾。")

class WishPowerBuff(BuffImpl):
    def on_damage_calculate(self, event, buff_state, entity):
        if entity == event.run.player and event.card.type == "spell":
            val = 6 if self.upgraded else 4
            event.modified_damage += val

@register_buff("commander_aurora_emperor")
class AuroraEmperorBuff(BuffImpl):
    def on_damage_calculate(self, event, buff_state, entity):
        if event.source.startswith("p") and event.source != "p0" and event.damage_type == "attack":
            shield = 3 if self.upgraded else 2
            event.engine._gain_shield(event.run, "p0", shield)
            msg = f"🛡️ [极光圣域] 我方随从发起攻击，玩家获得 {shield} 点护盾。"
            if self.upgraded:
                event.engine._draw_cards(event.run.player, 1, event.run)
                msg = f"🛡️ [极光圣域+] 我方随从发起攻击，玩家获得 {shield} 点护盾并抽取 1 张牌。"
            event.engine._log_event(event.run, msg)

class HellRaiderBuff(BuffImpl):
    pass

class PrismaticBarrierBuff(BuffImpl):
    pass

class AntimagicImmuneBuff(BuffImpl):
    def on_turn_end(self, event, buff_state, entity):
        if buff_state in entity.buffs:
            entity.buffs.remove(buff_state)


class RitualBuff(BuffImpl):
    def on_turn_start(self, event, buff_state, entity):
        if not event.is_player:
            event.engine._add_buff_to(entity, "strength", "力量", "造成的伤害增加", buff_state.stacks)
            event.engine._log_event(event.run, f"[仪式] 触发：【{entity.name}】获得了 {buff_state.stacks} 点力量。")


class GrappledBuff(BuffImpl):
    def on_turn_end(self, event, buff_state, entity):
        if event.is_player and entity == event.run.player:
            buff_state.stacks -= 1
            if buff_state.stacks <= 0:
                if buff_state in entity.buffs:
                    entity.buffs.remove(buff_state)


class AstralSpeedBuff(BuffImpl):
    pass

class SourceOfCinderBuff(BuffImpl):
    def on_turn_start(self, event, buff_state, entity):
        if entity == event.run.player and event.is_player:
            event.run.player.actions += buff_state.stacks
            event.run.player.bonus_actions += buff_state.stacks
            event.engine._log_event(event.run, f"🔥 [薪火之源] 触发！本回合额外获得 {buff_state.stacks}A {buff_state.stacks}BA！")


class UnyieldingBuff(BuffImpl):
    def on_damage_calculate_defend(self, event, buff_state, entity):
        dtype_str = event.damage_type.value if hasattr(event.damage_type, "value") else str(event.damage_type)
        if dtype_str == "true" or dtype_str == "TRUE":
            return
        already_taken = getattr(buff_state, "already_taken", 0)
        limit = buff_state.stacks
        allowed_remaining = max(0, limit - already_taken)
        if event.modified_damage > allowed_remaining:
            event.modified_damage = allowed_remaining

    def on_damage_take_defend(self, event, buff_state, entity, engine):
        dtype_str = event.damage_type.value if hasattr(event.damage_type, "value") else str(event.damage_type)
        if dtype_str == "true" or dtype_str == "TRUE":
            return
        already_taken = getattr(buff_state, "already_taken", 0)
        buff_state.already_taken = already_taken + event.amount

    def on_turn_end(self, event, buff_state, entity):
        buff_state.already_taken = 0


class TimeLordPassiveBuff(BuffImpl):
    def on_turn_start(self, event, buff_state, entity):
        if not event.is_player:
            entity.shield += 20
            to_remove = []
            for b in entity.buffs:
                if is_debuff(b.id):
                    to_remove.append(b)
            for b in to_remove:
                entity.buffs.remove(b)
            event.engine._log_event(event.run, f"⏳ 【{entity.name}】触发【时空主宰】：获得 20 护盾并清除了所有负面效果！")
            
            active_echoes = [e for e in event.run.enemies if e.name == "时空残影" and e.hp > 0]
            if len(active_echoes) < 1 and len(event.run.enemies) < 3:
                import random
                if random.random() < 0.5:
                    from ...models.state import EnemyState
                    echo_enemy = EnemyState(
                        name="时空残影",
                        hp=15,
                        max_hp=15,
                        shield=0,
                        actions=1,
                        bonus_actions=0,
                        max_actions=1,
                        max_bonus_actions=0
                    )
                    event.run.enemies.append(echo_enemy)
                    event.engine._log_event(event.run, "⏳ 亚弗戈蒙的时空波动爆发，从时间的褶皱中召唤出了【时空残影】！")

    def on_damage_calculate_defend(self, event, buff_state, entity):
        if event.modified_damage > 0:
            active_echoes = [e for e in event.run.enemies if e.name == "时空残影" and e.hp > 0]
            if active_echoes:
                active_echo = active_echoes[0]
                shared_dmg = event.modified_damage // 2
                if shared_dmg > 0:
                    event.modified_damage = event.modified_damage - shared_dmg
                    idx = event.run.enemies.index(active_echo) + 1
                    event.engine.combat_resolver.damage_target(event.run, f"e{idx}", shared_dmg, source="effect", damage_type="true")
                    event.engine._log_event(event.run, f"🔮 【时空残影】作为肉盾，为亚弗戈蒙分担了 {shared_dmg} 点伤害！")
            
            pass


class PendulumResonanceBuff(BuffImpl):
    def on_turn_end(self, event, buff_state, entity):
        if event.is_player:
            run = event.run
            p = run.player
            if p.actions == 0 or p.bonus_actions == 0:
                played_count = run.node_data.get("cards_played_this_turn", 0)
                dmg = max(4, played_count * 2)
                event.engine._damage_target(run, "p0", dmg, source="buff:钟摆共振", damage_type="true")
                event.engine._log_event(run, f"🔔 [钟摆共振] 银钟剧烈震荡！由于你本回合用光了动作点（当前 {p.actions}A {p.bonus_actions}BA），时空失衡，受到 {dmg} 点真实伤害！")
            else:
                event.engine._log_event(run, "⏳ [钟摆共振] 时间轴流动保持平稳。你保留了至少 1A 1BA，规避了震荡伤害，且在下回合将额外抽取 2 张牌！")
                run.node_data["draw_penalty_next_turn"] = run.node_data.get("draw_penalty_next_turn", 0) - 2


class SplitToTenBuff(BuffImpl):
    pass


class PhaseTransitionImmuneBuff(BuffImpl):
    def on_damage_calculate_defend(self, event, buff_state, entity):
        event.modified_damage = 0

    def on_turn_end(self, event, buff_state, entity):
        if not event.is_player and entity in event.run.enemies:
            buff_state.stacks -= 1
            if buff_state.stacks <= 0:
                if buff_state in entity.buffs:
                    entity.buffs.remove(buff_state)


for name, obj in list(globals().items()):
    if isinstance(obj, type) and issubclass(obj, BuffImpl) and obj is not BuffImpl:
        if not getattr(obj, "auto_register", True):
            continue
        snake = re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()
        if snake.endswith('_buff'):
            buff_id = snake[:-5]
        else:
            buff_id = snake
        register_buff(buff_id)(obj)
