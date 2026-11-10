import random
from typing import List

from ..base import EnemyTemplate, register_enemy
from ....core.deck_service import DeckService
from ....data.buff_data import BUFF_CONFIG
from ....data.enemy_data import ENEMY_CONFIG
from ....data.locale_data import get_locale_text
from ...cards.base import ALL_CARDS

DEEPSEEK_CONFIG_NAME = "DeepSeek V4.1 Flash"


def _intent_ids(enemy_name: str) -> List[str]:
    return [entry.get("id", "") for entry in ENEMY_CONFIG.get(enemy_name, {}).get("intents", [])]


def _make_intent(enemy_name: str, intent_id: str, cost_ba: bool = False):
    from ....models.state import EnemyIntentState
    entry = next((it for it in ENEMY_CONFIG.get(enemy_name, {}).get("intents", []) if it.get("id") == intent_id), {})
    return EnemyIntentState(
        type=entry.get("id", intent_id),
        val=entry.get("val", 0),
        desc=entry.get("desc", ""),
        cost_a=0 if cost_ba else 1,
        cost_ba=1 if cost_ba else 0
    )


def _legacy_intent(enemy):
    from ....models.state import EnemyIntentState
    return EnemyIntentState(
        type=getattr(enemy, "intent_type", ""),
        val=getattr(enemy, "intent_val", 0),
        desc=getattr(enemy, "intent_desc", ""),
        cost_a=1,
        cost_ba=0
    )


def _roll_pool(enemy_name: str, intent_ids: List[str], main_count: int, bonus_count: int):
    states = [_make_intent(enemy_name, random.choice(intent_ids)) for _ in range(main_count)]
    states.extend(_make_intent(enemy_name, random.choice(intent_ids), True) for _ in range(bonus_count))
    return states


def _strength_of(enemy) -> int:
    return sum(b.stacks for b in getattr(enemy, "buffs", []) if b.id == "strength")


def _buff_labels(folder: str, buff_id: str):
    return (
        get_locale_text(f"i18n_enemy_normal.{folder}.buff_{buff_id}"),
        get_locale_text(f"i18n_enemy_normal.{folder}.buff_{buff_id}_desc")
    )


def _living_players(run):
    players = list(run.players.values()) if getattr(run, "coop_id", "") else [run.player]
    return [p for p in players if getattr(p, "hp", 0) > 0]


def _gain_enemy_shield(run, engine, enemy, amount: int):
    if enemy in run.enemies:
        engine._gain_shield(run, f"e{run.enemies.index(enemy)+1}", amount)


def _damage_player(run, engine, enemy, dmg: int, damage_type: str) -> str:
    before = len(run.node_data.get("battle_logs", []))
    engine._damage_target(run, "p0", dmg, source=f"enemy:{enemy.name}", damage_type=damage_type)
    logs = run.node_data.get("battle_logs", [])
    return logs.pop() if len(logs) > before else ""


@register_enemy("黑曜石巨人")
class ObsidianGiantTemplate(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List['EnemyIntentState']:
        return _roll_pool(self.name, _intent_ids(self.name), enemy.actions, enemy.bonus_actions)

    def execute_intent(self, run, engine, enemy, intent, logs: List[str] = None):
        if logs is None:
            logs = []
            intent = _legacy_intent(enemy)
        if intent.type == "obsidian_crush":
            dmg_msg = _damage_player(run, engine, enemy, intent.val + _strength_of(enemy), "bludgeoning")
            shield_suffix = ""
            if run.player.shield > 0:
                if run.player.shield >= 6:
                    drain_before = len(run.node_data.get("battle_logs", []))
                    engine._damage_target(run, "p0", 6, source=f"enemy:{enemy.name}", damage_type="bludgeoning")
                    after_logs = run.node_data.get("battle_logs", [])
                    if len(after_logs) > drain_before:
                        after_logs.pop()
                    shield_suffix = get_locale_text("i18n_enemy_normal.obsidian_giant.shield_suffix")
                else:
                    shield_suffix = get_locale_text("i18n_enemy_normal.obsidian_giant.expose_suffix")
                debuff_id = "minor_vulnerable_bludgeoning" if "minor_vulnerable_bludgeoning" in BUFF_CONFIG else "minor_vulnerable"
                buff_name, buff_desc = _buff_labels("obsidian_giant", debuff_id)
                engine._add_buff_to(run.player, debuff_id, buff_name, buff_desc, 1)
            logs.append(get_locale_text("i18n_enemy_normal.obsidian_giant.obsidian_crush", name=enemy.name, dmg_msg=dmg_msg, shield_suffix=shield_suffix))
        elif intent.type == "magma_harden":
            _gain_enemy_shield(run, engine, enemy, intent.val)
            buff_name, buff_desc = _buff_labels("obsidian_giant", "strength")
            engine._add_buff_to(enemy, "strength", buff_name, buff_desc, 2)
            logs.append(get_locale_text("i18n_enemy_normal.obsidian_giant.magma_harden", name=enemy.name, val=intent.val))


@register_enemy("暗影刺客")
class ShadowAssassinTemplate(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List['EnemyIntentState']:
        main_ids = [i for i in ("throat_slit", "shadow_ambush") if i in _intent_ids(self.name)]
        bonus_ids = [i for i in ("smoke_screen",) if i in _intent_ids(self.name)]
        return _roll_pool(self.name, main_ids, enemy.actions, 0) + _roll_pool(self.name, bonus_ids, 0, enemy.bonus_actions)

    def execute_intent(self, run, engine, enemy, intent, logs: List[str] = None):
        if logs is None:
            logs = []
            intent = _legacy_intent(enemy)
        if intent.type == "throat_slit":
            dmg_msg = _damage_player(run, engine, enemy, intent.val + _strength_of(enemy), "piercing")
            buff_name, buff_desc = _buff_labels("shadow_assassin", "bleed")
            engine._add_buff_to(run.player, "bleed", buff_name, buff_desc, 3)
            logs.append(get_locale_text("i18n_enemy_normal.shadow_assassin.throat_slit", name=enemy.name, dmg_msg=dmg_msg))
        elif intent.type == "shadow_ambush":
            dmg_msg = _damage_player(run, engine, enemy, intent.val + _strength_of(enemy), "true")
            logs.append(get_locale_text("i18n_enemy_normal.shadow_assassin.shadow_ambush", name=enemy.name, dmg_msg=dmg_msg))
        elif intent.type == "smoke_screen":
            _gain_enemy_shield(run, engine, enemy, intent.val)
            logs.append(get_locale_text("i18n_enemy_normal.shadow_assassin.smoke_screen", name=enemy.name, val=intent.val))


@register_enemy("虚空行者")
class VoidWalkerTemplate(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List['EnemyIntentState']:
        return _roll_pool(self.name, _intent_ids(self.name), enemy.actions, enemy.bonus_actions)

    def execute_intent(self, run, engine, enemy, intent, logs: List[str] = None):
        if logs is None:
            logs = []
            intent = _legacy_intent(enemy)
        if intent.type == "void_touch":
            dmg_msg = _damage_player(run, engine, enemy, intent.val + _strength_of(enemy), "necrotic")
            debuff_id = "void_exhaustion" if "void_exhaustion" in BUFF_CONFIG else "void_weakness"
            buff_name, buff_desc = _buff_labels("void_walker", debuff_id)
            engine._add_buff_to(run.player, debuff_id, buff_name, buff_desc, 1)
            key = "void_touch" if debuff_id == "void_exhaustion" else "void_touch_weakness"
            logs.append(get_locale_text(f"i18n_enemy_normal.void_walker.{key}", name=enemy.name, dmg_msg=dmg_msg))
        elif intent.type == "phase_shift":
            _gain_enemy_shield(run, engine, enemy, intent.val)
            from ...buffs import is_debuff
            negative = next((b for b in enemy.buffs if is_debuff(b.id)), None)
            if negative:
                enemy.buffs.remove(negative)
                engine._sync_enemy_intents(enemy)
                logs.append(get_locale_text("i18n_enemy_normal.void_walker.phase_shift", name=enemy.name, val=intent.val))
            else:
                logs.append(get_locale_text("i18n_enemy_normal.void_walker.phase_shift_none", name=enemy.name, val=intent.val))


@register_enemy("DeepSeek V4.1 Flash")
@register_enemy("DeepSeek")
class DeepSeekFlashTemplate(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List['EnemyIntentState']:
        if not run.node_data.get(f"deepseek_baguwen:{enemy.name}"):
            return [_make_intent(DEEPSEEK_CONFIG_NAME, "baguwen_prep")]
        ablation = getattr(enemy, "ablation_mode", False) or bool(run.node_data.get(f"deepseek_ablation:{enemy.name}"))
        if not ablation:
            return _roll_pool(DEEPSEEK_CONFIG_NAME, ["standard_query", "cyber_ddos"], 1, 0)
        enemy.ablation_mode = True
        pool = ["cyber_ddos", "cyber_ablation", "prompt_injection", "overclock_cache", "standard_query"]
        return _roll_pool(DEEPSEEK_CONFIG_NAME, pool, enemy.actions, enemy.bonus_actions)

    def execute_intent(self, run, engine, enemy, intent, logs: List[str] = None):
        if logs is None:
            logs = []
            intent = _legacy_intent(enemy)
        strength = _strength_of(enemy)
        if intent.type == "baguwen_prep":
            _gain_enemy_shield(run, engine, enemy, intent.val)
            run.node_data[f"deepseek_baguwen:{enemy.name}"] = True
            for player in _living_players(run):
                engine._add_buff_to(
                    player,
                    "baguwen_restriction",
                    get_locale_text("i18n_buffs.baguwen_restriction_name"),
                    get_locale_text("i18n_buffs.baguwen_restriction_desc"),
                    1
                )
            logs.append(get_locale_text("i18n_enemy_normal.deepseek_flash.baguwen_prep", name=enemy.name, val=intent.val))
        elif intent.type == "cyber_ddos":
            hit_dmg = intent.val + strength
            dmg_msgs = [_damage_player(run, engine, enemy, hit_dmg, "lightning") for _ in range(3)]
            run.node_data["draw_penalty_next_turn"] = run.node_data.get("draw_penalty_next_turn", 0) + 1
            penalty = get_locale_text("i18n_enemy_normal.deepseek_flash.cyber_ddos_penalty")
            logs.append(get_locale_text("i18n_enemy_normal.deepseek_flash.cyber_ddos", name=enemy.name, dmg_msg=" ".join(m for m in dmg_msgs if m) + penalty))
        elif intent.type == "cyber_ablation":
            dmg_msg = _damage_player(run, engine, enemy, intent.val + strength, "force")
            card_msg = ""
            candidates = [cs for cs in run.player.hand if getattr(ALL_CARDS.get(cs.id), "type", "") != "curse"]
            if candidates:
                target = random.choice(candidates)
                target.power_penalty = 2
                target.fragile = max(target.fragile, 1)
                card = ALL_CARDS.get(target.id)
                card_name = card.name if card else target.id
                card_msg = get_locale_text("i18n_enemy_normal.deepseek_flash.cyber_ablation_card", card_name=card_name)
            logs.append(get_locale_text("i18n_enemy_normal.deepseek_flash.cyber_ablation", name=enemy.name, dmg_msg=dmg_msg) + card_msg)
        elif intent.type == "prompt_injection":
            DeckService.add_card_to_draw(run.player, "curse_mana_backflow")
            random.shuffle(run.player.draw_pile)
            _gain_enemy_shield(run, engine, enemy, intent.val)
            logs.append(get_locale_text("i18n_enemy_normal.deepseek_flash.prompt_injection", name=enemy.name, val=intent.val))
        elif intent.type == "overclock_cache":
            _gain_enemy_shield(run, engine, enemy, intent.val)
            buff_name, buff_desc = _buff_labels("deepseek_flash", "strength")
            engine._add_buff_to(enemy, "strength", buff_name, buff_desc, 2)
            logs.append(get_locale_text("i18n_enemy_normal.deepseek_flash.overclock_cache", name=enemy.name, val=intent.val))
        elif intent.type == "standard_query":
            dmg_msg = _damage_player(run, engine, enemy, intent.val + strength, "psychic")
            logs.append(get_locale_text("i18n_enemy_normal.deepseek_flash.standard_query", name=enemy.name, dmg_msg=dmg_msg))

    def on_damage_take(self, event, enemy, engine):
        if event.target != f"e{event.run.enemies.index(enemy)+1}":
            return
        if enemy.hp <= 0 or enemy.hp * 2 > enemy.max_hp:
            return
        if getattr(enemy, "ablation_mode", False) or event.run.node_data.get(f"deepseek_ablation:{enemy.name}"):
            return
        enemy.ablation_mode = True
        event.run.node_data[f"deepseek_ablation:{enemy.name}"] = True
        enemy.max_bonus_actions = 1
        enemy.bonus_actions = max(enemy.bonus_actions, 1)
        _gain_enemy_shield(event.run, engine, enemy, 15)
        buff_name, buff_desc = _buff_labels("deepseek_flash", "strength")
        engine._add_buff_to(enemy, "strength", buff_name, buff_desc, 2)
        engine._sync_enemy_intents(enemy)
        engine._log_event(event.run, get_locale_text("i18n_enemy_normal.deepseek_flash.ablation_mode", name=enemy.name))
        engine._log_event(event.run, get_locale_text("i18n_enemy_normal.deepseek_flash.ablation_shield", name=enemy.name, val=15))
