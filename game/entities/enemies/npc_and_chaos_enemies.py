import random
from typing import Dict, List, Optional
from .base import ALL_ENEMIES, EnemyTemplate
from .trash_talk_actions import try_trash_talk
from ...data.enemy_data import ENEMY_CONFIG
from ...data.locale_data import get_locale_text
from ...models.state import CardState, EnemyIntentState

CHAOS_INTENT_SPECS: Dict[str, dict] = {
    "forge_hammer": {"kind": "attack", "damage_type": "bludgeoning", "debuff": ("weak", 1)},
    "quench_guard": {"kind": "guard", "strength": 1},
    "slag_spray": {"kind": "attack", "damage_type": "fire", "debuff": ("burning", 1)},
    "poison_dart": {"kind": "attack", "damage_type": "piercing", "debuff": ("poison", 1)},
    "smoke_screen": {"kind": "guard", "debuff": ("drain_ba", 1)},
    "debt_collect": {"kind": "attack", "damage_type": "slashing", "self_shield": 3},
    "manuscript_blast": {"kind": "attack", "damage_type": "psychic", "dazed": 1},
    "arcane_ward": {"kind": "guard", "strength": 1},
    "knowledge_burn": {"kind": "attack", "damage_type": "force"},
    "snare_shot": {"kind": "attack", "damage_type": "piercing", "debuff": ("bleed", 1)},
    "evasive_roll": {"kind": "guard", "strength": 1},
    "desperate_volley": {"kind": "attack", "damage_type": "piercing"},
    "lantern_burn": {"kind": "attack", "damage_type": "necrotic", "debuff": ("weak", 1)},
    "sanctuary_prayer": {"kind": "guard", "self_heal": 3},
    "seal_backlash": {"kind": "attack", "damage_type": "psychic"},
    "abacus_smash": {"kind": "attack", "damage_type": "bludgeoning", "strip_shield": 3},
    "golden_barrier": {"kind": "guard"},
    "bankrupt_strike": {"kind": "attack", "damage_type": "force"},
    "espresso_splash": {"kind": "attack", "damage_type": "fire", "debuff": ("burning", 1)},
    "counter_cover": {"kind": "guard", "self_heal": 3},
    "closing_sweep": {"kind": "attack", "damage_type": "bludgeoning", "debuff": ("weak", 1)},
    "chain_lightning": {"kind": "attack", "damage_type": "lightning", "debuff": ("shock", 1)},
    "mage_armor": {"kind": "guard", "strength": 1},
    "soul_trap": {"kind": "attack", "damage_type": "psychic", "dazed": 1},
    "compass_slash": {"kind": "attack", "damage_type": "piercing"},
    "star_chart_veil": {"kind": "guard", "strength": 1},
    "astral_ray": {"kind": "attack", "damage_type": "force"},
    "ember_lash": {"kind": "attack", "damage_type": "fire", "debuff": ("burning", 2)},
    "brazier_guard": {"kind": "guard", "strength": 1},
    "cinder_burst": {"kind": "attack", "damage_type": "fire"},
    "yin_yang_bounce": {"kind": "attack", "damage_type": "force", "self_shield": 5, "log_key": "i18n_chaos_expansion.enemies.hakurei_reimu.yin_yang_log"},
    "duplex_barrier": {"kind": "guard", "strength": 2, "log_key": "i18n_chaos_expansion.enemies.hakurei_reimu.barrier_log"},
    "fantasy_seal": {"kind": "attack", "damage_type": "radiant", "log_key": "i18n_chaos_expansion.enemies.hakurei_reimu.seal_log"},
    "stardust_reverie": {"kind": "attack", "damage_type": "radiant", "debuff": ("burning", 2), "log_key": "i18n_chaos_expansion.enemies.kirisame_marisa.stardust_log"},
    "broom_dodge": {"kind": "guard", "strength": 2, "log_key": "i18n_chaos_expansion.enemies.kirisame_marisa.dodge_log"},
    "master_spark": {"kind": "attack", "damage_type": "force", "log_key": "i18n_chaos_expansion.enemies.kirisame_marisa.spark_log"},
    "aglaophotis_burn": {"kind": "attack", "damage_type": "fire", "debuff": ("burning", 2), "log_key": "i18n_chaos_expansion.enemies.patchouli_knowledge.fire_log"},
    "philosopher_stone": {"kind": "guard", "strength": 2, "log_key": "i18n_chaos_expansion.enemies.patchouli_knowledge.stone_log"},
    "princess_undine": {"kind": "attack", "damage_type": "cold", "debuff": ("weak", 1), "log_key": "i18n_chaos_expansion.enemies.patchouli_knowledge.water_log"},
    "contract_whisper": {"kind": "attack", "damage_type": "psychic", "dazed": 1, "log_key": "i18n_chaos_expansion.enemies.kyubey.whisper_log"},
    "backup_body": {"kind": "guard", "self_heal": 6, "log_key": "i18n_chaos_expansion.enemies.kyubey.backup_log"},
    "entropy_glare": {"kind": "attack", "damage_type": "true", "log_key": "i18n_chaos_expansion.enemies.kyubey.glare_log"},
    "ribbon_bind": {"kind": "attack", "damage_type": "piercing", "debuff": ("drain_ba", 1), "log_key": "i18n_chaos_expansion.enemies.tomoe_mami.ribbon_log"},
    "musket_dance": {"kind": "attack", "damage_type": "piercing", "self_shield": 5, "log_key": "i18n_chaos_expansion.enemies.tomoe_mami.musket_log"},
    "tiro_finale": {"kind": "attack", "damage_type": "force", "log_key": "i18n_chaos_expansion.enemies.tomoe_mami.finale_log"},
    "divine_shooter": {"kind": "attack", "damage_type": "force", "log_key": "i18n_chaos_expansion.enemies.takamachi_nanoha.shooter_log"},
    "barrier_jacket": {"kind": "guard", "strength": 2, "log_key": "i18n_chaos_expansion.enemies.takamachi_nanoha.jacket_log"},
    "starlight_breaker": {"kind": "attack", "damage_type": "force", "log_key": "i18n_chaos_expansion.enemies.takamachi_nanoha.breaker_log"},
    "plasma_scythe": {"kind": "attack", "damage_type": "lightning", "debuff": ("shock", 1), "log_key": "i18n_chaos_expansion.enemies.fate_testarossa.scythe_log"},
    "sonic_form": {"kind": "guard", "strength": 2, "log_key": "i18n_chaos_expansion.enemies.fate_testarossa.sonic_log"},
    "thunder_rage": {"kind": "attack", "damage_type": "lightning", "log_key": "i18n_chaos_expansion.enemies.fate_testarossa.thunder_log"},
    "gargoyle_stone_slam": {"kind": "attack", "damage_type": "bludgeoning", "self_shield": 4},
    "gargoyle_fortify": {"kind": "guard", "strength": 2},
    "beast_savage_bite": {"kind": "attack", "damage_type": "piercing", "debuff": ("bleed", 2)},
    "beast_howl": {"kind": "guard", "strength": 2},
    "slime_frost_spit": {"kind": "attack", "damage_type": "cold", "debuff": ("weak", 1)},
    "slime_chill_shell": {"kind": "guard", "strength": 1},
    "archer_bleed_arrow": {"kind": "attack", "damage_type": "piercing", "debuff": ("bleed", 1)},
    "archer_aim_step": {"kind": "guard", "strength": 2},
    "bone_shield_bash": {"kind": "attack", "damage_type": "bludgeoning", "self_shield": 4},
    "bone_slash": {"kind": "attack", "damage_type": "slashing"},
}


class ConfiguredChaosEnemyTemplate(EnemyTemplate):
    def _enemy_tag(self, enemy) -> Optional[str]:
        if enemy in getattr(enemy, "_parent_run_enemies", []):
            return None
        return None

    def roll_intents(self, run, engine, enemy) -> List[EnemyIntentState]:
        cfg = ENEMY_CONFIG.get(self.name, {})
        intents = cfg.get("intents", [])
        if not intents:
            return super().roll_intents(run, engine, enemy)
        intents_list: List[EnemyIntentState] = []
        turn_key = f"chaos_turn_{self.name}"
        idx = int(run.node_data.get(turn_key, 0))
        run.node_data[turn_key] = idx + 1
        for offset in range(max(1, enemy.actions)):
            chosen = intents[(idx + offset) % len(intents)]
            intents_list.append(
                EnemyIntentState(
                    type=chosen["id"],
                    val=int(chosen.get("val", 6)),
                    desc=chosen.get("desc", chosen["id"]),
                    cost_a=1,
                    cost_ba=0,
                )
            )
        guard_intents = [it for it in intents if CHAOS_INTENT_SPECS.get(it["id"], {}).get("kind") == "guard"] or intents
        for _ in range(max(0, enemy.bonus_actions)):
            chosen = random.choice(guard_intents)
            intents_list.append(
                EnemyIntentState(
                    type=chosen["id"],
                    val=max(2, int(chosen.get("val", 4)) // 2),
                    desc=chosen.get("desc", chosen["id"]),
                    cost_a=0,
                    cost_ba=1,
                )
            )
        return intents_list

    def execute_intent(self, run, engine, enemy, intent, logs: Optional[List[str]] = None):
        if logs is None:
            logs = []
        try_trash_talk(run, enemy, logs)
        spec = CHAOS_INTENT_SPECS.get(intent.type)
        if not spec:
            return super().execute_intent(run, engine, enemy, intent, logs)
        p = run.player
        strength = 0
        for buff in getattr(enemy, "buffs", []):
            if buff.id == "strength":
                strength += buff.stacks
        enemy_idx = run.enemies.index(enemy) + 1 if enemy in run.enemies else 1
        etag = f"e{enemy_idx}"
        dmg_dealt = int(intent.val) + strength
        if spec["kind"] == "attack":
            if spec.get("strip_shield", 0) > 0 and getattr(p, "shield", 0) > 0:
                p.shield = max(0, p.shield - int(spec["strip_shield"]))
            engine._damage_target(
                run,
                "p0",
                dmg_dealt,
                source=f"enemy:{enemy.name}",
                damage_type=spec.get("damage_type", "physical"),
            )
            if spec.get("self_shield", 0) > 0:
                engine._gain_shield(run, etag, int(spec["self_shield"]))
        else:
            engine._gain_shield(run, etag, int(intent.val))
            if spec.get("self_heal", 0) > 0:
                engine._heal_target(run, etag, int(spec["self_heal"]))

        if spec.get("strength", 0) > 0:
            engine._add_buff_to(
                enemy,
                "strength",
                get_locale_text("i18n_enemy_misc.common.strength_name"),
                get_locale_text("i18n_chaos_expansion.enemies.strength_desc"),
                int(spec["strength"]),
            )
        debuff = spec.get("debuff")
        if debuff:
            bid, stacks = debuff
            bname = get_locale_text(f"i18n_chaos_expansion.enemies.buff_{bid}_name") or bid
            bdesc = get_locale_text(f"i18n_chaos_expansion.enemies.buff_{bid}_desc") or bid
            engine._add_buff_to(p, bid, bname, bdesc, int(stacks))
        if spec.get("dazed", 0) > 0:
            for _ in range(int(spec["dazed"])):
                p.discard_pile.append(CardState(id="dazed"))

        move_label = str(intent.desc).split(" (", 1)[0]
        log_key = spec.get("log_key")
        if log_key:
            logs.append(
                get_locale_text(
                    log_key,
                    name=enemy.name,
                    dmg=dmg_dealt,
                    shield=int(spec.get("self_shield", intent.val)),
                    heal=int(spec.get("self_heal", 0)),
                )
            )
        elif spec["kind"] == "attack":
            logs.append(
                get_locale_text(
                    "i18n_chaos_expansion.enemies.npc_common.strike_log",
                    name=enemy.name,
                    move=move_label,
                    dmg=dmg_dealt,
                )
            )
        else:
            logs.append(
                get_locale_text(
                    "i18n_chaos_expansion.enemies.npc_common.guard_log",
                    name=enemy.name,
                    move=move_label,
                    shield=int(intent.val),
                )
            )


class KyubeyEnemyTemplate(ConfiguredChaosEnemyTemplate):
    def on_enemy_before_death(self, run, enemy, event, engine):
        if run.node_data.get("kyubey_backup_used"):
            return
        run.node_data["kyubey_backup_used"] = True
        event.cancel()
        enemy.hp = max(12, enemy.max_hp // 2)
        enemy.shield = 6
        engine._log_event(run, get_locale_text("i18n_chaos_expansion.enemies.kyubey_revive", name=enemy.name, hp=enemy.hp))


NPC_AND_CHAOS_NAMES = (
    "狂怒铁匠·托林",
    "黑市掮客·莫斯",
    "狂乱学者·艾拉",
    "绝望斥候·里昂",
    "幽暗守坛人·赛伦",
    "秘境行商·维克多",
    "暴走店长·布鲁诺",
    "白漫城宫廷法师",
    "星界制图师",
    "古坛守望者",
    "博丽灵梦",
    "雾雨魔理沙",
    "帕秋莉·诺蕾姬",
    "巴麻美",
    "高町奈叶",
    "菲特·泰斯特罗莎",
    "石像鬼守卫",
    "狂暴野兽",
    "冰霜史莱姆",
    "骷髅弓箭手",
    "骨轻卒",
)

for _enemy_name in NPC_AND_CHAOS_NAMES:
    ALL_ENEMIES[_enemy_name] = ConfiguredChaosEnemyTemplate(_enemy_name)

SPECIAL_CHAOS_TEMPLATES = {
    "丘比": KyubeyEnemyTemplate,
}

for _sname, _scls in SPECIAL_CHAOS_TEMPLATES.items():
    ALL_ENEMIES[_sname] = _scls(_sname)
