from ...models.state import Card
from ...data.card_data import CARD_CONFIG
from ...data.buff_data import BUFF_CONFIG
from ...data.locale_data import get_locale_text
from ...core.sp_system import consume_sp, restore_sp
from .registry import register_card


@register_card("haste_sp")
class HasteSpCard(Card):
    def execute(self, run, target, engine) -> str:
        p = run.player
        sp_cost = getattr(self, "sp_cost", 2 if self.upgraded else 3)
        draw_count = getattr(self, "draw_count", 2 if self.upgraded else 1)
        sp_res = consume_sp(p, sp_cost, allow_overdraft=True)
        p.actions = max(0, p.actions) * 2
        p.bonus_actions = max(0, p.bonus_actions) * 2
        engine._draw_cards(p, draw_count, run)
        if sp_res["exhaustion_added"] > 0:
            engine._log_event(run, get_locale_text("i18n_grid_map.haste_sp_overdraft_log", exhaustion=p.exhaustion))
            if p.exhaustion >= 5:
                p.hp = 0
                run.node_data["death_cause"] = get_locale_text("i18n_grid_map.exhaustion_death_cause")
                from ...core.battle.party_battle import mark_downed
                mark_downed(engine, run, p)
        cfg = CARD_CONFIG.get(self.id.replace("+", ""), {})
        tmpl = cfg.get("feedback", "")
        if tmpl:
            return tmpl.format(sp_cost=sp_cost, actions=p.actions, bonus_actions=p.bonus_actions, draw_count=draw_count)
        return get_locale_text("i18n_grid_map.haste_sp_result", sp_cost=sp_cost, actions=p.actions, bonus_actions=p.bonus_actions, draw_count=draw_count)


@register_card("calm_mind")
class CalmMindCard(Card):
    def execute(self, run, target, engine) -> str:
        p = run.player
        sp_gain = getattr(self, "sp_gain", 6 if self.upgraded else 4)
        buff_stacks = getattr(self, "buff_stacks", 4 if self.upgraded else 3)
        gained = restore_sp(p, sp_gain)
        binfo = BUFF_CONFIG.get("psychic_resistance", {})
        engine._add_buff_to(
            p,
            "psychic_resistance",
            binfo.get("name", get_locale_text("i18n_grid_map.buff_psychic_resistance_name")),
            binfo.get("desc", get_locale_text("i18n_grid_map.buff_psychic_resistance_desc")),
            buff_stacks,
        )
        cfg = CARD_CONFIG.get(self.id.replace("+", ""), {})
        tmpl = cfg.get("feedback", "")
        if tmpl:
            return tmpl.format(sp_gain=gained if gained > 0 else sp_gain, buff_stacks=buff_stacks)
        return get_locale_text("i18n_grid_map.calm_mind_result", sp_gain=sp_gain, buff_stacks=buff_stacks)


@register_card("desperate_strike")
class DesperateStrikeCard(Card):
    def execute(self, run, target, engine) -> str:
        p = run.player
        base = getattr(self, "base_dmg", 8 if self.upgraded else 6)
        sp_loss_bonus = getattr(self, "sp_loss_bonus", 3 if self.upgraded else 2)
        exhaustion_pct = getattr(self, "exhaustion_pct", 35 if self.upgraded else 25)
        max_sp = max(0, int(getattr(p, "max_sp", 10)))
        cur_sp = max(0, int(getattr(p, "sp", max_sp)))
        lost_sp = max(0, max_sp - cur_sp)
        raw_dmg = base + lost_sp * sp_loss_bonus
        dmg = engine.get_modified_spell_damage(run, self, raw_dmg)
        ex = max(0, int(getattr(p, "exhaustion", 0) or 0))
        if ex > 0:
            dmg = int(dmg * (100 + ex * exhaustion_pct) // 100)
        name = engine._get_target_name(run, target)
        engine._damage_target(run, target, dmg, damage_type="slashing", card=self, damage_ready=True)
        return get_locale_text("i18n_grid_map.desperate_strike_result", target=name, dmg=dmg)


@register_card("intangible")
class IntangibleCard(Card):
    def execute(self, run, target, engine) -> str:
        p = run.player
        buff_stacks = getattr(self, "buff_stacks", 1)
        binfo = BUFF_CONFIG.get("intangible", {})
        engine._add_buff_to(
            p,
            "intangible",
            binfo.get("name", get_locale_text("i18n_grid_map.buff_intangible_name")),
            binfo.get("desc", get_locale_text("i18n_grid_map.buff_intangible_desc")),
            buff_stacks,
        )
        return get_locale_text("i18n_grid_map.intangible_result", stacks=buff_stacks)


@register_card("bladesong")
class BladesongCard(Card):
    def execute(self, run, target, engine) -> str:
        p = run.player
        shield_val = getattr(self, "shield_amount", 12 if self.upgraded else 8)
        buff_stacks = getattr(self, "buff_stacks", 2 if self.upgraded else 1)
        engine._gain_shield(run, "p0", shield_val)
        binfo = BUFF_CONFIG.get("bladesong", {})
        engine._add_buff_to(
            p,
            "bladesong",
            binfo.get("name", get_locale_text("i18n_grid_map.buff_bladesong_name")),
            binfo.get("desc", get_locale_text("i18n_grid_map.buff_bladesong_desc")),
            buff_stacks,
        )
        return get_locale_text("i18n_grid_map.bladesong_result", shield=shield_val, stacks=buff_stacks)
