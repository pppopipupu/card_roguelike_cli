import random
from typing import List, Optional

from .base import EnemyTemplate, register_enemy
from ...data.enemies.enemy_data import ENEMY_CONFIG
from ...data.enemies.enemy_data_bleak_falls import BLEAK_DRAUGR_SUMMON_NAME, ENEMY_BLEAK_FALLS_CONFIG
from ...data.text.locale_data import get_locale_text
from ...models.state import EnemyIntentState, EnemyState


def _enemy_intents_from_config(enemy_name: str, main_count: int, bonus_count: int) -> List[EnemyIntentState]:
    cfg = ENEMY_CONFIG.get(enemy_name, {})
    entries = list(cfg.get("intents", []))
    if not entries:
        return []
    result = []
    for _ in range(max(1, main_count)):
        entry = random.choice(entries)
        result.append(EnemyIntentState(
            type=entry.get("id", "attack"),
            val=entry.get("val", 5),
            desc=entry.get("desc", ""),
            cost_a=1,
            cost_ba=0,
        ))
    for _ in range(max(0, bonus_count)):
        entry = random.choice(entries)
        result.append(EnemyIntentState(
            type=entry.get("id", "attack"),
            val=entry.get("val", 4),
            desc=entry.get("desc", ""),
            cost_a=0,
            cost_ba=1,
        ))
    return result


def _strength_bonus(enemy) -> int:
    return sum(b.stacks for b in getattr(enemy, "buffs", []) if b.id == "strength")


def _idx_target(run, enemy) -> str:
    if enemy in run.enemies:
        return f"e{run.enemies.index(enemy) + 1}"
    return "e1"


class BleakFallsEnemyBase(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List:
        return _enemy_intents_from_config(self.name, enemy.actions, enemy.bonus_actions)

    def execute_intent(self, run, engine, enemy, intent, logs: Optional[List[str]] = None):
        itype = intent.type
        val = int(intent.val or 0)
        str_val = _strength_bonus(enemy)
        target_tag = _idx_target(run, enemy)

        def emit(key: str, **kwargs):
            text = get_locale_text(f"i18n_bleak_falls.enemies.{key}", **kwargs)
            if logs is not None:
                logs.append(text)
            else:
                engine._log_event(run, text)

        def buff_pair(prefix: str) -> tuple[str, str]:
            return (
                get_locale_text(f"i18n_bleak_falls.enemies.buffs.{prefix}_name"),
                get_locale_text(f"i18n_bleak_falls.enemies.buffs.{prefix}_desc"),
            )

        if itype in ("bandit_slash", "draugr_cleave"):
            dmg = val
            engine._damage_target(run, "p0", dmg, source=f"enemy:{enemy.name}", damage_type="slashing")
            emit(itype, name=enemy.name, dmg=dmg)
        elif itype in ("bandit_throw", "arvel_backstab"):
            dmg = val
            engine._damage_target(run, "p0", dmg, source=f"enemy:{enemy.name}", damage_type="piercing")
            emit(itype, name=enemy.name, dmg=dmg)
        elif itype in ("bandit_shield", "draugr_armor"):
            engine._gain_shield(run, target_tag, val)
            emit(itype, name=enemy.name, shield=val)
        elif itype == "bandit_warcry":
            bname, bdesc = buff_pair("strength")
            for other in run.enemies:
                if other.hp > 0:
                    engine._add_buff_to(other, "strength", bname, bdesc, max(1, val))
            emit("bandit_warcry", name=enemy.name, str=max(1, val))
        elif itype == "spider_bite":
            dmg = val
            engine._damage_target(run, "p0", dmg, source=f"enemy:{enemy.name}", damage_type="cold")
            vname, vdesc = buff_pair("cold_vuln")
            engine._add_buff_to(run.player, "minor_vulnerable_cold", vname, vdesc, 1)
            emit("spider_bite", name=enemy.name, dmg=dmg, vuln=1)
        elif itype == "spider_web":
            dmg = val
            engine._damage_target(run, "p0", dmg, source=f"enemy:{enemy.name}", damage_type="cold")
            bname, bdesc = buff_pair("lose_ba")
            engine._add_buff_to(run.player, "next_turn_lose_ba", bname, bdesc, 1)
            emit("spider_web", name=enemy.name, dmg=dmg)
        elif itype == "spider_cocoon":
            engine._gain_shield(run, target_tag, val)
            heal_amt = min(enemy.max_hp - enemy.hp, 4)
            enemy.hp += heal_amt
            emit("spider_cocoon", name=enemy.name, shield=val, heal=heal_amt)
        elif itype == "arvel_smoke":
            engine._gain_shield(run, target_tag, val)
            bname, bdesc = buff_pair("strength")
            engine._add_buff_to(enemy, "strength", bname, bdesc, 1)
            emit("arvel_smoke", name=enemy.name, shield=val)
        elif itype == "draugr_frost":
            dmg = val
            engine._damage_target(run, "p0", dmg, source=f"enemy:{enemy.name}", damage_type="cold")
            emit("draugr_frost", name=enemy.name, dmg=dmg)
        elif itype == "wraith_drain":
            dmg = val
            engine._damage_target(run, "p0", dmg, source=f"enemy:{enemy.name}", damage_type="necrotic")
            heal_amt = min(enemy.max_hp - enemy.hp, 3)
            enemy.hp += heal_amt
            emit("wraith_drain", name=enemy.name, dmg=dmg, heal=heal_amt)
        elif itype == "wraith_chant":
            bname, bdesc = buff_pair("strength")
            for idx_e, other in enumerate(run.enemies, 1):
                if other.hp > 0:
                    engine._gain_shield(run, f"e{idx_e}", val)
                    engine._add_buff_to(other, "strength", bname, bdesc, 1)
            emit("wraith_chant", name=enemy.name, shield=val, str=1)
        elif itype == "overlord_shout":
            dmg = val
            engine._damage_target(run, "p0", dmg, source=f"enemy:{enemy.name}", damage_type="force")
            bname, bdesc = buff_pair("lose_a")
            engine._add_buff_to(run.player, "next_turn_lose_a", bname, bdesc, 1)
            emit("overlord_shout", name=enemy.name, dmg=dmg)
        elif itype == "overlord_summon":
            if len([e for e in run.enemies if e.hp > 0]) < 4:
                new_draugr = EnemyState(
                    name=BLEAK_DRAUGR_SUMMON_NAME,
                    hp=22,
                    max_hp=22,
                    shield=0,
                    actions=1,
                    bonus_actions=1,
                    is_summon=True,
                    max_actions=1,
                    max_bonus_actions=1,
                )
                run.enemies.append(new_draugr)
                emit("overlord_summon", name=enemy.name)
            else:
                engine._gain_shield(run, target_tag, 10)
                bname, bdesc = buff_pair("strength")
                engine._add_buff_to(enemy, "strength", bname, bdesc, 1)
                emit("overlord_summon_fallback", name=enemy.name, shield=10, str=1)


for _bf_enemy_name in ENEMY_BLEAK_FALLS_CONFIG:
    register_enemy(_bf_enemy_name)(BleakFallsEnemyBase)
