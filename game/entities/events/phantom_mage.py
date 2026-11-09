import random
from .base import EventOption
from ..cards import ALL_CARDS

class ReadScrollOption(EventOption, action="read_scroll", text="解读残卷"):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        if random.random() < 0.5:
            p.deck.append("spell_surge")
            res = "🍀 你成功解读了残卷！你对奥术的领悟更深了，将卡牌【奥术涌动】加入了你的卡组。"
        else:
            p.deck.append("curse_dazed")
            res = "⚡ 残卷上狂暴的奥术能量瞬间反噬了你！你感到一阵【晕眩】（1张【晕眩】卡牌已加入卡组）。"
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return res

class ResonateScrollOption(EventOption, action="resonate_scroll", text="用魔网产生共鸣"):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        if p.gold < 15:
            return "❌ 你的金币不足 15 点。"
        p.gold -= 15
        spells = [cid for cid, c in ALL_CARDS.items() if c.type == "spell" and c.rarity not in ("legendary", "mythic", "artifact") and not cid.startswith("curse_") and not getattr(c, "coop_only", False)]
        got_card = random.choice(spells) if spells else "dagger_throw"
        p.deck.append(got_card)
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return f"🪙 你消耗了 15 金币。魔网与残卷共鸣，凭空凝聚出一张卡牌【{ALL_CARDS[got_card].name}】并加入了你的卡组。"

class DispelPhantomOption(EventOption, action="dispel_phantom", text="驱散残影"):
    def _run_effect(self, run, engine) -> str:
        p = run.player
        if "wither_seed" not in p.relics:
            p.hp = min(p.max_hp, p.hp + 15)
            res = "✨ 你用魔力驱散了法师的残影。残影破碎为纯净的奥术微光，治愈了你的伤势，生命值回复了 15 点。"
        else:
            res = "✨ 你用魔力驱散了法师的残影。残影化为奥术微光散去（因为有枯萎之种，你无法获得治疗）。"
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return res
