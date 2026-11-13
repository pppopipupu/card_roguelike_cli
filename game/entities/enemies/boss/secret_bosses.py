from typing import List
from ..base import EnemyTemplate, register_enemy
from ....core.inventory.deck_service import DeckService
from ....data.enemy_data import ENEMY_CONFIG
from ....data.locale_data import get_locale_text


def _make_intent(intent_id: str, val: int, desc: str, cost_a: int, cost_ba: int):
    from ....models.state import EnemyIntentState
    return EnemyIntentState(type=intent_id, val=val, desc=desc, cost_a=cost_a, cost_ba=cost_ba)


def _intent_val(name: str, intent_id: str, default: int) -> int:
    for entry in ENEMY_CONFIG.get(name, {}).get("intents", []):
        if entry.get("id") == intent_id:
            return int(entry.get("val", default))
    return default


@register_enemy("裂隙暗影领主")
class SecretRiftShadowLordTemplate(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List['EnemyIntentState']:
        turn = int(run.node_data.get("secret_boss_turn", 1))
        run.node_data["secret_boss_turn"] = turn + 1
        v_slash = _intent_val(self.name, "rift_slash", 11)
        v_veil = _intent_val(self.name, "shadow_veil", 14)
        v_mind = _intent_val(self.name, "mind_flay", 7)
        if turn % 2 == 1:
            return [
                _make_intent("rift_slash", v_slash, get_locale_text("i18n_grid_map.secret_boss.rift_slash_intent", val=v_slash), 1, 0),
                _make_intent("shadow_veil", v_veil, get_locale_text("i18n_grid_map.secret_boss.shadow_veil_intent", val=v_veil), 0, 1),
            ]
        return [
            _make_intent("mind_flay", v_mind, get_locale_text("i18n_grid_map.secret_boss.mind_flay_intent", val=v_mind), 1, 0),
            _make_intent("rift_slash", v_slash, get_locale_text("i18n_grid_map.secret_boss.rift_slash_intent", val=v_slash), 0, 1),
        ]

    def execute_intent(self, run, engine, enemy, intent, logs: List[str] = None):
        if logs is None:
            return ""
        strength = sum(b.stacks for b in enemy.buffs if b.id == "strength")
        if intent.type == "rift_slash":
            dmg = intent.val + strength
            engine._damage_target(run, "p0", dmg, source=f"enemy:{enemy.name}", damage_type="slashing")
            engine._add_buff_to(run.player, "void_weakness", get_locale_text("i18n_enemy_boss.buff_void_weakness"), get_locale_text("i18n_enemy_boss.buff_void_weakness_desc"), 1)
            logs.append(get_locale_text("i18n_grid_map.secret_boss.rift_slash_log", enemy_name=enemy.name, dmg=dmg))
        elif intent.type == "shadow_veil":
            engine._gain_shield(run, f"e{run.enemies.index(enemy)+1}" if enemy in run.enemies else "e1", intent.val)
            logs.append(get_locale_text("i18n_grid_map.secret_boss.shadow_veil_log", enemy_name=enemy.name, shield=intent.val))
        elif intent.type == "mind_flay":
            dmg = intent.val + strength
            engine._damage_target(run, "p0", dmg, source=f"enemy:{enemy.name}", damage_type="psychic")
            logs.append(get_locale_text("i18n_grid_map.secret_boss.mind_flay_log", enemy_name=enemy.name, dmg=dmg))
        return "\n".join(logs)


@register_enemy("星渊审判官")
class SecretAstralInquisitorTemplate(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List['EnemyIntentState']:
        turn = int(run.node_data.get("secret_boss_turn", 1))
        run.node_data["secret_boss_turn"] = turn + 1
        v_verdict = _intent_val(self.name, "astral_verdict", 14)
        v_ward = _intent_val(self.name, "starlight_ward", 18)
        v_lash = _intent_val(self.name, "gravity_lash", 9)
        if turn % 2 == 1:
            return [
                _make_intent("astral_verdict", v_verdict, get_locale_text("i18n_grid_map.secret_boss.astral_verdict_intent", val=v_verdict), 1, 0),
                _make_intent("starlight_ward", v_ward, get_locale_text("i18n_grid_map.secret_boss.starlight_ward_intent", val=v_ward), 0, 1),
            ]
        return [
            _make_intent("gravity_lash", v_lash, get_locale_text("i18n_grid_map.secret_boss.gravity_lash_intent", val=v_lash), 1, 0),
            _make_intent("astral_verdict", v_verdict, get_locale_text("i18n_grid_map.secret_boss.astral_verdict_intent", val=v_verdict), 1, 0),
        ]

    def execute_intent(self, run, engine, enemy, intent, logs: List[str] = None):
        if logs is None:
            return ""
        strength = sum(b.stacks for b in enemy.buffs if b.id == "strength")
        if intent.type == "astral_verdict":
            dmg = intent.val + strength
            engine._damage_target(run, "p0", dmg, source=f"enemy:{enemy.name}", damage_type="psychic")
            logs.append(get_locale_text("i18n_grid_map.secret_boss.astral_verdict_log", enemy_name=enemy.name, dmg=dmg))
        elif intent.type == "starlight_ward":
            engine._gain_shield(run, f"e{run.enemies.index(enemy)+1}" if enemy in run.enemies else "e1", intent.val)
            engine._add_buff_to(enemy, "strength", get_locale_text("i18n_battle_core.buff_strength_name"), get_locale_text("i18n_battle_core.buff_strength_desc"), 1)
            logs.append(get_locale_text("i18n_grid_map.secret_boss.starlight_ward_log", enemy_name=enemy.name, shield=intent.val))
        elif intent.type == "gravity_lash":
            dmg = intent.val + strength
            engine._damage_target(run, "p0", dmg, source=f"enemy:{enemy.name}", damage_type="bludgeoning")
            run.node_data["drain_ba"] = True
            logs.append(get_locale_text("i18n_grid_map.secret_boss.gravity_lash_log", enemy_name=enemy.name, dmg=dmg))
        return "\n".join(logs)


@register_enemy("深渊原初回响")
class SecretPrimordialEchoTemplate(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List['EnemyIntentState']:
        turn = int(run.node_data.get("secret_boss_turn", 1))
        run.node_data["secret_boss_turn"] = turn + 1
        v_roar = _intent_val(self.name, "primordial_roar", 16)
        v_aegis = _intent_val(self.name, "void_aegis", 22)
        v_cleave = _intent_val(self.name, "abyssal_cleave", 12)
        if turn % 2 == 1:
            return [
                _make_intent("primordial_roar", v_roar, get_locale_text("i18n_grid_map.secret_boss.primordial_roar_intent", val=v_roar), 1, 0),
                _make_intent("void_aegis", v_aegis, get_locale_text("i18n_grid_map.secret_boss.void_aegis_intent", val=v_aegis), 0, 1),
            ]
        return [
            _make_intent("abyssal_cleave", v_cleave, get_locale_text("i18n_grid_map.secret_boss.abyssal_cleave_intent", val=v_cleave), 1, 0),
            _make_intent("primordial_roar", v_roar, get_locale_text("i18n_grid_map.secret_boss.primordial_roar_intent", val=v_roar), 0, 1),
        ]

    def execute_intent(self, run, engine, enemy, intent, logs: List[str] = None):
        if logs is None:
            return ""
        strength = sum(b.stacks for b in enemy.buffs if b.id == "strength")
        if intent.type == "primordial_roar":
            dmg = intent.val + strength
            engine._damage_target(run, "p0", dmg, source=f"enemy:{enemy.name}", damage_type="psychic")
            DeckService.add_card_to_discard(run.player, "curse_dazed")
            logs.append(get_locale_text("i18n_grid_map.secret_boss.primordial_roar_log", enemy_name=enemy.name, dmg=dmg))
        elif intent.type == "void_aegis":
            engine._gain_shield(run, f"e{run.enemies.index(enemy)+1}" if enemy in run.enemies else "e1", intent.val)
            engine._add_buff_to(enemy, "strength", get_locale_text("i18n_battle_core.buff_strength_name"), get_locale_text("i18n_battle_core.buff_strength_desc"), 2)
            logs.append(get_locale_text("i18n_grid_map.secret_boss.void_aegis_log", enemy_name=enemy.name, shield=intent.val))
        elif intent.type == "abyssal_cleave":
            dmg = intent.val + strength
            engine._damage_target(run, "p0", dmg, source=f"enemy:{enemy.name}", damage_type="force")
            for mk in list(run.player.minions.keys()):
                if mk in run.player.minions:
                    engine._damage_target(run, f"p{mk}", dmg, source=f"enemy:{enemy.name}", damage_type="force")
            logs.append(get_locale_text("i18n_grid_map.secret_boss.abyssal_cleave_log", enemy_name=enemy.name, dmg=dmg))
        return "\n".join(logs)
