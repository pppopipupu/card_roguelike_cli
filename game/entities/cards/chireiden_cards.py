from ...data.buff_data import BUFF_CONFIG
from ...data.locale_data import get_locale_text
from ...models.state import Card
from .registry import register_card


def _add_buff(engine, entity, buff_id: str, stacks: int):
    if stacks <= 0 or entity is None:
        return
    binfo = BUFF_CONFIG.get(buff_id, {})
    engine._add_buff_to(entity, buff_id, binfo.get("name", buff_id), binfo.get("desc", ""), stacks)


def _first_alive_enemy_tag(run, target) -> str:
    if isinstance(target, str) and target.startswith("e"):
        try:
            idx = int(target[1:]) - 1
            if 0 <= idx < len(run.enemies) and run.enemies[idx].hp > 0:
                return target
        except ValueError:
            pass
    for idx, enemy in enumerate(run.enemies):
        if enemy.hp > 0:
            return f"e{idx + 1}"
    return "e1"


@register_card("d_he3_fusion_ignition")
class DHe3FusionIgnitionCard(Card):
    def execute(self, run, target, engine) -> str:
        p = run.player
        base_dmg = int(getattr(self, "base_dmg", 28 if self.upgraded else 20))
        shield_amt = int(getattr(self, "shield_amount", 12 if self.upgraded else 8))
        stacks = int(getattr(self, "buff_stacks", 3 if self.upgraded else 2))
        draw_count = int(getattr(self, "draw_count", 1))
        has_overcharge = any(b.id == "fusion_overcharge" and b.stacks > 0 for b in p.buffs)
        dmg = engine.get_modified_spell_damage(run, self, base_dmg)
        if has_overcharge:
            for idx, enemy in enumerate(list(run.enemies)):
                if enemy.hp > 0:
                    engine._damage_target(run, f"e{idx + 1}", dmg, source="p0", damage_type="fire", card=self, damage_ready=True)
            engine._gain_shield(run, "p0", shield_amt)
            _add_buff(engine, p, "fusion_overcharge", stacks)
            engine._draw_cards(p, draw_count, run)
            return get_locale_text(
                "i18n_chireiden.card_results.d_he3_aoe",
                dmg=dmg,
                shield=shield_amt,
                stacks=stacks,
                draw=draw_count,
            )
        tag = _first_alive_enemy_tag(run, target)
        tname = engine._get_target_name(run, tag)
        engine._damage_target(run, tag, dmg, source="p0", damage_type="fire", card=self, damage_ready=True)
        engine._gain_shield(run, "p0", shield_amt)
        _add_buff(engine, p, "fusion_overcharge", stacks)
        return get_locale_text(
            "i18n_chireiden.card_results.d_he3_single",
            target=tname,
            dmg=dmg,
            shield=shield_amt,
            stacks=stacks,
        )


@register_card("pb_bi_coolant_loop")
class PbBiCoolantLoopCard(Card):
    def execute(self, run, target, engine) -> str:
        p = run.player
        shield_amt = int(getattr(self, "shield_amount", 22 if self.upgraded else 16))
        heal_amt = int(getattr(self, "heal_amount", 15 if self.upgraded else 10))
        stacks = int(getattr(self, "buff_stacks", 3 if self.upgraded else 2))
        engine._gain_shield(run, "p0", shield_amt)
        _add_buff(engine, p, "magnetic_confinement", stacks)
        for bad_id in ("bleed", "burn"):
            for b in list(p.buffs):
                if b.id == bad_id and b.stacks > 0:
                    b.stacks -= 1
                    if b.stacks <= 0:
                        p.buffs.remove(b)
                    break
        engine._heal_target(run, "p0", heal_amt)
        return get_locale_text(
            "i18n_chireiden.card_results.pb_bi_loop",
            shield=shield_amt,
            stacks=stacks,
            heal=heal_amt,
        )


@register_card("lunar_he3_orbital_drop")
class LunarHe3OrbitalDropCard(Card):
    def execute(self, run, target, engine) -> str:
        p = run.player
        base_dmg = int(getattr(self, "base_dmg", 25 if self.upgraded else 18))
        gain_a = int(getattr(self, "action_gain", getattr(self, "gain_a", 1)))
        draw_count = int(getattr(self, "draw_count", 3 if self.upgraded else 2))
        dmg = engine.get_modified_spell_damage(run, self, base_dmg)
        for idx, enemy in enumerate(list(run.enemies)):
            if enemy.hp > 0:
                engine._damage_target(run, f"e{idx + 1}", dmg, source="p0", damage_type="force", card=self, damage_ready=True)
        p.actions += gain_a
        engine._draw_cards(p, draw_count, run)
        return get_locale_text(
            "i18n_chireiden.card_results.lunar_drop",
            dmg=dmg,
            gain_a=gain_a,
            draw=draw_count,
        )


@register_card("int19_tokamak_calculus")
class Int19TokamakCalculusCard(Card):
    def execute(self, run, target, engine) -> str:
        p = run.player
        draw_count = int(getattr(self, "draw_count", 3 if self.upgraded else 2))
        gain_a = int(getattr(self, "action_gain", getattr(self, "gain_a", 2 if self.upgraded else 1)))
        stacks = int(getattr(self, "buff_stacks", 4 if self.upgraded else 3))
        heal_amt = int(getattr(self, "heal_amount", 10 if self.upgraded else 6))
        engine._draw_cards(p, draw_count, run)
        p.actions += gain_a
        _add_buff(engine, p, "fusion_overcharge", stacks)
        engine._heal_target(run, "p0", heal_amt)
        return get_locale_text(
            "i18n_chireiden.card_results.int19_calculus",
            draw=draw_count,
            gain_a=gain_a,
            stacks=stacks,
            heal=heal_amt,
        )


@register_card("penning_trap_lockdown")
class PenningTrapLockdownCard(Card):
    def execute(self, run, target, engine) -> str:
        p = run.player
        base_dmg = int(getattr(self, "base_dmg", 30 if self.upgraded else 22))
        shield_amt = int(getattr(self, "shield_amount", 20 if self.upgraded else 14))
        stacks = int(getattr(self, "buff_stacks", 3 if self.upgraded else 2))
        weak_stacks = int(getattr(self, "weak_stacks", 3 if self.upgraded else 2))
        dmg = engine.get_modified_spell_damage(run, self, base_dmg)
        for idx, enemy in enumerate(list(run.enemies)):
            if enemy.hp > 0:
                engine._damage_target(run, f"e{idx + 1}", dmg, source="p0", damage_type="lightning", card=self, damage_ready=True)
                if enemy.hp > 0:
                    _add_buff(engine, enemy, "weak", weak_stacks)
        engine._gain_shield(run, "p0", shield_amt)
        _add_buff(engine, p, "magnetic_confinement", stacks)
        return get_locale_text(
            "i18n_chireiden.card_results.penning_lockdown",
            dmg=dmg,
            shield=shield_amt,
            stacks=stacks,
        )


@register_card("hisoutensoku_thermonuclear_cannon")
class HisoutensokuThermonuclearCannonCard(Card):
    def execute(self, run, target, engine) -> str:
        p = run.player
        base_dmg = int(getattr(self, "base_dmg", 46 if self.upgraded else 34))
        splash_base = int(getattr(self, "splash_dmg", 20 if self.upgraded else 14))
        scale = int(getattr(self, "overcharge_scale", 6 if self.upgraded else 4))
        overcharge = sum(b.stacks for b in p.buffs if b.id == "fusion_overcharge")
        raw_main = base_dmg + overcharge * scale
        main_dmg = engine.get_modified_spell_damage(run, self, raw_main)
        splash_dmg = engine.get_modified_spell_damage(run, self, splash_base)
        tag = _first_alive_enemy_tag(run, target)
        tname = engine._get_target_name(run, tag)
        main_idx = int(tag[1:]) - 1
        engine._damage_target(run, tag, main_dmg, source="p0", damage_type="fire", card=self, damage_ready=True)
        for idx, enemy in enumerate(list(run.enemies)):
            if idx != main_idx and enemy.hp > 0:
                engine._damage_target(run, f"e{idx + 1}", splash_dmg, source="p0", damage_type="fire", card=self, damage_ready=True)
        return get_locale_text(
            "i18n_chireiden.card_results.thermonuclear_cannon",
            target=tname,
            dmg=main_dmg,
            splash=splash_dmg,
        )
