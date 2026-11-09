from ...data.minion_data import MINION_CONFIG
from ...data.locale_data import get_locale_text
from .minion_base import BaseMinionSkill, MinionTemplate


def _minion_config(minion_id):
    return MINION_CONFIG.get(minion_id, {})


def _skill_config(minion, index):
    skills = _minion_config(getattr(minion, "id", "")).get("skills") or []
    return skills[index] if 0 <= index < len(skills) else {}


def _stat(cfg, key, fallback, source=None):
    return cfg[key] if key in cfg else getattr(source, key, fallback)


def _summon_stats(owner_id, token_id, upgraded):
    owner_cfg = _minion_config(owner_id)
    token_cfg = _minion_config(token_id)
    hp = token_cfg.get("hp", owner_cfg.get("token_hp", 4 if upgraded else 3))
    atk = token_cfg.get("atk", owner_cfg.get("token_atk", 2 if upgraded else 1))
    return hp, atk


class BannerBearerBuff(BaseMinionSkill):
    def execute(self, run, my_grid, target, engine) -> str:
        m = run.player.minions[my_grid]
        cfg = _skill_config(m, 0)
        is_upgraded = m.id.endswith("+")
        eligible = [mk for mk, mv in run.player.minions.items() if mk != my_grid]
        if not eligible:
            return get_locale_text("i18n_minions.officer.banner_bearer_no_target")
        import random
        chosen_grid = random.choice(eligible)
        chosen_minion = run.player.minions[chosen_grid]
        val = _stat(cfg, "atk_buff", 3 if is_upgraded else 2, self)
        chosen_minion.atk += val
        shield_msg = ""
        if is_upgraded:
            heal = _stat(cfg, "heal", 3, self)
            engine._heal_target(run, f"p{my_grid}", heal)
            shield_msg = get_locale_text("i18n_minions.officer.banner_bearer_heal_suffix", heal=heal)
        return get_locale_text("i18n_minions.officer.banner_bearer_result", name=chosen_minion.name, val=val, suffix=shield_msg)


class PatrolCaptainOrder(BaseMinionSkill):
    def execute(self, run, my_grid, target, engine) -> str:
        m = run.player.minions[my_grid]
        cfg = _skill_config(m, 0)
        is_upgraded = m.id.endswith("+")
        heal_val = _stat(cfg, "heal", 5 if is_upgraded else 3, self)
        shield_val = _stat(cfg, "shield", 5 if is_upgraded else 3, self)
        for mk in list(run.player.minions.keys()):
            engine._heal_target(run, f"p{mk}", heal_val)
        engine._gain_shield(run, "p0", shield_val)
        return get_locale_text("i18n_minions.officer.patrol_captain_order_result", heal=heal_val, shield=shield_val)


class GarrisonLeaderWall(BaseMinionSkill):
    def execute(self, run, my_grid, target, engine) -> str:
        m = run.player.minions[my_grid]
        cfg = _skill_config(m, 0)
        is_upgraded = m.id.endswith("+")
        shield_val = _stat(cfg, "shield", 9 if is_upgraded else 6, self)
        heal_val = _stat(cfg, "heal", 5 if is_upgraded else 3, self)
        engine._gain_shield(run, "p0", shield_val)
        for mk, mv in list(run.player.minions.items()):
            if mv.id.startswith("officer_") or mv.id.startswith("commander_"):
                engine._heal_target(run, f"p{mk}", heal_val)
        return get_locale_text("i18n_minions.officer.garrison_leader_wall_result", shield=shield_val, heal=heal_val)


class ValiantHeraldSignal(BaseMinionSkill):
    def execute(self, run, my_grid, target, engine) -> str:
        m = run.player.minions[my_grid]
        cfg = _skill_config(m, 0)
        is_upgraded = m.id.endswith("+")
        val = _stat(cfg, "atk_buff", 3 if is_upgraded else 2, self)
        for mk, mv in run.player.minions.items():
            mv.atk += val
        return get_locale_text("i18n_minions.officer.valiant_herald_signal_result", val=val)


class SteelcladTacticianStrike(BaseMinionSkill):
    def execute(self, run, my_grid, target, engine) -> str:
        m = run.player.minions[my_grid]
        cfg = _skill_config(m, 0)
        is_upgraded = m.id.endswith("+")
        dmg = _stat(cfg, "damage", 9 if is_upgraded else 6, self)
        t = target or "e1"
        tname = engine._get_target_name(run, t)
        enemy_to_attack = None
        if t.startswith("e"):
            try:
                idx = int(t[1:]) - 1
                if 0 <= idx < len(run.enemies):
                    enemy_to_attack = run.enemies[idx]
            except ValueError:
                pass
        engine._damage_target(run, t, dmg, damage_type="bludgeoning", source=f"p{my_grid}")
        is_kill = False
        if enemy_to_attack and enemy_to_attack.hp <= 0:
            is_kill = True
        tok_msg = ""
        if is_kill:
            tok_id = "officer_soldier_token+" if is_upgraded else "officer_soldier_token"
            tok_name = get_locale_text("i18n_minions.common.soldier_token_name_upgraded") if is_upgraded else get_locale_text("i18n_minions.common.soldier_token_name")
            summon_total = _stat(cfg, "summon_count", 2, self)
            tok_hp, tok_atk = _summon_stats(m.id, tok_id, is_upgraded)
            summon_count = 0
            for _ in range(summon_total):
                tok_grid = engine._summon_minion(run, tok_id, tok_name, tok_hp, tok_atk, 0)
                if tok_grid:
                    summon_count += 1
                    tm = run.player.minions[tok_grid]
                    engine._add_buff_to(tm, "ward", get_locale_text("i18n_minions.common.ward_name"), get_locale_text("i18n_minions.common.ward_desc"))
            if summon_count > 0:
                tok_msg = get_locale_text("i18n_minions.officer.steelclad_tactician_kill_suffix", count=summon_count, token_name=tok_name)
        return get_locale_text("i18n_minions.officer.steelclad_tactician_result", target=tname, damage=dmg, suffix=tok_msg)


class BladeDancerSlash(BaseMinionSkill):
    def execute(self, run, my_grid, target, engine) -> str:
        m = run.player.minions[my_grid]
        cfg = _skill_config(m, 0)
        is_upgraded = m.id.endswith("+")
        dmg = _stat(cfg, "damage", 6 if is_upgraded else 4, self)
        hits = _stat(cfg, "hits", 2, self)
        t = target or "e1"
        tname = engine._get_target_name(run, t)
        for _ in range(hits):
            engine._damage_target(run, t, dmg, damage_type="slashing", source=f"p{my_grid}")
        return get_locale_text("i18n_minions.officer.blade_dancer_slash_result", target=tname, damage=dmg, hits=hits)


class AuroraEmperorJudgment(BaseMinionSkill):
    def execute(self, run, my_grid, target, engine) -> str:
        m = run.player.minions[my_grid]
        cfg = _skill_config(m, 0)
        is_upgraded = m.id.endswith("+")
        rally = run.node_data.get("rally_count", 0)
        rally_threshold = _stat(cfg, "rally_threshold", 15, self)
        if rally >= rally_threshold:
            dmg = _stat(cfg, "damage_high", 22 if is_upgraded else 15, self)
            dtype = "true"
        else:
            dmg = _stat(cfg, "damage", 12 if is_upgraded else 8, self)
            dtype = "radiant"
        for idx in range(len(run.enemies) - 1, -1, -1):
            engine._damage_target(run, f"e{idx+1}", dmg, damage_type=dtype, source=f"p{my_grid}")
        type_name = get_locale_text("i18n_minions.common.damage_type_true") if dtype == "true" else get_locale_text("i18n_minions.common.damage_type_radiant")
        return get_locale_text("i18n_minions.officer.aurora_emperor_judgment_result", damage=dmg, type_name=type_name)


class SoldierTokenTemplate(MinionTemplate):
    def on_minion_summon(self, run, grid, event, engine):
        if event.minion_state.id == self.id:
            engine._add_buff_to(event.minion_state, "ward", get_locale_text("i18n_minions.common.ward_name"), get_locale_text("i18n_minions.common.ward_desc"))


class CommanderPatrolCaptainTemplate(MinionTemplate):
    def on_minion_summon(self, run, grid, event, engine):
        if event.minion_state.id == self.id:
            is_upgraded = event.minion_state.id.endswith("+")
            tok_id = "officer_soldier_token+" if is_upgraded else "officer_soldier_token"
            tok_name = get_locale_text("i18n_minions.common.soldier_token_name_upgraded") if is_upgraded else get_locale_text("i18n_minions.common.soldier_token_name")
            tok_hp, tok_atk = _summon_stats(event.minion_state.id, tok_id, is_upgraded)
            tok_grid = engine._summon_minion(run, tok_id, tok_name, tok_hp, tok_atk, 0)
            if tok_grid:
                tm = run.player.minions[tok_grid]
                engine._add_buff_to(tm, "ward", get_locale_text("i18n_minions.common.ward_name"), get_locale_text("i18n_minions.common.ward_desc"))
                engine._log_event(run, get_locale_text("i18n_minions.officer.soldier_token_summon_log", name=event.minion_state.name, grid=tok_grid, token_name=tok_name))


class RecruitVanguardTemplate(MinionTemplate):
    def on_attack(self, run, grid, event, engine):
        m = run.player.minions.get(grid)
        if m:
            cfg = _minion_config(m.id)
            rally = run.node_data.get("rally_count", 0)
            if rally >= _stat(cfg, "rally_threshold", 6, self):
                is_upgraded = m.id.endswith("+")
                val = _stat(cfg, "atk_buff", 4 if is_upgraded else 2, self)
                event.modified_damage += val
                shield_msg = ""
                if is_upgraded:
                    shield_val = _stat(cfg, "shield", 2, self)
                    engine._gain_shield(run, "p0", shield_val)
                    shield_msg = get_locale_text("i18n_minions.officer.recruit_vanguard_shield_suffix", shield=shield_val)
                engine._log_event(run, get_locale_text("i18n_minions.officer.recruit_vanguard_attack_log", name=m.name, rally=rally, val=val, suffix=shield_msg))


class BannerBearerTemplate(MinionTemplate):
    def on_card_played(self, run, grid, event, engine):
        m = run.player.minions.get(grid)
        if m and event.card.id.replace("+", "") in ("warrior_strike", "warrior_bash", "iron_wave", "warrior_anger", "body_slam", "pommel_strike", "heavy_blade", "uppercut", "feed", "bludgeon"):
            cfg = _minion_config(m.id)
            is_upgraded = m.id.endswith("+")
            turn_uses = run.node_data.get(f"banner_bearer_use_{grid}", 0)
            if turn_uses < _stat(cfg, "max_count", 1, self):
                eligible = [mk for mk, mv in run.player.minions.items() if mk != grid]
                if eligible:
                    import random
                    chosen_grid = random.choice(eligible)
                    chosen_minion = run.player.minions[chosen_grid]
                    chosen_minion.attack_actions = _stat(cfg, "attack_actions", 1, self)
                    val = _stat(cfg, "atk_buff", 3 if is_upgraded else 2, self)
                    chosen_minion.atk += val
                    run.node_data[f"banner_bearer_use_{grid}"] = turn_uses + 1
                    shield_msg = ""
                    if is_upgraded:
                        shield_val = _stat(cfg, "shield", 3, self)
                        engine._gain_shield(run, f"p{grid}", shield_val)
                        shield_msg = get_locale_text("i18n_minions.officer.banner_bearer_shield_suffix", name=m.name, shield=shield_val)
                    engine._log_event(run, get_locale_text("i18n_minions.officer.banner_bearer_passive_log", name=m.name, target=chosen_minion.name, val=val, suffix=shield_msg))


class RoyalGuardTemplate(MinionTemplate):
    def on_shield_gain(self, run, grid, event, engine):
        m = run.player.minions.get(grid)
        if m and event.target == "p0" and event.modified_amount > 0:
            cfg = _minion_config(m.id)
            is_upgraded = m.id.endswith("+")
            val = _stat(cfg, "atk_buff", 2 if is_upgraded else 1, self)
            m.atk += val
            dmg = _stat(cfg, "damage", 3 if is_upgraded else 2, self)
            dtype = "true" if is_upgraded else "piercing"
            first_enemy = engine._get_first_alive_enemy(run)
            if first_enemy:
                engine._damage_target(run, first_enemy, dmg, damage_type=dtype, source=f"p{grid}")
                tname = engine._get_target_name(run, first_enemy)
                engine._log_event(run, get_locale_text("i18n_minions.officer.royal_guard_passive_log", name=m.name, val=val, target=tname))


class GarrisonLeaderTemplate(MinionTemplate):
    def on_minion_summon(self, run, grid, event, engine):
        if event.minion_state.id == self.id:
            engine._add_buff_to(event.minion_state, "ward", get_locale_text("i18n_minions.common.ward_name"), get_locale_text("i18n_minions.common.ward_desc_self"))

    def on_damage_take(self, run, grid, event, engine):
        m = run.player.minions.get(grid)
        if m and event.target == "p0" and event.amount > 0:
            p = run.player
            if p.shield == 0 and "last_shield_before_dmg" in run.node_data and run.node_data["last_shield_before_dmg"] > 0:
                cfg = _minion_config(m.id)
                is_upgraded = m.id.endswith("+")
                tok_id = "officer_soldier_token+" if is_upgraded else "officer_soldier_token"
                tok_name = get_locale_text("i18n_minions.common.soldier_token_name_upgraded") if is_upgraded else get_locale_text("i18n_minions.common.soldier_token_name")
                tok_hp, tok_atk = _summon_stats(m.id, tok_id, is_upgraded)
                tok_grid = engine._summon_minion(run, tok_id, tok_name, tok_hp, tok_atk, 0)
                shield_val = _stat(cfg, "shield", 5 if is_upgraded else 3, self)
                engine._gain_shield(run, "p0", shield_val)
                ref_msg = ""
                if is_upgraded:
                    engine._damage_target(run, event.source, event.amount, damage_type="true", source=f"p{grid}")
                    ref_msg = get_locale_text("i18n_minions.officer.garrison_leader_reflect_suffix", target=engine._get_target_name(run, event.source), damage=event.amount)
                tok_msg = get_locale_text("i18n_minions.officer.garrison_leader_token_suffix", grid=tok_grid, token_name=tok_name, suffix=ref_msg) if tok_grid else ""
                engine._log_event(run, get_locale_text("i18n_minions.officer.garrison_leader_passive_log", name=m.name, shield=shield_val, suffix=tok_msg))


class SquadSkirmisherTemplate(MinionTemplate):
    def on_minion_death(self, run, grid, event, engine):
        m = run.player.minions.get(grid)
        if m and event.is_enemy and event.source == f"p{grid}":
            cfg = _minion_config(m.id)
            is_upgraded = m.id.endswith("+")
            tok_id = "officer_soldier_token+" if is_upgraded else "officer_soldier_token"
            tok_name = get_locale_text("i18n_minions.common.soldier_token_name_upgraded") if is_upgraded else get_locale_text("i18n_minions.common.soldier_token_name")
            tok_hp, tok_atk = _summon_stats(m.id, tok_id, is_upgraded)
            tok_grid = engine._summon_minion(run, tok_id, tok_name, tok_hp, tok_atk, 0)
            if tok_grid:
                tm = run.player.minions[tok_grid]
                engine._add_buff_to(tm, "ward", get_locale_text("i18n_minions.common.ward_name"), get_locale_text("i18n_minions.common.ward_desc"))
                if is_upgraded:
                    tm.attack_actions = _stat(cfg, "attack_actions", 2, self)
                    engine._log_event(run, get_locale_text("i18n_minions.officer.squad_skirmisher_kill_upgraded_log", name=m.name, target=event.name, grid=tok_grid, token_name=tok_name))
                else:
                    engine._log_event(run, get_locale_text("i18n_minions.officer.squad_skirmisher_kill_log", name=m.name, target=event.name, grid=tok_grid, token_name=tok_name))

    def on_card_exhaust(self, run, grid, event, engine):
        m = run.player.minions.get(grid)
        if m:
            cfg = _minion_config(m.id)
            is_upgraded = m.id.endswith("+")
            val = _stat(cfg, "atk_buff", 3 if is_upgraded else 2, self)
            layers = _stat(cfg, "vulnerable_layers", 1, self)
            m.atk += val
            if is_upgraded:
                for enemy in list(run.enemies):
                    engine._add_buff_to(enemy, "minor_vulnerable", get_locale_text("i18n_minions.common.vulnerable_name"), get_locale_text("i18n_minions.common.vulnerable_desc"), layers)
                engine._log_event(run, get_locale_text("i18n_minions.officer.squad_skirmisher_exhaust_all_log", name=m.name, val=val, layers=layers))
            else:
                first_enemy = engine._get_first_alive_enemy(run)
                if first_enemy:
                    try:
                        f_idx = int(first_enemy.replace("e", "")) - 1
                        if 0 <= f_idx < len(run.enemies):
                            engine._add_buff_to(run.enemies[f_idx], "minor_vulnerable", get_locale_text("i18n_minions.common.vulnerable_name"), get_locale_text("i18n_minions.common.vulnerable_desc"), layers)
                    except ValueError:
                        pass
                    tname = engine._get_target_name(run, first_enemy)
                    engine._log_event(run, get_locale_text("i18n_minions.officer.squad_skirmisher_exhaust_one_log", name=m.name, val=val, target=tname, layers=layers))


class ValiantHeraldTemplate(MinionTemplate):
    def on_minion_death(self, run, grid, event, engine):
        from ..cards.base import ALL_CARDS
        if event.grid == f"p{grid}" and not event.is_enemy:
            is_upgraded = event.minion_id.endswith("+")
            if is_upgraded:
                eligible = [cid for cid in run.player.hand if ALL_CARDS.get(cid) and ALL_CARDS.get(cid).type == "minion"]
                for cid in eligible:
                    run.node_data.setdefault("free_minion_cards", []).append(cid)
                engine._log_event(run, get_locale_text("i18n_minions.officer.valiant_herald_death_upgraded_log"))
            else:
                eligible = [cid for cid in run.player.hand if ALL_CARDS.get(cid) and ALL_CARDS.get(cid).type == "minion"]
                if eligible:
                    import random
                    chosen = random.choice(eligible)
                    run.node_data.setdefault("free_minion_cards", []).append(chosen)
                    cname = ALL_CARDS.get(chosen).name
                    engine._log_event(run, get_locale_text("i18n_minions.officer.valiant_herald_death_log", name=cname))


class SteelcladTacticianTemplate(MinionTemplate):
    def on_turn_end(self, run, grid, event, engine):
        m = run.player.minions.get(grid)
        if m:
            cfg = _minion_config(m.id)
            rally = run.node_data.get("rally_count", 0)
            if rally >= _stat(cfg, "rally_threshold", 10, self):
                is_upgraded = m.id.endswith("+")
                tok_id = "officer_soldier_token+" if is_upgraded else "officer_soldier_token"
                tok_name = get_locale_text("i18n_minions.common.soldier_token_name_upgraded") if is_upgraded else get_locale_text("i18n_minions.common.soldier_token_name")
                tok_hp, tok_atk = _summon_stats(m.id, tok_id, is_upgraded)
                tok_grid = engine._summon_minion(run, tok_id, tok_name, tok_hp, tok_atk, 0)
                coef = _stat(cfg, "coef", 2 if is_upgraded else 1, self)
                shield_val = len(run.player.minions) * coef
                engine._gain_shield(run, "p0", shield_val)
                tok_msg = get_locale_text("i18n_minions.officer.steelclad_tactician_token_suffix", grid=tok_grid, token_name=tok_name) if tok_grid else get_locale_text("i18n_minions.officer.steelclad_tactician_no_grid", token_name=tok_name)
                engine._log_event(run, get_locale_text("i18n_minions.officer.steelclad_tactician_turn_end_log", name=m.name, rally=rally, shield=shield_val, suffix=tok_msg))


class BladeDancerTemplate(MinionTemplate):
    def on_damage_calculate(self, run, grid, event, engine):
        if event.source == f"p{grid}":
            target_enemy = None
            if event.target.startswith("e"):
                try:
                    idx = int(event.target[1:]) - 1
                    if 0 <= idx < len(run.enemies):
                        target_enemy = run.enemies[idx]
                except ValueError:
                    pass
            if target_enemy and target_enemy.shield > 0:
                m = run.player.minions.get(grid)
                is_upgraded = m.id.endswith("+") if m else False
                cfg = _minion_config(m.id if m else "officer_blade_dancer")
                coef = _stat(cfg, "coef", 2.0 if is_upgraded else 1.5, self)
                event.modified_damage = int(event.modified_damage * coef)
                event.damage_type = "true"
                engine._log_event(run, get_locale_text("i18n_minions.officer.blade_dancer_passive_log", name=m.name if m else get_locale_text("i18n_minions.common.blade_dancer_fallback_name"), percent=int(coef*100)))
