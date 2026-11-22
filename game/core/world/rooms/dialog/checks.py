import random
from typing import Any, Dict, List, Tuple
from ....text.events import LocaleText, TextNode, locale_text
from .conditions import eval_condition
from .state import NpcMemoryStore

CHECK_KIND_KEYS = {
    "persuade": "i18n_npc_crpg_core.checks.kind_persuade",
    "insight": "i18n_npc_crpg_core.checks.kind_insight",
    "intimidate": "i18n_npc_crpg_core.checks.kind_intimidate",
    "haggle": "i18n_npc_crpg_core.checks.kind_haggle",
}


class DiceCheckEngine:
    @staticmethod
    def difficulty_tier_key(effective_dc: int) -> str:
        if effective_dc <= 4:
            return "i18n_npc_crpg_core.checks.tier_trivial"
        if effective_dc <= 8:
            return "i18n_npc_crpg_core.checks.tier_easy"
        if effective_dc <= 11:
            return "i18n_npc_crpg_core.checks.tier_medium"
        if effective_dc <= 14:
            return "i18n_npc_crpg_core.checks.tier_hard"
        return "i18n_npc_crpg_core.checks.tier_extreme"

    @staticmethod
    def compute_modifiers(check_cfg: dict, ctx: dict) -> Tuple[int, int, List[Tuple[str, int]], bool]:
        run_npc = ctx.get("run_npc") or {}
        affinity = int(run_npc.get("affinity", 0))
        att_mod = NpcMemoryStore.attitude_modifier(affinity)
        mods: List[Tuple[str, int]] = []
        if att_mod != 0:
            tier = NpcMemoryStore.attitude_tier(affinity)
            mods.append((f"i18n_npc_crpg_core.checks.mod_attitude_{tier}", att_mod))
        context_sum = 0
        for item in check_cfg.get("modifiers") or []:
            cond = item.get("cond")
            if cond and not eval_condition(cond, ctx):
                continue
            bonus = int(item.get("bonus", 0) or 0)
            if bonus == 0:
                continue
            context_sum += bonus
            reason_key = str(item.get("reason_key") or "i18n_npc_crpg_core.checks.mod_context")
            mods.append((reason_key, bonus))
        auto_cond = check_cfg.get("auto_pass_cond")
        is_auto = bool(auto_cond and eval_condition(auto_cond, ctx))
        base_dc = int(check_cfg.get("dc", 12))
        effective_dc = base_dc - (att_mod + context_sum)
        if effective_dc <= 4:
            is_auto = True
        return base_dc, effective_dc, mods, is_auto

    @staticmethod
    def build_option_tag(check_cfg: dict, ctx: dict) -> LocaleText:
        kind = str(check_cfg.get("kind", "persuade"))
        kind_key = CHECK_KIND_KEYS.get(kind, CHECK_KIND_KEYS["persuade"])
        _, effective_dc, _, is_auto = DiceCheckEngine.compute_modifiers(check_cfg, ctx)
        if is_auto:
            return locale_text("i18n_npc_crpg_core.checks.tag_auto_pass")
        tier_key = DiceCheckEngine.difficulty_tier_key(effective_dc)
        return locale_text(
            "i18n_npc_crpg_core.checks.tag_format",
            params={
                "kind": locale_text(kind_key),
                "tier": locale_text(tier_key),
            },
        )

    @staticmethod
    def resolve_check(check_cfg: dict, ctx: dict) -> Tuple[bool, List[TextNode], Dict[str, Any]]:
        kind = str(check_cfg.get("kind", "persuade"))
        kind_key = CHECK_KIND_KEYS.get(kind, CHECK_KIND_KEYS["persuade"])
        base_dc, effective_dc, mods, is_auto = DiceCheckEngine.compute_modifiers(check_cfg, ctx)
        tier_key = DiceCheckEngine.difficulty_tier_key(effective_dc)
        if is_auto:
            reason = check_cfg.get("auto_pass_reason_key") or "i18n_npc_crpg_core.checks.auto_pass_default"
            nodes: List[TextNode] = [
                locale_text(
                    "i18n_npc_crpg_core.checks.auto_pass_log",
                    params={
                        "kind": locale_text(kind_key),
                        "reason": locale_text(reason),
                    },
                )
            ]
            return True, nodes, {"auto": True, "roll": 20, "total": 20}

        roll = random.randint(1, 20)
        mod_sum = sum(val for _, val in mods)
        total = roll + mod_sum
        crit_success = roll == 20
        crit_fail = roll == 1
        if crit_success:
            passed = True
        elif crit_fail:
            passed = False
        else:
            passed = total >= base_dc

        if mods:
            from ....text.events import JoinedText

            mod_parts = [
                locale_text(
                    "i18n_npc_crpg_core.checks.mod_item_pos" if val >= 0 else "i18n_npc_crpg_core.checks.mod_item_neg",
                    params={"reason": locale_text(rkey), "val": abs(val)},
                )
                for rkey, val in mods
            ]
            mod_text: TextNode = JoinedText(parts=mod_parts, separator=" ")
        else:
            mod_text = locale_text("i18n_npc_crpg_core.checks.mod_none")

        if crit_success:
            result_key = "i18n_npc_crpg_core.checks.result_crit_success"
        elif crit_fail:
            result_key = "i18n_npc_crpg_core.checks.result_crit_fail"
        elif passed:
            result_key = "i18n_npc_crpg_core.checks.result_success"
        else:
            result_key = "i18n_npc_crpg_core.checks.result_fail"

        nodes = [
            locale_text(
                "i18n_npc_crpg_core.checks.roll_log",
                params={
                    "kind": locale_text(kind_key),
                    "tier": locale_text(tier_key),
                    "roll": roll,
                    "mods": mod_text,
                    "total": total,
                    "result": locale_text(result_key),
                },
            )
        ]
        return passed, nodes, {
            "auto": False,
            "roll": roll,
            "total": total,
            "crit_success": crit_success,
            "crit_fail": crit_fail,
        }
