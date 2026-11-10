from typing import List
from ..base import EnemyTemplate, register_enemy
from ....data.enemy_data import ENEMY_CONFIG
from ....data.locale_data import get_locale_text

@register_enemy("狂暴兽王")
class BeastMasterTemplate(EnemyTemplate):
    def _hound_name(self, cfg) -> str:
        return cfg.get("summon_hound", {}).get("name", get_locale_text("i18n_enemy_elite_a.beast_master.hound_name"))

    def _living_hounds(self, run, hound_name: str) -> List:
        return [e for e in run.enemies if e.hp > 0 and hound_name and e.name.startswith(hound_name)]

    def roll_intents(self, run, engine, enemy) -> List['EnemyIntentState']:
        from ....models.state import EnemyIntentState
        import random
        cfg = ENEMY_CONFIG.get("狂暴兽王", {})
        intents = cfg.get("intents", [])
        hound_name = self._hound_name(cfg)
        a_ids = ["attack"]
        if len(self._living_hounds(run, hound_name)) < 2:
            a_ids.append("summon_beast")
        a_pool = [it for it in intents if it.get("id") in a_ids] or intents
        ba_pool = [it for it in intents if it.get("id") in ("pack_howl", "defend")] or intents
        intents_list = []
        for _ in range(enemy.actions):
            chosen = random.choice(a_pool)
            intents_list.append(EnemyIntentState(type=chosen["id"], val=chosen["val"], desc=chosen["desc"], cost_a=1, cost_ba=0))
        for _ in range(enemy.bonus_actions):
            chosen = random.choice(ba_pool)
            intents_list.append(EnemyIntentState(type=chosen["id"], val=chosen["val"], desc=chosen["desc"], cost_a=0, cost_ba=1))
        return intents_list

    def execute_intent(self, run, engine, enemy, intent, logs: List[str] = None):
        if logs is None:
            logs = intent
            from ....models.state import EnemyIntentState
            intent = EnemyIntentState(
                type=getattr(enemy, "intent_type", ""),
                val=getattr(enemy, "intent_val", 0),
                desc=getattr(enemy, "intent_desc", ""),
                cost_a=1,
                cost_ba=0
            )
        cfg = ENEMY_CONFIG.get("狂暴兽王", {})
        hound_name = self._hound_name(cfg)
        strength = 0
        for b in enemy.buffs:
            if b.id == "strength":
                strength += b.stacks
        if intent.type == "attack":
            living_hounds = self._living_hounds(run, hound_name)
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", intent.val + strength, source=f"enemy:{enemy.name}", damage_type="slashing")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            extra_dmg = cfg.get("hound_bonus", 3) * len(living_hounds)
            if extra_dmg > 0:
                before_extra = len(run.node_data.get("battle_logs", []))
                engine._damage_target(run, "p0", extra_dmg, source=f"enemy:{enemy.name}", damage_type="piercing")
                after_extra = run.node_data.get("battle_logs", [])
                if len(after_extra) > before_extra:
                    dmg_msg = f"{dmg_msg}{after_extra.pop()}"
            hound_suffix = get_locale_text("i18n_enemy_elite_a.beast_master.hound_suffix") if living_hounds else ""
            logs.append(get_locale_text("i18n_enemy_elite_a.beast_master.attack", name=enemy.name, dmg_msg=dmg_msg, hound_suffix=hound_suffix))
        elif intent.type == "summon_beast":
            from ....models.state import EnemyState, EnemyIntentState
            sh = cfg.get("summon_hound", {})
            bite_val = sh.get("val", 3)
            new_hound = EnemyState(
                name=sh.get("name", get_locale_text("i18n_enemy_elite_a.beast_master.hound_name")),
                hp=sh.get("hp", 10),
                max_hp=sh.get("max_hp", 10),
                shield=0,
                actions=1,
                bonus_actions=0,
                is_summon=True,
                max_actions=1,
                max_bonus_actions=0,
                intents=[EnemyIntentState(
                    type="hound_bite",
                    val=bite_val,
                    desc=get_locale_text("i18n_enemy_misc.frenzied_hound.intent_hound_bite", val=bite_val),
                    cost_a=1,
                    cost_ba=0
                )]
            )
            run.enemies.append(new_hound)
            logs.append(get_locale_text("i18n_enemy_elite_a.beast_master.summon_beast", name=enemy.name))
        elif intent.type == "pack_howl":
            living_hounds = self._living_hounds(run, hound_name)
            if living_hounds:
                for idx, hound in enumerate(run.enemies):
                    if hound.hp > 0 and hound_name and hound.name.startswith(hound_name):
                        engine._add_buff_to(hound, "strength", get_locale_text("i18n_enemy_elite_a.common.strength_name"), get_locale_text("i18n_enemy_elite_a.common.strength_desc"), intent.val)
                        engine._gain_shield(run, f"e{idx+1}", cfg.get("pack_howl_shield", 4))
                logs.append(get_locale_text("i18n_enemy_elite_a.beast_master.pack_howl", name=enemy.name))
            else:
                self_idx = next((i for i, e in enumerate(run.enemies) if e is enemy), -1)
                engine._add_buff_to(enemy, "strength", get_locale_text("i18n_enemy_elite_a.common.strength_name"), get_locale_text("i18n_enemy_elite_a.common.strength_desc"), cfg.get("pack_howl_alone_strength", 1))
                if self_idx >= 0:
                    engine._gain_shield(run, f"e{self_idx+1}", cfg.get("pack_howl_alone_shield", 5))
                logs.append(get_locale_text("i18n_enemy_elite_a.beast_master.pack_howl_alone", name=enemy.name))
        elif intent.type == "defend":
            self_idx = next((i for i, e in enumerate(run.enemies) if e is enemy), -1)
            if self_idx >= 0:
                engine._gain_shield(run, f"e{self_idx+1}", intent.val)
            logs.append(get_locale_text("i18n_enemy_elite_a.beast_master.defend", name=enemy.name, val=intent.val))
