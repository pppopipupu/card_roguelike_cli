import random
from typing import List, Optional

from .base import EnemyTemplate, register_enemy
from ...data.buff_data import BUFF_CONFIG
from ...data.enemy_data import ENEMY_CONFIG
from ...data.enemy_data_chireiden import (
    ENEMY_CHIREIDEN_CONFIG,
    SUPER_PORTAL_MAX_XEN_ALIVE,
    SUPER_PORTAL_PHASES,
    SUPER_PORTAL_PHASE_BY_NAME,
    UTSUHO_INTENT_CYCLE,
)
from ...data.locale_data import get_locale_text
from ...models.state import BuffState, EnemyIntentState


def _enemy_idx_tag(run, enemy) -> str:
    if enemy in run.enemies:
        return f"e{run.enemies.index(enemy) + 1}"
    return "e1"


def _buff_pair(buff_id: str) -> tuple[str, str]:
    cfg = BUFF_CONFIG.get(buff_id, {})
    return cfg.get("name", buff_id), cfg.get("desc", "")


def _is_first_aoe_tick(run) -> bool:
    if not run.node_data.get("coop_damage_aoe"):
        return True
    from ...core.battle.party_battle import alive_uids
    alive = alive_uids(run)
    cur = run.node_data.get("coop_damage_target_uid")
    return not alive or cur == alive[0]


def _strength_bonus(enemy) -> int:
    return sum(b.stacks for b in getattr(enemy, "buffs", []) if b.id == "strength")


def _overcharge_bonus(enemy) -> int:
    return sum(b.stacks for b in getattr(enemy, "buffs", []) if b.id == "fusion_overcharge") * 2


def _intents_from_entries(entries: list, main_count: int, bonus_count: int) -> List[EnemyIntentState]:
    if not entries:
        return []
    result: List[EnemyIntentState] = []
    for _ in range(max(1, main_count)):
        entry = random.choice(entries)
        result.append(EnemyIntentState(
            type=entry["id"],
            val=int(entry.get("val", 0)),
            desc=entry.get("desc", ""),
            cost_a=1,
            cost_ba=0,
        ))
    for _ in range(max(0, bonus_count)):
        entry = random.choice(entries)
        result.append(EnemyIntentState(
            type=entry["id"],
            val=int(entry.get("val", 0)),
            desc=entry.get("desc", ""),
            cost_a=0,
            cost_ba=1,
        ))
    return result


def _spawn_xen_unit(run, engine, xen_name: str):
    cfg = ENEMY_CONFIG.get(xen_name, {})
    hp_val = int(str(cfg.get("hp", "30")).split()[0])
    act_str = str(cfg.get("actions", "1A 0BA"))
    act_a = 2 if "2A" in act_str else 1
    act_ba = 1 if "1BA" in act_str else 0
    unit = engine._build_enemy_state(xen_name, hp_val, act_a, act_ba)
    unit.is_summon = True
    bname, bdesc = _buff_pair("xen_swarm_link")
    unit.buffs.append(BuffState(id="xen_swarm_link", name=bname, stacks=1, desc=bdesc))
    run.enemies.append(unit)
    entries = list(cfg.get("intents", []))
    unit.intents = _intents_from_entries(entries, unit.actions, unit.bonus_actions)
    from ...core.world.encounter_lore import record_encounter_for_run

    record_encounter_for_run(getattr(engine, "save_manager", None), run, xen_name)
    return unit


def _spawn_xen_wave(run, portal_enemy, phase_cfg: dict, engine, logs: Optional[List[str]]):
    alive_summons = sum(1 for e in run.enemies if getattr(e, "is_summon", False) and e.hp > 0)
    capacity = max(0, SUPER_PORTAL_MAX_XEN_ALIVE - alive_summons)
    batch = min(int(phase_cfg.get("summon_batch", 1)), capacity)
    pool = list(phase_cfg.get("summon_pool", ["Xen猎头蟹"]))
    if batch <= 0:
        engine._gain_shield(run, _enemy_idx_tag(run, portal_enemy), 16)
        msg = get_locale_text("i18n_chireiden.actions.portal_summon_empty", portal=portal_enemy.name, shield=16)
        if logs is not None:
            logs.append(msg)
        else:
            engine._log_event(run, msg)
        return
    for idx in range(batch):
        xen_name = pool[idx % len(pool)] if idx == 0 else random.choice(pool)
        unit = _spawn_xen_unit(run, engine, xen_name)
        msg = get_locale_text("i18n_chireiden.utsuho_ally.portal_summon", portal=portal_enemy.name, summon_name=unit.name)
        if logs is not None:
            logs.append(msg)
        else:
            engine._log_event(run, msg)


def ensure_utsuho_ally_joined(run, engine, logs: Optional[List[str]] = None) -> bool:
    merc_uid = "merc_utsuho"
    if merc_uid in run.players and run.players[merc_uid].hp > 0:
        return False
    from ...core.inventory.deck_service import DeckService
    from ...core.party.mercenary import build_mercenary_player

    owner_uid = run.uid_for(run.player) or run.user_id
    merc = build_mercenary_player("utsuho_reiuji", owner_uid)
    merc.relics = ["headband_of_intellect_int19"]
    merc.actions = 2
    merc.bonus_actions = 1
    merc.shield = 16
    merc.draw_pile = [DeckService.clone_state(c) for c in merc.deck]
    random.shuffle(merc.draw_pile)
    bname, bdesc = _buff_pair("fusion_overcharge")
    engine._add_buff_to(merc, "fusion_overcharge", bname, bdesc, 2)

    run.players[merc_uid] = merc
    if merc_uid not in run.party_order:
        run.party_order.append(merc_uid)
    full_order = getattr(run, "_full_party_order", None)
    if isinstance(full_order, list) and merc_uid not in full_order:
        full_order.append(merc_uid)

    fm = getattr(run, "floor_map", None)
    if fm is not None and isinstance(getattr(fm, "player_session_map", None), dict):
        sid = fm.player_session_map.get(owner_uid) or fm.player_session_map.get(run.user_id)
        if sid:
            fm.player_session_map[merc_uid] = sid
            sess = fm.active_sessions.get(sid)
            if sess is not None and isinstance(getattr(sess, "participants", None), list):
                if merc_uid not in sess.participants:
                    sess.participants.append(merc_uid)

    turn_ready = run.node_data.setdefault("turn_ready", {})
    if isinstance(turn_ready, dict):
        turn_ready[merc_uid] = True
    run.node_data["chireiden_utsuho_joined"] = True
    from ...core.progress.achievement_service import record_run_achievement_stat

    record_run_achievement_stat(getattr(engine, "save_manager", None), run, "chireiden_utsuho_allies", 1, battle_engine=engine)

    banner = get_locale_text("i18n_chireiden.utsuho_ally.join_banner")
    if logs is not None:
        logs.append(banner)
    else:
        engine._log_event(run, banner)
    return True


class ChireidenBaseEnemy(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List:
        cfg = ENEMY_CHIREIDEN_CONFIG.get(self.name) or ENEMY_CONFIG.get(self.name) or {}
        return _intents_from_entries(list(cfg.get("intents", [])), enemy.actions, enemy.bonus_actions)

    def _emit(self, engine, run, logs: Optional[List[str]], msg: str):
        if logs is not None:
            logs.append(msg)
        else:
            engine._log_event(run, msg)

    def execute_intent(self, run, engine, enemy, intent, logs: Optional[List[str]] = None):
        itype = intent.type
        val = int(intent.val or 0)
        bonus = _strength_bonus(enemy) + _overcharge_bonus(enemy)
        tag = _enemy_idx_tag(run, enemy)
        act_name = get_locale_text(f"i18n_chireiden.actions.{itype}")

        if itype in ("turbine_steam_slam", "xen_headcrab_leap"):
            dmg = val + bonus
            engine._damage_target(run, "p0", dmg, source=f"enemy:{enemy.name}", damage_type="piercing" if itype == "xen_headcrab_leap" else "bludgeoning")
            self._emit(engine, run, logs, get_locale_text("i18n_chireiden.actions.attack_log", name=enemy.name, action=act_name, dmg=dmg))
        elif itype in ("drone_orbital_laser", "portal_ion_beam", "xen_vortigaunt_bolt", "tokamak_arc_sweep", "xen_controller_psi_lance"):
            dtype = "lightning" if itype in ("portal_ion_beam", "xen_vortigaunt_bolt", "tokamak_arc_sweep") else ("psychic" if itype == "xen_controller_psi_lance" else "force")
            dmg = val + bonus
            engine._damage_target(run, "p0", dmg, source=f"enemy:{enemy.name}", damage_type=dtype)
            self._emit(engine, run, logs, get_locale_text("i18n_chireiden.actions.attack_log", name=enemy.name, action=act_name, dmg=dmg))
        elif itype in ("lbe_molten_splash", "xen_bullsquid_acid"):
            dmg = val + bonus
            dtype = "fire" if itype == "lbe_molten_splash" else "acid"
            engine._damage_target(run, "p0", dmg, source=f"enemy:{enemy.name}", damage_type=dtype)
            b_id = "weak" if itype == "lbe_molten_splash" else "vulnerable"
            bname, bdesc = _buff_pair(b_id)
            engine._add_buff_to(run.player, b_id, bname, bdesc, 2 if itype == "lbe_molten_splash" else 1)
            self._emit(engine, run, logs, get_locale_text("i18n_chireiden.actions.attack_log", name=enemy.name, action=act_name, dmg=dmg))
        elif itype in ("turbine_shield_vent", "xen_headcrab_burrow"):
            engine._gain_shield(run, tag, val)
            if itype == "turbine_shield_vent":
                sname, sdesc = _buff_pair("strength")
                engine._add_buff_to(enemy, "strength", sname, sdesc, 2)
            self._emit(engine, run, logs, get_locale_text("i18n_chireiden.actions.buff_log", name=enemy.name, action=act_name, shield=val))
        elif itype == "lbe_dense_wall":
            engine._gain_shield(run, tag, val)
            engine._heal_target(run, tag, 8)
            self._emit(engine, run, logs, get_locale_text("i18n_chireiden.actions.buff_log", name=enemy.name, action=act_name, shield=val))
        elif itype in ("tokamak_field_lock", "portal_magnetic_pulse"):
            sname, sdesc = _buff_pair("strength")
            str_gain = 3 if itype == "portal_magnetic_pulse" else 2
            for e in run.enemies:
                if e.hp > 0:
                    engine._gain_shield(run, _enemy_idx_tag(run, e), val)
                    engine._add_buff_to(e, "strength", sname, sdesc, str_gain)
            self._emit(engine, run, logs, get_locale_text("i18n_chireiden.actions.portal_field_charge", name=enemy.name, shield=val))
        elif itype in ("drone_he3_drop", "xen_houndeye_sonic", "portal_xen_bombard"):
            dmg = val + bonus
            dtype = "fire" if itype == "drone_he3_drop" else ("thunder" if itype == "xen_houndeye_sonic" else "force")
            engine._damage_target(run, "p0", dmg, source=f"enemy:{enemy.name}", damage_type=dtype)
            if itype == "drone_he3_drop" and _is_first_aoe_tick(run):
                for e in run.enemies:
                    if e.hp > 0:
                        engine._gain_shield(run, _enemy_idx_tag(run, e), 8)
            self._emit(engine, run, logs, get_locale_text("i18n_chireiden.actions.aoe_log", name=enemy.name, action=act_name, dmg=dmg))
        elif itype == "xen_controller_overdrive":
            sname, sdesc = _buff_pair("strength")
            for e in run.enemies:
                if e.hp > 0:
                    engine._add_buff_to(e, "strength", sname, sdesc, max(1, val))
                    engine._heal_target(run, _enemy_idx_tag(run, e), 14)
            self._emit(engine, run, logs, get_locale_text("i18n_chireiden.actions.buff_log", name=enemy.name, action=act_name, shield=0))


@register_enemy("非想天则涡轮机兵")
@register_enemy("月都氦三物流机")
@register_enemy("铅铋液态金属怪")
@register_enemy("托卡马克电弧守卫")
@register_enemy("Xen猎头蟹")
@register_enemy("Xen猎犬眼")
@register_enemy("Xen弗地冈")
@register_enemy("Xen牛鱿")
@register_enemy("Xen控制器")
class ChireidenUnitEnemy(ChireidenBaseEnemy):
    pass


@register_enemy("火焰猫燐")
class KaenbyouRinEnemy(ChireidenBaseEnemy):
    def on_battle_start(self, run, enemy, engine):
        if not any(b.id == "lbe_thermal_inertia" for b in enemy.buffs):
            bname, bdesc = _buff_pair("lbe_thermal_inertia")
            enemy.buffs.append(BuffState(id="lbe_thermal_inertia", name=bname, stacks=1, desc=bdesc))

    def execute_intent(self, run, engine, enemy, intent, logs: Optional[List[str]] = None):
        itype = intent.type
        val = int(intent.val or 0)
        bonus = _strength_bonus(enemy) + _overcharge_bonus(enemy)
        tag = _enemy_idx_tag(run, enemy)
        act_name = get_locale_text(f"i18n_chireiden.actions.{itype}")
        if itype == "rin_cat_wheel_charge":
            dmg = val + bonus
            engine._damage_target(run, "p0", dmg, source=f"enemy:{enemy.name}", damage_type="fire")
            vname, vdesc = _buff_pair("vulnerable")
            engine._add_buff_to(run.player, "vulnerable", vname, vdesc, 2)
            self._emit(engine, run, logs, get_locale_text("i18n_chireiden.actions.attack_log", name=enemy.name, action=act_name, dmg=dmg))
        elif itype == "rin_lbe_quench_guard":
            engine._gain_shield(run, tag, val)
            engine._heal_target(run, tag, 12)
            mname, mdesc = _buff_pair("magnetic_confinement")
            engine._add_buff_to(enemy, "magnetic_confinement", mname, mdesc, 2)
            self._emit(engine, run, logs, get_locale_text("i18n_chireiden.actions.buff_log", name=enemy.name, action=act_name, shield=val))
        elif itype == "rin_corpse_ash_nova":
            dmg = val + bonus
            if _is_first_aoe_tick(run):
                sname, sdesc = _buff_pair("strength")
                for e in run.enemies:
                    if e.hp > 0:
                        engine._add_buff_to(e, "strength", sname, sdesc, 2)
            engine._damage_target(run, "p0", dmg, source=f"enemy:{enemy.name}", damage_type="fire")
            self._emit(engine, run, logs, get_locale_text("i18n_chireiden.actions.aoe_log", name=enemy.name, action=act_name, dmg=dmg))
        else:
            super().execute_intent(run, engine, enemy, intent, logs)


@register_enemy("灵乌路空")
class UtsuhoReiujiBossEnemy(ChireidenBaseEnemy):
    def on_battle_start(self, run, enemy, engine):
        if not any(b.id == "headband_int19_aura" for b in enemy.buffs):
            bname, bdesc = _buff_pair("headband_int19_aura")
            enemy.buffs.append(BuffState(id="headband_int19_aura", name=bname, stacks=1, desc=bdesc))

    def roll_intents(self, run, engine, enemy) -> List:
        cfg = ENEMY_CHIREIDEN_CONFIG["灵乌路空"]
        entries = {item["id"]: item for item in cfg["intents"]}
        turn = int(run.node_data.get("turn_count", 1) or 1)
        primary_id = UTSUHO_INTENT_CYCLE[(turn - 1) % len(UTSUHO_INTENT_CYCLE)]
        secondary_id = UTSUHO_INTENT_CYCLE[turn % len(UTSUHO_INTENT_CYCLE)]
        bonus_id = "utsuho_elevator_logistics" if turn % 2 == 1 else "utsuho_d_he3_ray"
        return [
            EnemyIntentState(type=entries[primary_id]["id"], val=entries[primary_id]["val"], desc=entries[primary_id]["desc"], cost_a=1, cost_ba=0),
            EnemyIntentState(type=entries[secondary_id]["id"], val=entries[secondary_id]["val"], desc=entries[secondary_id]["desc"], cost_a=1, cost_ba=0),
            EnemyIntentState(type=entries[bonus_id]["id"], val=entries[bonus_id]["val"], desc=entries[bonus_id]["desc"], cost_a=0, cost_ba=1),
        ]

    def execute_intent(self, run, engine, enemy, intent, logs: Optional[List[str]] = None):
        itype = intent.type
        val = int(intent.val or 0)
        bonus = _strength_bonus(enemy) + _overcharge_bonus(enemy)
        tag = _enemy_idx_tag(run, enemy)
        act_name = get_locale_text(f"i18n_chireiden.actions.{itype}")
        if itype == "utsuho_d_he3_ray":
            dmg = val + bonus
            engine._damage_target(run, "p0", dmg, source=f"enemy:{enemy.name}", damage_type="fire")
            fname, fdesc = _buff_pair("fusion_overcharge")
            engine._add_buff_to(enemy, "fusion_overcharge", fname, fdesc, 2)
            self._emit(engine, run, logs, get_locale_text("i18n_chireiden.actions.attack_log", name=enemy.name, action=act_name, dmg=dmg))
        elif itype == "utsuho_elevator_logistics":
            engine._gain_shield(run, tag, val)
            sname, sdesc = _buff_pair("strength")
            fname, fdesc = _buff_pair("fusion_overcharge")
            engine._add_buff_to(enemy, "strength", sname, sdesc, 2)
            engine._add_buff_to(enemy, "fusion_overcharge", fname, fdesc, 3)
            self._emit(engine, run, logs, get_locale_text("i18n_chireiden.actions.he3_logistics_surge", shield=val, str=2))
        elif itype == "utsuho_tokamak_flare":
            dmg = val + bonus
            engine._damage_target(run, "p0", dmg, source=f"enemy:{enemy.name}", damage_type="fire")
            bname, bdesc = _buff_pair("burn")
            engine._add_buff_to(run.player, "burn", bname, bdesc, 2)
            self._emit(engine, run, logs, get_locale_text("i18n_chireiden.actions.aoe_log", name=enemy.name, action=act_name, dmg=dmg))
        elif itype == "utsuho_subterranean_sun":
            dmg = val + bonus
            engine._damage_target(run, "p0", dmg, source=f"enemy:{enemy.name}", damage_type="radiant")
            self._emit(engine, run, logs, get_locale_text("i18n_chireiden.actions.attack_log", name=enemy.name, action=act_name, dmg=dmg))
        else:
            super().execute_intent(run, engine, enemy, intent, logs)


@register_enemy("彭宁离子井·超级传送门·初阶裂隙")
@register_enemy("彭宁离子井·超级传送门·二阶扩口")
@register_enemy("彭宁离子井·超级传送门·三阶超临界")
@register_enemy("彭宁离子井·超级传送门·四阶终焉极井")
class PenningSuperPortalEnemy(ChireidenBaseEnemy):
    def on_battle_start(self, run, enemy, engine):
        p_cfg = SUPER_PORTAL_PHASE_BY_NAME.get(enemy.name, SUPER_PORTAL_PHASES[0])
        bid = p_cfg["buff_id"]
        if not any(b.id == bid for b in enemy.buffs):
            bname, bdesc = _buff_pair(bid)
            enemy.buffs.append(BuffState(id=bid, name=bname, stacks=1, desc=bdesc))
        if not any(getattr(e, "is_summon", False) and e.hp > 0 for e in run.enemies):
            _spawn_xen_unit(run, engine, p_cfg["summon_pool"][0])

    def roll_intents(self, run, engine, enemy) -> List:
        cfg = ENEMY_CHIREIDEN_CONFIG.get(enemy.name, ENEMY_CHIREIDEN_CONFIG["彭宁离子井·超级传送门·初阶裂隙"])
        entries = {item["id"]: item for item in cfg["intents"]}
        result: List[EnemyIntentState] = []
        alive_xen = sum(1 for e in run.enemies if getattr(e, "is_summon", False) and e.hp > 0)
        for idx in range(max(1, enemy.actions)):
            if idx == 0 and alive_xen < SUPER_PORTAL_MAX_XEN_ALIVE:
                chosen = entries["portal_summon_swarm"]
            else:
                chosen = entries["portal_ion_beam"] if idx % 2 == 1 else entries["portal_xen_bombard"]
            result.append(EnemyIntentState(type=chosen["id"], val=chosen["val"], desc=chosen["desc"], cost_a=1, cost_ba=0))
        for idx in range(max(0, enemy.bonus_actions)):
            chosen = entries["portal_magnetic_pulse"] if idx == 0 else entries["portal_xen_bombard"]
            result.append(EnemyIntentState(type=chosen["id"], val=chosen["val"], desc=chosen["desc"], cost_a=0, cost_ba=1))
        return result

    def execute_intent(self, run, engine, enemy, intent, logs: Optional[List[str]] = None):
        if intent.type == "portal_summon_swarm":
            p_cfg = SUPER_PORTAL_PHASE_BY_NAME.get(enemy.name, SUPER_PORTAL_PHASES[0])
            _spawn_xen_wave(run, enemy, p_cfg, engine, logs)
            sname, sdesc = _buff_pair("strength")
            for e in run.enemies:
                if e.hp > 0:
                    engine._add_buff_to(e, "strength", sname, sdesc, 1)
            return
        super().execute_intent(run, engine, enemy, intent, logs)

    def on_enemy_before_death(self, run, enemy, event, engine):
        cur_cfg = SUPER_PORTAL_PHASE_BY_NAME.get(enemy.name)
        if not cur_cfg or cur_cfg["phase"] >= 4:
            return
        next_phase = cur_cfg["phase"] + 1
        event.cancel()
        enemy.hp = 1
        enemy.shield = 0
        enemy.intents.clear()
        pname, pdesc = _buff_pair("phase_transition_immune")
        if not any(b.id == "phase_transition_immune" for b in enemy.buffs):
            enemy.buffs.append(BuffState(id="phase_transition_immune", name=pname, stacks=1, desc=pdesc))
        enemy.intents.append(EnemyIntentState(
            type="phase_transition",
            val=0,
            desc=get_locale_text("i18n_chireiden.actions.portal_phase_intent", phase=next_phase),
            cost_a=1,
            cost_ba=0,
        ))
        run.node_data.setdefault("pending_transitions", {})[enemy.name] = next_phase

    def apply_phase_transition(self, run, enemy, target_phase: int, engine, logs: list):
        if target_phase < 1 or target_phase > len(SUPER_PORTAL_PHASES):
            return
        cfg = SUPER_PORTAL_PHASES[target_phase - 1]
        act_a, act_ba = cfg["actions"]
        enemy.name = cfg["name"]
        enemy.max_hp = cfg["hp"]
        enemy.hp = cfg["hp"]
        enemy.shield = 20 * target_phase
        enemy.actions = act_a
        enemy.max_actions = act_a
        enemy.bonus_actions = act_ba
        enemy.max_bonus_actions = act_ba
        enemy.buffs.clear()
        bname, bdesc = _buff_pair(cfg["buff_id"])
        enemy.buffs.append(BuffState(id=cfg["buff_id"], name=bname, stacks=1, desc=bdesc))
        pname, pdesc = _buff_pair("phase_transition_immune")
        enemy.buffs.append(BuffState(id="phase_transition_immune", name=pname, stacks=1, desc=pdesc))
        enemy.intents = [EnemyIntentState(
            type="phase_transition",
            val=0,
            desc=get_locale_text("i18n_chireiden.actions.portal_phase_intent", phase=target_phase),
            cost_a=1,
            cost_ba=0,
        )]
        logs.append(get_locale_text(
            "i18n_chireiden.utsuho_ally.phase_banner",
            phase=target_phase,
            form_name=cfg["name"],
            max_hp=cfg["hp"],
        ))
        if target_phase >= 2:
            ensure_utsuho_ally_joined(run, engine, logs)
        _spawn_xen_wave(run, enemy, cfg, engine, logs)
        from ...core.world.encounter_lore import record_encounter_for_run

        record_encounter_for_run(getattr(engine, "save_manager", None), run, cfg["name"])
