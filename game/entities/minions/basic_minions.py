from ...data.minion_data import MINION_CONFIG
from ...data.locale_data import get_locale_text
from .minion_base import BaseMinionSkill, MinionTemplate


class MercenaryHeavyStrike(BaseMinionSkill):
    def execute(self, run, my_grid, target, engine) -> str:
        m = run.player.minions[my_grid]
        cfg = MINION_CONFIG[m.id]["skills"][0]
        damage = cfg["damage"]
        tname = engine._get_target_name(run, target)
        engine._damage_target(run, target, damage)
        return cfg["feedback"].format(target=tname, damage=damage)


class MercenaryBattlecry(BaseMinionSkill):
    def execute(self, run, my_grid, target, engine) -> str:
        m = run.player.minions[my_grid]
        cfg = MINION_CONFIG[m.id]["skills"][1]
        atk_buff = cfg["atk_buff"]
        m.atk += atk_buff
        return cfg["feedback"].format(atk_buff=atk_buff)


class ShieldGuardDefend(BaseMinionSkill):
    def execute(self, run, my_grid, target, engine) -> str:
        m = run.player.minions[my_grid]
        cfg = MINION_CONFIG[m.id]["skills"][0]
        shield = cfg["shield"]
        engine._gain_shield(run, "p0", shield)
        return cfg["feedback"].format(shield=shield)


class ShieldGuardBash(BaseMinionSkill):
    def execute(self, run, my_grid, target, engine) -> str:
        m = run.player.minions[my_grid]
        cfg = MINION_CONFIG[m.id]["skills"][1]
        damage = cfg["damage"]
        shield = cfg["shield"]
        tname = engine._get_target_name(run, target)
        engine._damage_target(run, target, damage)
        engine._gain_shield(run, "p0", shield)
        return cfg["feedback"].format(target=tname, damage=damage, shield=shield)


class FamiliarAssist(BaseMinionSkill):
    def execute(self, run, my_grid, target, engine) -> str:
        m = run.player.minions[my_grid]
        cfg = MINION_CONFIG[m.id]["skills"][0]
        draw = cfg["draw"]
        engine._draw_cards(run.player, draw, run)
        return cfg["feedback"].format(draw=draw)


class FamiliarCharge(BaseMinionSkill):
    def execute(self, run, my_grid, target, engine) -> str:
        m = run.player.minions[my_grid]
        cfg = MINION_CONFIG[m.id]["skills"][1]
        ba_gain = cfg["ba_gain"]
        run.player.bonus_actions += ba_gain
        return cfg["feedback"].format(ba_gain=ba_gain)


class WaterTouch(BaseMinionSkill):
    def execute(self, run, my_grid, target, engine) -> str:
        m = run.player.minions[my_grid]
        cfg = MINION_CONFIG[m.id]["skills"][0]
        t = target or "e1"
        if run.node_type == "duel":
            if t == "e1" or t == "e":
                enemy = run.player2
            elif t.startswith("e") and len(t) > 1:
                try:
                    grid_idx = str(int(t[1:]) - 1)
                    enemy = run.player2.minions.get(grid_idx)
                except ValueError:
                    enemy = None
            else:
                enemy = None
        else:
            enemy = None
            if t.startswith("e"):
                try:
                    grid_idx = int(t[1:]) - 1
                except ValueError:
                    grid_idx = 0
                if 0 <= grid_idx < len(run.enemies):
                    enemy = run.enemies[grid_idx]
        if enemy:
            ba_reduction = cfg.get("ba_reduction", getattr(self, "ba_reduction", 1))
            enemy.bonus_actions = max(0, enemy.bonus_actions - ba_reduction)
            tname = engine._get_target_name(run, t)
            return cfg["feedback"].format(target=tname, ba_reduction=ba_reduction)
        return get_locale_text("i18n_minions.common.no_enemy_target")


class WaterLance(BaseMinionSkill):
    def execute(self, run, my_grid, target, engine) -> str:
        m = run.player.minions[my_grid]
        cfg = MINION_CONFIG[m.id]["skills"][1]
        damage = cfg["damage"]
        t = target or "e1"
        tname = engine._get_target_name(run, t)
        engine._damage_target(run, t, damage)
        if run.node_type == "duel":
            if t == "e1" or t == "e":
                enemy = run.player2
            elif t.startswith("e") and len(t) > 1:
                try:
                    grid_idx = str(int(t[1:]) - 1)
                    enemy = run.player2.minions.get(grid_idx)
                except ValueError:
                    enemy = None
            else:
                enemy = None
        else:
            enemy = None
            if t.startswith("e"):
                try:
                    grid_idx = int(t[1:]) - 1
                except ValueError:
                    grid_idx = 0
                if 0 <= grid_idx < len(run.enemies):
                    enemy = run.enemies[grid_idx]
        if enemy:
            action_reduction = cfg.get("action_reduction", getattr(self, "action_reduction", 1))
            enemy.actions = max(0, enemy.actions - action_reduction)
            if cfg.get("stun"):
                engine._add_buff_to(enemy, "stun", get_locale_text("i18n_minions.common.stun_name"), get_locale_text("i18n_minions.common.stun_desc"), cfg["stun"])
            feedback_boss = cfg.get("feedback_boss")
            if feedback_boss and (t == "e1" or t == "e" or run.node_type == "duel"):
                return feedback_boss.format(target=tname, damage=damage, action_reduction=action_reduction)
            return cfg["feedback"].format(target=tname, damage=damage, action_reduction=action_reduction)
        return get_locale_text("i18n_minions.common.no_enemy_target")


class GolemOverload(BaseMinionSkill):
    def execute(self, run, my_grid, target, engine) -> str:
        m = run.player.minions[my_grid]
        cfg = MINION_CONFIG[m.id]["skills"][0]
        self_damage = cfg["self_damage"]
        atk_buff = cfg["atk_buff"]
        engine._damage_target(run, f"p{my_grid}", self_damage, source="self", damage_type="true")
        if my_grid not in run.player.minions or run.player.minions[my_grid] is not m:
            return cfg["feedback_dead"].format(self_damage=self_damage, atk_buff=atk_buff)
        m.atk += atk_buff
        return cfg["feedback"].format(self_damage=self_damage, atk_buff=atk_buff)


class GolemRepair(BaseMinionSkill):
    def execute(self, run, my_grid, target, engine) -> str:
        m = run.player.minions[my_grid]
        cfg = MINION_CONFIG[m.id]["skills"][1]
        heal = cfg["heal"]
        engine._heal_target(run, f"p{my_grid}", heal)
        m = run.player.minions[my_grid]
        return cfg["feedback"].format(heal=heal, hp=m.hp, max_hp=m.max_hp)


class IcerainbowwSpray(BaseMinionSkill):
    def execute(self, run, my_grid, target, engine) -> str:
        m = run.player.minions[my_grid]
        cfg = MINION_CONFIG[m.id]["skills"][0]
        damage = cfg["damage"]
        layers = cfg.get("vulnerable_layers", getattr(self, "vulnerable_layers", 1))
        for idx, enemy in enumerate(list(run.enemies)):
            engine._damage_target(run, f"e{idx+1}", damage, source=f"minion:{m.name}", damage_type="cold")
            engine._add_buff_to(enemy, "minor_vulnerable_cold", get_locale_text("i18n_minions.common.cold_vulnerable_name"), get_locale_text("i18n_minions.common.cold_vulnerable_desc"), layers)
        return cfg["feedback"] + get_locale_text("i18n_minions.basic.icerainboww_spray_suffix", damage=damage, layers=layers)


class IcerainbowwShield(BaseMinionSkill):
    def execute(self, run, my_grid, target, engine) -> str:
        m = run.player.minions[my_grid]
        cfg = MINION_CONFIG[m.id]["skills"][1]
        p_shield = cfg.get("player_shield", getattr(self, "player_shield", 12))
        m_heal = cfg.get("minion_heal", getattr(self, "minion_heal", 4))
        engine._gain_shield(run, "p0", p_shield)
        for mk in list(run.player.minions.keys()):
            engine._heal_target(run, f"p{mk}", m_heal)
        return cfg["feedback"] + get_locale_text("i18n_minions.basic.icerainboww_shield_suffix", p_shield=p_shield, m_heal=m_heal)


class GateGuardStrike(BaseMinionSkill):
    def execute(self, run, my_grid, target, engine) -> str:
        m = run.player.minions[my_grid]
        cfg = MINION_CONFIG[m.id]["skills"][0]
        damage = cfg["damage"]
        action_reduction = cfg.get("action_reduction", getattr(self, "action_reduction", 1))
        t = target or "e1"
        tname = engine._get_target_name(run, t)
        engine._damage_target(run, t, damage)
        if t.startswith("e"):
            try:
                grid_idx = int(t[1:]) - 1
            except ValueError:
                grid_idx = 0
            if 0 <= grid_idx < len(run.enemies):
                enemy = run.enemies[grid_idx]
                enemy.actions = max(0, enemy.actions - action_reduction)
        return cfg["feedback"].format(target=tname, damage=damage, action_reduction=action_reduction)


class CardsPlayedEntryDamageTemplate(MinionTemplate):
    def on_minion_summon(self, run, grid, event, engine):
        if grid != event.grid:
            return
        if event.minion_state.id != self.id:
            return
        cfg = MINION_CONFIG.get(self.id) or MINION_CONFIG.get(self.id.rstrip("+"), {})
        thresholds = cfg.get("enter_hit_thresholds") or []
        damage = int(cfg.get("enter_damage", 0))
        if not thresholds or damage <= 0:
            return
        count = run.node_data.get("cards_played_this_turn", 0)
        if run.node_data.get("current_playing_card_id"):
            count += int(cfg.get("enter_current_card_bonus", getattr(self, "enter_current_card_bonus", 1)))
        if count < min(thresholds):
            return
        hits = sum(1 for threshold in thresholds if count >= threshold)
        damage_type = cfg.get("enter_damage_type", "effect")
        damage_name = cfg.get("enter_damage_name", get_locale_text("i18n_minions.common.damage_type_default"))
        import random
        hit_count = 0
        for _ in range(hits):
            alive = [idx for idx, enemy in enumerate(run.enemies) if enemy.hp > 0]
            if not alive:
                break
            idx = random.choice(alive)
            engine._damage_target(run, f"e{idx+1}", damage, source=f"p{grid}", damage_type=damage_type)
            hit_count += 1
        if hit_count:
            engine._log_event(run, get_locale_text("i18n_minions.basic.cards_played_entry_log", name=self.name, count=count, hit_count=hit_count, damage_name=damage_name))


class ShieldGuardTemplate(MinionTemplate):
    def on_minion_summon(self, run, grid, event, engine):
        if event.minion_state.id == self.id:
            engine._add_buff_to(event.minion_state, "ward", get_locale_text("i18n_minions.common.ward_name"), get_locale_text("i18n_minions.common.ward_desc"))


class GateGuardTemplate(MinionTemplate):
    def on_minion_summon(self, run, grid, event, engine):
        if event.minion_state.id == self.id:
            engine._add_buff_to(event.minion_state, "ward", get_locale_text("i18n_minions.common.ward_name"), get_locale_text("i18n_minions.common.ward_desc_self"))


class MercenaryTemplate(MinionTemplate):
    def on_attack(self, run, grid, event, engine):
        m = run.player.minions.get(grid)
        if m:
            cfg = MINION_CONFIG.get(m.id, {})
            is_upgraded = m.id.endswith("+")
            val = cfg.get("atk_buff", getattr(self, "atk_buff", 2 if is_upgraded else 1))
            m.atk += val
            engine._log_event(run, get_locale_text("i18n_minions.basic.mercenary_attack_log", name=m.name, val=val))
