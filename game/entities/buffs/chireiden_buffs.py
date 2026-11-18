from .base import BuffImpl
from .registry import register_buff
from ...data.buff_data import BUFF_CONFIG


def _stat(instance, buff_id: str, key: str, default):
    cfg = BUFF_CONFIG.get(buff_id, {})
    return getattr(instance, key, cfg.get(key, default))


def _is_attack_owner(event, entity) -> bool:
    run = event.run
    if entity == run.player and event.source == "p0":
        return True
    if entity in run.enemies:
        try:
            idx = run.enemies.index(entity)
        except ValueError:
            return False
        return event.source == f"e{idx + 1}"
    return False


def _defend_target_tag(run, entity) -> str:
    if entity == run.player:
        return "p0"
    for idx, uid in enumerate(getattr(run, "party_order", []) or []):
        if run.players.get(uid) is entity:
            return f"a{idx + 1}"
    if entity in run.enemies:
        try:
            return f"e{run.enemies.index(entity) + 1}"
        except ValueError:
            return ""
    return ""


def _is_defend_owner(event, entity) -> bool:
    run = event.run
    target = getattr(event, "target", "")
    if entity == run.player and target == "p0":
        return True
    if target.startswith("a"):
        try:
            slot = int(target[1:]) - 1
        except ValueError:
            return False
        party = getattr(run, "party_order", []) or []
        if 0 <= slot < len(party):
            return run.players.get(party[slot]) is entity
    if entity in run.enemies:
        try:
            idx = run.enemies.index(entity)
        except ValueError:
            return False
        return target == f"e{idx + 1}"
    return False


@register_buff("fusion_overcharge")
class FusionOverchargeBuff(BuffImpl):
    def on_damage_calculate(self, event, buff_state, entity):
        if not _is_attack_owner(event, entity) or buff_state.stacks <= 0:
            return
        per_stack = int(_stat(self, "fusion_overcharge", "dmg_per_stack", 2))
        event.modified_damage += buff_state.stacks * per_stack

    def on_turn_end(self, event, buff_state, entity):
        is_player_entity = entity == event.run.player or entity in event.run.players.values()
        if event.is_player and is_player_entity:
            buff_state.stacks = buff_state.stacks // 2
            if buff_state.stacks <= 0 and buff_state in entity.buffs:
                entity.buffs.remove(buff_state)
        elif not event.is_player and entity in event.run.enemies:
            buff_state.stacks = buff_state.stacks // 2
            if buff_state.stacks <= 0 and buff_state in entity.buffs:
                entity.buffs.remove(buff_state)


@register_buff("magnetic_confinement")
class MagneticConfinementBuff(BuffImpl):
    def on_damage_calculate_defend(self, event, buff_state, entity):
        if not _is_defend_owner(event, entity) or buff_state.stacks <= 0 or event.modified_damage <= 0:
            return
        pct = int(_stat(self, "magnetic_confinement", "reduction_pct", 25))
        event.modified_damage = max(0, (event.modified_damage * (100 - pct)) // 100)

    def on_damage_take_defend(self, event, buff_state, entity, engine):
        if not _is_defend_owner(event, entity) or buff_state.stacks <= 0:
            return
        rebound = int(_stat(self, "magnetic_confinement", "rebound_shield", 4))
        buff_state.stacks -= 1
        if buff_state.stacks <= 0 and buff_state in entity.buffs:
            entity.buffs.remove(buff_state)
        tag = _defend_target_tag(event.run, entity)
        if tag and rebound > 0:
            engine._gain_shield(event.run, tag, rebound)


@register_buff("headband_int19_aura")
class HeadbandInt19AuraBuff(BuffImpl):
    def on_turn_end(self, event, buff_state, entity):
        if event.is_player or entity not in event.run.enemies or entity.hp <= 0:
            return
        cur = sum(b.stacks for b in entity.buffs if b.id == "fusion_overcharge")
        if cur < 8:
            gain = min(int(_stat(self, "headband_int19_aura", "overcharge_gain", 2)), 8 - cur)
            cfg = BUFF_CONFIG["fusion_overcharge"]
            event.engine._add_buff_to(entity, "fusion_overcharge", cfg["name"], cfg["desc"], gain)


@register_buff("lbe_thermal_inertia")
class LbeThermalInertiaBuff(BuffImpl):
    def on_turn_end(self, event, buff_state, entity):
        if event.is_player or entity not in event.run.enemies or entity.hp <= 0:
            return
        tag = _defend_target_tag(event.run, entity)
        shield_gain = int(_stat(self, "lbe_thermal_inertia", "end_turn_shield", 12))
        if tag and shield_gain > 0:
            event.engine._gain_shield(event.run, tag, shield_gain)


class _PenningRiftPhaseBuff(BuffImpl):
    buff_key = "penning_xen_rift_p1"

    def on_turn_end(self, event, buff_state, entity):
        if event.is_player or entity not in event.run.enemies or entity.hp <= 0:
            return
        str_gain = int(_stat(self, self.buff_key, "bonus_str_per_turn", 1))
        scfg = BUFF_CONFIG.get("strength", {})
        if str_gain > 0:
            event.engine._add_buff_to(entity, "strength", scfg.get("name", "strength"), scfg.get("desc", ""), str_gain)


@register_buff("penning_xen_rift_p1")
class PenningXenRiftP1Buff(_PenningRiftPhaseBuff):
    buff_key = "penning_xen_rift_p1"


@register_buff("penning_xen_rift_p2")
class PenningXenRiftP2Buff(_PenningRiftPhaseBuff):
    buff_key = "penning_xen_rift_p2"


@register_buff("penning_xen_rift_p3")
class PenningXenRiftP3Buff(_PenningRiftPhaseBuff):
    buff_key = "penning_xen_rift_p3"


@register_buff("penning_xen_rift_p4")
class PenningXenRiftP4Buff(_PenningRiftPhaseBuff):
    buff_key = "penning_xen_rift_p4"


@register_buff("xen_swarm_link")
class XenSwarmLinkBuff(BuffImpl):
    def on_turn_end(self, event, buff_state, entity):
        if event.is_player or entity not in event.run.enemies or entity.hp <= 0:
            return
        heal = int(_stat(self, "xen_swarm_link", "end_turn_heal", 4))
        tag = _defend_target_tag(event.run, entity)
        if tag and heal > 0:
            event.engine._heal_target(event.run, tag, heal)
