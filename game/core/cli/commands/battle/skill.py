from typing import Generator
from ...base import CommandHandler

class SkillCommand(CommandHandler, names=["技能", "skill", "sk", "k"], allowed_states=["battle"]):
    def execute(self, router, user_id: str, parts: list[str]) -> Generator[str, None, None]:
        run = router.save_manager.load_save(user_id)
        if not run or run.node_type != "battle":
            yield "❌ 只有在战斗中才能使用职业技能。"
            return
        stats = router.save_manager.load_stats(user_id)
        p_class = getattr(stats, "selected_class", "法师")
        if p_class != "战士":
            yield "❌ 当前职业不是战士，无法使用【动作如潮】技能。"
            return
        skill_arg = parts[1].lower() if len(parts) >= 2 else "as"
        if skill_arg not in ("as", "action_surge", "动作如潮"):
            yield "💡 战士职业技能使用命令：/rogue 技能 as （或 /rogue sk as）"
            return
        p = run.player
        if getattr(run, "coop_id", "") and p.downed:
            yield "💀 你已倒地，无法使用职业技能。"
            return
        surge_key = f"action_surge_uses:{user_id}" if getattr(run, "coop_id", "") else "action_surge_uses"
        used_key = f"action_surge_turn_used:{user_id}" if getattr(run, "coop_id", "") else "action_surge_turn_used"
        uses = run.node_data.get(surge_key, 0)
        if uses <= 0:
            yield "❌ 动作如潮在一场战斗中只能使用两次，本场战斗的使用次数已用尽！"
            return
        if run.node_data.get(used_key, False):
            yield "❌ 动作如潮每回合只能使用一次！"
            return
        run.node_data[surge_key] = uses - 1
        run.node_data[used_key] = True
        p.actions += 2
        p.bonus_actions += 1
        router.save_manager.save_save(user_id, run)
        yield f"🔥 战士发动了【动作如潮】！获得了额外的 2A 1BA 动作点！(本场战斗还可使用 {uses - 1} 次)\n当前行动点: {p.actions}A, {p.bonus_actions}BA"
