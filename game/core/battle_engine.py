import random
from typing import Optional
from ..models.state import GameRun, PlayerState, EnemyState, Card
from ..data.map_config import MapConfig
from .battle.base import BaseBattleEngine
from .battle.combat_resolver import CombatResolver
from .battle.card_player import CardPlayer
from .battle.enemy_controller import EnemyTurnController
from .battle.observers import RelicTriggerHandler, BuffTriggerHandler, AmuletTriggerHandler, RallyTriggerHandler, MinionTriggerHandler, EnemyTriggerHandler, CardTriggerHandler
from .battle.instant_summon import InstantSummonHandler
from .daily_blessing import DailyBlessingHandler

class BattleEngine(BaseBattleEngine):
    def __init__(self, save_manager):
        super().__init__(save_manager)
        self.combat_resolver = CombatResolver(self)
        self.card_player = CardPlayer(self)
        self.enemy_controller = EnemyTurnController(self)
        self.relic_handler = RelicTriggerHandler(self.event_bus, self)
        self.buff_handler = BuffTriggerHandler(self.event_bus, self)
        self.amulet_handler = AmuletTriggerHandler(self.event_bus, self)
        self.rally_handler = RallyTriggerHandler(self.event_bus, self)
        self.minion_handler = MinionTriggerHandler(self.event_bus, self)
        self.enemy_handler = EnemyTriggerHandler(self.event_bus, self)
        self.card_handler = CardTriggerHandler(self.event_bus, self)
        self.instant_summon_handler = InstantSummonHandler(self.event_bus, self)
        self.daily_blessing_handler = DailyBlessingHandler(self.event_bus, self)

    def _log_event(self, run: Optional[GameRun], msg: str):
        if run is None:
            return
        if "battle_logs" not in run.node_data:
            run.node_data["battle_logs"] = []
        run.node_data["battle_logs"].append(msg)

    def _append_logs_to_res(self, run: GameRun, res: str) -> str:
        if "battle_logs" in run.node_data:
            logs = run.node_data.pop("battle_logs", [])
            if logs:
                res = res.rstrip() + "\n" + "\n".join(logs)
        return res

    def is_battle_won(self, run: GameRun) -> bool:
        if run.node_type != "battle":
            return False
        if not run.enemies:
            return True
        if all(e.hp <= 0 for e in run.enemies):
            return True
        alive_enemies = [e for e in run.enemies if e.hp > 0]
        if all(e.is_summon for e in alive_enemies):
            return True
        return False

    def _get_first_alive_enemy(self, run: GameRun) -> str:
        return self.combat_resolver.get_first_alive_enemy(run)

    def _get_target_name(self, run: GameRun, target: Optional[str]) -> str:
        return self.combat_resolver.get_target_name(run, target)

    def _damage_target(self, run: GameRun, target: str, dmg: int, source: str = "effect", damage_type: str = "effect", card: Optional[Card] = None):
        self.combat_resolver.damage_target(run, target, dmg, source, damage_type, card)

    def _heal_target(self, run: GameRun, target: str, heal: int):
        self.combat_resolver.heal_target(run, target, heal)

    def _summon_minion(self, run: GameRun, minion_id: str, name: str, hp: int, atk: int, ba: int) -> Optional[str]:
        return self.combat_resolver.summon_minion(run, minion_id, name, hp, atk, ba)

    def _gain_shield(self, run: GameRun, target: str, amount: int):
        self.combat_resolver.gain_shield(run, target, amount)

    def _sync_enemy_intents(self, enemy: EnemyState):
        self.enemy_controller.sync_enemy_intents(enemy)

    def _add_buff_to(self, entity, buff_id: str, buff_name: str, desc: str, count: int = 1, count2: Optional[int] = None):
        self.combat_resolver.add_buff_to(entity, buff_id, buff_name, desc, count, count2)

    def _get_free_grid(self, p: PlayerState) -> Optional[str]:
        return self.combat_resolver.get_free_grid(p)

    def _register_card_played(self, run: GameRun) -> int:
        count = run.node_data.get("cards_played_this_turn", 0) + 1
        run.node_data["cards_played_this_turn"] = count
        from ..models.events import CardPlayedCountEvent
        self.event_bus.dispatch(CardPlayedCountEvent(run, count))
        return count

    def _draw_cards(self, p: PlayerState, count: int, run: Optional[GameRun] = None, ignore_focus: bool = False):
        self.card_player.draw_cards(p, count, run, ignore_focus)

    def _init_battle_node(self, run: GameRun, difficulty: str = "normal"):
        p = run.player
        if run.node_data.get("temp_minus_1a"):
            run.node_data["drain_a"] = True
            run.node_data.pop("temp_minus_1a", None)
        p.hand.clear()
        p.draw_pile = p.deck.copy()
        import random
        random.shuffle(p.draw_pile)
        p.discard_pile.clear()
        p.exhaust_pile.clear()
        p.minion_graveyard.clear()
        p.enemy_graveyard.clear()
        p.minions.clear()
        p.amulets.clear()
        p.buffs.clear()
        p.actions = 2
        p.bonus_actions = 1
        p.shield = 0
        run.node_data["cards_played_this_turn"] = 0
        run.node_data["turn_count"] = 1
        selected_class = "法师"
        stats = self.save_manager.load_stats(run.user_id) if hasattr(self, "save_manager") and self.save_manager else None
        if stats:
            selected_class = getattr(stats, "selected_class", "法师")
        elif hasattr(p, "selected_class"):
            selected_class = getattr(p, "selected_class", "法师")
        if selected_class == "战士":
            run.node_data["action_surge_uses"] = 2
            run.node_data["action_surge_turn_used"] = False

        from ..models.events import BattleStartEvent, TurnStartEvent
        evt_start = BattleStartEvent(run)
        self.event_bus.dispatch(evt_start)

        if getattr(p, "subclass", "") == "时序法师":
            if random.random() < 0.25:
                p.bonus_actions += 1
                self._log_event(run, "⏳ [时序被动] 触发时间跳跃，初始额外获得 1 个附赠动作（BA）！")
        if getattr(p, "subclass", "") == "秘钥学者":
            self._add_buff_to(p, "key_scholar_passive", "门扉共鸣", "打出或部署护符卡牌时，玩家回复 3 点生命值并获得 4 点护盾")
        init_draw = 6
        for r in p.relics:
            from ..entities.relics import get_relic_impl
            impl = get_relic_impl(r)
            if impl:
                init_draw = impl.modify_initial_draw(run, init_draw, self)
        self._draw_cards(p, init_draw, run, ignore_focus=True)
        run.node_data["difficulty"] = difficulty

        if difficulty == "boss":
            if p.stage == 12:
                boss_name = random.choice(["远古红龙", "雷霆领主"])
                if boss_name == "远古红龙":
                    run.enemies = [EnemyState(
                        name="远古红龙",
                        hp=140,
                        max_hp=140,
                        shield=0,
                        actions=1,
                        bonus_actions=2,
                        max_actions=1,
                        max_bonus_actions=2
                    )]
                    run.node_data["boss_name"] = "远古红龙"
                else:
                    run.enemies = [EnemyState(
                        name="雷霆领主",
                        hp=130,
                        max_hp=130,
                        shield=0,
                        actions=1,
                        bonus_actions=2,
                        max_actions=1,
                        max_bonus_actions=2
                    )]
                    run.node_data["boss_name"] = "雷霆领主"
                    run.node_data["thunder_lord_turn"] = 1
            elif p.stage == MapConfig.GATE_BOSS_STAGE:
                boss_name = random.choice(["腐化之心", "Icerainboww"])
                if boss_name == "腐化之心":
                    run.enemies = [EnemyState(
                        name="腐化之心",
                        hp=200,
                        max_hp=200,
                        shield=0,
                        actions=1,
                        bonus_actions=2,
                        max_actions=1,
                        max_bonus_actions=2
                    )]
                    self._add_buff_to(run.enemies[0], "beat_of_death", "死亡律动", "玩家每使用一张牌，受到 1 点力场伤害。")
                    self._add_buff_to(run.enemies[0], "unyielding", "坚不可摧", "一回合最多可受到该状态层数点伤害，超出的部分会直接免疫，真实伤害可以穿透坚不可摧", 40)
                    run.node_data["boss_name"] = "腐化之心"
                else:
                    run.enemies = [EnemyState(
                        name="Icerainboww",
                        hp=160,
                        max_hp=160,
                        shield=0,
                        actions=2,
                        bonus_actions=0,
                        max_actions=2,
                        max_bonus_actions=0
                    )]
                    run.node_data["boss_name"] = "Icerainboww"
                    run.node_data["icerainboww_turn"] = 1
            elif p.stage == MapConfig.AVERGOMON_STAGE:
                run.enemies = [EnemyState(
                    name="亚弗戈蒙",
                    hp=180,
                    max_hp=180,
                    shield=0,
                    actions=2,
                    bonus_actions=1,
                    max_actions=2,
                    max_bonus_actions=1
                )]
                run.node_data["boss_name"] = "亚弗戈蒙"
            elif p.stage == MapConfig.FINAL_BOSS_STAGE:
                run.enemies = [EnemyState(
                    name="虚空之门·尤格-索托斯",
                    hp=200,
                    max_hp=200,
                    shield=0,
                    actions=2,
                    bonus_actions=1,
                    max_actions=2,
                    max_bonus_actions=1
                )]
                self._add_buff_to(run.enemies[0], "ancient_protection", "先古庇护", "受到伤害的 20% 反弹为真实伤害，回合开始有盾清除负面效果")
                run.node_data["boss_name"] = "虚空之门·尤格-索托斯"
                run.node_data["yog_sothoth_phase"] = 1
                run.node_data["yog_sothoth_turn"] = 1
                stats = self.save_manager.load_stats(run.user_id)
                if stats:
                    stats.yog_sothoth_challenge_count = getattr(stats, "yog_sothoth_challenge_count", 0) + 1
                    self.save_manager.save_stats(run.user_id, stats)
                    challenge_count = stats.yog_sothoth_challenge_count
                else:
                    challenge_count = 1
                if challenge_count == 1:
                    self._log_event(run, "💬 【虚空之门·尤格-索托斯】：‘渺小的灵魂，竟敢踏足终焉的视界。虚空之门将把你吞噬。’")
                else:
                    self._log_event(run, f"💬 【虚空之门·尤格-索托斯】：‘又一次……你再一次回到了这里，{run.player.name}。但无论多少次尝试，这扇门永远是你的死路！’")
            else:
                boss_name = random.choice(["远古红龙", "雷霆领主"])
                if boss_name == "远古红龙":
                    run.enemies = [EnemyState(
                        name="远古红龙",
                        hp=140,
                        max_hp=140,
                        shield=0,
                        actions=1,
                        bonus_actions=2,
                        max_actions=1,
                        max_bonus_actions=2
                    )]
                    run.node_data["boss_name"] = "远古红龙"
                else:
                    run.enemies = [EnemyState(
                        name="雷霆领主",
                        hp=130,
                        max_hp=130,
                        shield=0,
                        actions=1,
                        bonus_actions=2,
                        max_actions=1,
                        max_bonus_actions=2
                    )]
                    run.node_data["boss_name"] = "雷霆领主"
                    run.node_data["thunder_lord_turn"] = 1
        elif difficulty == "elite":
            from ..data.enemy_data import ENEMY_CONFIG
            if p.stage <= 12:
                elite_pool = ["地精百夫长", "石像鬼祭司", "狂暴兽王", "夺心魔", "冷蛛", "米·戈"]
            elif p.stage <= 25:
                elite_pool = ["黑曜石巨灵", "幽灵大魔法师", "暗影影魔", "夺心魔", "修格斯", "星之精"]
            else:
                elite_pool = ["末日守卫", "亡灵巫师", "夺心魔奥术师", "吉斯洋基至高指挥官", "虚空潜伏者", "克苏鲁之星之眷族"]
            run.enemies = []
            base_name = random.choice(elite_pool)
            run.node_data["elite_name"] = base_name
            cfg = ENEMY_CONFIG.get(base_name, {})
            import re
            hp_str = cfg.get("hp", "30")
            base_hp = 30
            match = re.match(r"^(\d+)", hp_str)
            if match:
                base_hp = int(match.group(1))
            hp_final = base_hp + p.stage * 3

            actions_str = cfg.get("actions", "1A 1BA")
            act_match = re.search(r"(\d+)A", actions_str)
            ba_match = re.search(r"(\d+)BA", actions_str)
            actions = int(act_match.group(1)) if act_match else 1
            bonus_actions = int(ba_match.group(1)) if ba_match else 1

            run.enemies.append(EnemyState(
                name=base_name,
                hp=hp_final,
                max_hp=hp_final,
                shield=0,
                actions=actions,
                bonus_actions=bonus_actions,
                max_actions=actions,
                max_bonus_actions=bonus_actions
            ))
        elif difficulty == "ghost":
            ghost_name = str(run.node_data.get("ghost_name", "冤魂"))
            ghost_hp = max(1, int(run.node_data.get("ghost_max_hp", 60) or 60))
            run.enemies = [EnemyState(
                name=ghost_name,
                hp=ghost_hp,
                max_hp=ghost_hp,
                shield=0,
                actions=1,
                bonus_actions=0,
                max_actions=1,
                max_bonus_actions=0
            )]
        else:
            from ..data.enemy_data import ENEMY_CONFIG
            if p.stage <= 12:
                normal_pool = ["地精突袭者", "石像鬼守卫", "堕落学徒", "狂暴野兽", "邪教徒咔咔", "深潜者", "食尸鬼"]
            elif p.stage <= 25:
                normal_pool = ["幽灵法师", "冰霜史莱姆", "骷髅弓箭手", "剧毒蜘蛛", "邪教徒咔咔", "夜魇", "夏塔克鸟"]
            else:
                normal_pool = ["黑曜石巨人", "暗影刺客", "吉斯洋基海盗", "虚空行者", "空鬼"]
            run.enemies = []
            num_enemies = random.randint(1, 3)
            selected_names = [random.choice(normal_pool) for _ in range(num_enemies)]
            for i, base_name in enumerate(selected_names):
                cfg = ENEMY_CONFIG.get(base_name, {})
                import re
                hp_str = cfg.get("hp", "12")
                base_hp = 12
                match = re.match(r"^(\d+)", hp_str)
                if match:
                    base_hp = int(match.group(1))
                hp_final = base_hp + p.stage * 2

                actions_str = cfg.get("actions", "1A 0BA")
                act_match = re.search(r"(\d+)A", actions_str)
                ba_match = re.search(r"(\d+)BA", actions_str)
                actions = int(act_match.group(1)) if act_match else 1
                bonus_actions = int(ba_match.group(1)) if ba_match else 0

                name = f"{base_name} {chr(65 + i)}" if num_enemies > 1 else base_name
                run.enemies.append(EnemyState(
                    name=name,
                    hp=hp_final,
                    max_hp=hp_final,
                    shield=0,
                    actions=actions,
                    bonus_actions=bonus_actions,
                    max_actions=actions,
                    max_bonus_actions=bonus_actions
                ))

        evt_turn = TurnStartEvent(run, is_player=True)
        self.event_bus.dispatch(evt_turn)
        self._roll_enemy_intent(run)

    init_battle = _init_battle_node

    def play_card(self, run: GameRun, hand_idx: int, target: Optional[str] = None) -> str:
        return self.card_player.play_card(run, hand_idx, target)

    def play_special_action(self, run: GameRun, hand_idx: int, target: Optional[str] = None) -> str:
        return self.card_player.play_special_action(run, hand_idx, target)

    def minion_attack(self, run: GameRun, my_grid: str, opp_grid: Optional[str] = None) -> str:
        return self.card_player.minion_attack(run, my_grid, opp_grid)

    def minion_skill(self, run: GameRun, my_grid: str, skill_idx: int = 1, target: Optional[str] = None) -> str:
        return self.card_player.minion_skill(run, my_grid, skill_idx, target)

    def _execute_card_effect(self, run: GameRun, card: Card, target: Optional[str] = None) -> str:
        res = card.execute(run, target, self)
        if run.node_data.get("split_to_ten_active"):
            for _ in range(10):
                if self.is_battle_won(run):
                    break
                extra_res = card.execute(run, target, self)
                from ..models.events import CardPlayedEvent
                played_evt = CardPlayedEvent(run, card, target, extra_res, is_extra=True)
                self.event_bus.dispatch(played_evt)
                run.node_data.setdefault("extra_play_msgs", []).append(f" 🔀 [一分为十触发] {played_evt.feedback}")
        return res

    def get_modified_spell_damage(self, run: GameRun, card: Card, damage: int) -> int:
        return self.combat_resolver.get_modified_spell_damage(run, card, damage)

    def _discard_card(self, run: GameRun, cid: str) -> str:
        return self.card_player.discard_card(run, cid)

    def end_turn(self, run: GameRun) -> str:
        return self.card_player.end_turn(run)

    def _enemy_turn(self, run: GameRun) -> str:
        return self.enemy_controller.enemy_turn(run)

    def _handle_battle_win(self, run: GameRun):
        self.card_player.handle_battle_win(run)

    def _roll_enemy_intent(self, run: GameRun):
        self.enemy_controller.roll_enemy_intent(run)

    def _reindex_minions(self, p: PlayerState):
        active = [p.minions[k] for k in sorted(p.minions.keys(), key=int)]
        available = [str(i) for i in range(1, 7) if str(i) not in p.amulets]
        new_minions = {}
        for idx, m in enumerate(active):
            if idx < len(available):
                new_minions[available[idx]] = m
        p.minions = new_minions

    def execute_emperor_eye_resolve(self, run: GameRun, keep_idx: int, upgraded: bool) -> str:
        p = run.player
        exhausted_count = 0
        retained_cid = None
        if 0 <= keep_idx < len(p.hand):
            retained_cid = p.hand[keep_idx]
        cards_to_exhaust = []
        for i, cid in enumerate(p.hand):
            if i != keep_idx:
                cards_to_exhaust.append(cid)
        p.hand.clear()
        if retained_cid:
            p.hand.append(retained_cid)
        from ..models.events import CardExhaustEvent
        from ..entities.cards.base import ALL_CARDS
        for cid in cards_to_exhaust:
            p.exhaust_pile.append(cid)
            card_obj = ALL_CARDS.get(cid)
            cname = card_obj.name if card_obj else cid
            self._log_event(run, f"✨ [消耗] 【{cname}】已被移入消耗堆。")
            self.event_bus.dispatch(CardExhaustEvent(run, cid, "emperor_eye"))
            exhausted_count += 1
        card_pool = []
        for cid, card_obj in ALL_CARDS.items():
            if not cid.startswith("duel_") and not cid.startswith("curse_") and not cid.endswith("+"):
                if not getattr(card_obj, "unplayable", False):
                    card_pool.append(cid)
        drawn = []
        if card_pool and exhausted_count > 0:
            import random
            max_hand = 9 if "mask_of_void" in p.relics else 12
            for _ in range(exhausted_count):
                if len(p.hand) < max_hand:
                    new_cid = random.choice(card_pool)
                    p.hand.append(new_cid)
                    card_obj = ALL_CARDS.get(new_cid)
                    drawn.append(card_obj.name if card_obj else new_cid)
        dmg_msg = ""
        if upgraded:
            alive_enemies = [e for e in run.enemies if e.hp > 0]
            if alive_enemies:
                import random
                target_enemy = random.choice(alive_enemies)
                target_idx = run.enemies.index(target_enemy) + 1
                self.combat_resolver.damage_target(run, f"e{target_idx}", 49, source="p0", damage_type="force")
                dmg_msg = f"\n💥 【霸瞳天星+】对随机敌人【{target_enemy.name}】造成了 49 点力场伤害！"
        self.resolve_suspended_card(run)

        retained_name = ALL_CARDS[retained_cid].name if retained_cid else "无"
        drawn_str = "，".join(drawn) if drawn else "无"
        res_str = f"👁️ 【霸瞳天星】发动成功！保留了手牌中的【{retained_name}】，消耗了其他 {exhausted_count} 张卡牌。并随机获得了同等数量的卡牌：【{drawn_str}】。{dmg_msg}"
        self.save_manager.save_save(run.user_id, run)
        return self._append_logs_to_res(run, res_str)

    def resolve_suspended_card(self, run: GameRun):
        suspended_state = run.node_data.pop("suspended_card_cid", None)
        if not suspended_state:
            suspended_state = run.node_data.pop("emperor_eye_cid", None)
        if not suspended_state:
            return
        run.node_data.pop("suspended_card_cost_a", None)
        run.node_data.pop("suspended_card_cost_ba", None)
        run.node_data.pop("suspended_card_hand_idx", None)
        p = run.player
        from ..models.state import ensure_card_state
        suspended_state = ensure_card_state(suspended_state)
        from ..entities.cards.base import ALL_CARDS
        card = ALL_CARDS.get(suspended_state)
        if not card:
            return
        
        return_left = suspended_state.return_left
        if return_left <= 0:
            if hasattr(card, "gems") and card.gems:
                if "gem_return_5" in card.gems:
                    return_left = 5
                elif "gem_return_3" in card.gems:
                    return_left = 3

        should_return = False
        import copy
        new_cid = copy.copy(suspended_state)
        if return_left > 0:
            next_left = return_left - 1
            if next_left > 0:
                should_return = True
                new_cid.return_left = next_left

        extra_return_msg = ""
        if should_return:
            p.hand.append(new_cid)
            extra_return_msg = f"\n✨ [返回] 【{card.name}】打出后回到了你的手牌！（剩余次数 {next_left}）"
        else:
            self.card_player._handle_card_post_play(run, card, suspended_state, source="played")

        if hasattr(card, "gems") and card.gems:
            has_shield_gem = any(g in card.gems for g in ("gem_shield_add_3", "gem_shield_add_8"))
            if has_shield_gem and not run.node_data.get("card_played_triggered_shield", False):
                self.combat_resolver.gain_shield(run, "p0", 0)
            has_heal_gem = "gem_heal_add_2" in card.gems
            if has_heal_gem and not run.node_data.get("card_played_triggered_heal", False):
                self.combat_resolver.heal_target(run, "p0", 0)
            has_dmg_gem = "gem_dmg_add_2" in card.gems
            if has_dmg_gem and not run.node_data.get("card_played_triggered_dmg", False):
                dmg_target = self._get_first_alive_enemy(run)
                if dmg_target and dmg_target != "0" and dmg_target != "e0":
                    self.combat_resolver.damage_target(run, dmg_target, 0, source="p0", damage_type="effect")

            for g in card.gems:
                if g == "gem_gain_a_1":
                    p.actions += 1
                    self._log_event(run, "💎 [劫掠青金石] 触发，获得 1A！")
                elif g == "gem_gain_a_1_ba_1":
                    p.actions += 1
                    p.bonus_actions += 1
                    self._log_event(run, "💎 [神圣白钻] 触发，获得 1A 1BA！")
                elif g == "gem_vuln_1":
                    dmg_target = self._get_first_alive_enemy(run)
                    if dmg_target and dmg_target.startswith("e"):
                        try:
                            idx = int(dmg_target[1:]) - 1
                            if idx < 0: idx = 0
                        except ValueError:
                            idx = 0
                        if idx < len(run.enemies):
                            self.combat_resolver.add_buff_to(run.enemies[idx], "vulnerable", "易伤", "受到的伤害增加50%", 1)
                            self._log_event(run, f"💎 [易伤尖晶石] 触发，对【{run.enemies[idx].name}】施加 1 层易伤！")
                elif g == "gem_weak_2":
                    dmg_target = self._get_first_alive_enemy(run)
                    if dmg_target and dmg_target.startswith("e"):
                        try:
                            idx = int(dmg_target[1:]) - 1
                            if idx < 0: idx = 0
                        except ValueError:
                            idx = 0
                        if idx < len(run.enemies):
                            self.combat_resolver.add_buff_to(run.enemies[idx], "weak", "虚弱", "造成的伤害减少50%", 2)
                            self._log_event(run, f"💎 [虚弱玛瑙] 触发，对【{run.enemies[idx].name}】施加 2 层虚弱！")

        extra_copy_msg = ""
        copy_count = 0
        if not suspended_state.no_copy:
            if hasattr(card, "copy") and card.copy > 0:
                copy_count = card.copy
            if hasattr(card, "gems") and card.gems and "gem_copy_1" in card.gems:
                copy_count = max(copy_count, 1)
        if copy_count > 0:
            import copy
            copy_cid = copy.copy(suspended_state)
            copy_cid.gems = [g for g in copy_cid.gems if g != "gem_copy_1"]
            copy_cid.no_copy = True
            max_hand = 9 if "mask_of_void" in p.relics else 12
            added = 0
            for _ in range(copy_count):
                if len(p.hand) < max_hand:
                    p.hand.append(copy_cid)
                    added += 1
            if added > 0:
                extra_copy_msg = f"\n✨ [复制] 【{card.name}】打出后往手牌中添加了 {added} 张复制品！"

        if hasattr(card, "execute_tags"):
            card.execute_tags(run, None, self)

        from ..models.events import CardPlayedEvent
        played_evt = CardPlayedEvent(run, card, None, "")
        self.event_bus.dispatch(played_evt)

        if extra_return_msg:
            self._log_event(run, extra_return_msg.strip())
        if extra_copy_msg:
            self._log_event(run, extra_copy_msg.strip())
        
        self._register_card_played(run)

    def rollback_suspended_card(self, run: GameRun):
        suspended_state = run.node_data.pop("suspended_card_cid", None)
        if not suspended_state:
            suspended_state = run.node_data.pop("emperor_eye_cid", None)
        if not suspended_state:
            return
        from ..models.state import ensure_card_state
        suspended_state = ensure_card_state(suspended_state)
        cost_a = run.node_data.pop("suspended_card_cost_a", 0)
        cost_ba = run.node_data.pop("suspended_card_cost_ba", 0)
        hand_idx = run.node_data.pop("suspended_card_hand_idx", None)
        p = run.player
        p.actions += cost_a
        p.bonus_actions += cost_ba
        if hand_idx is not None and 0 <= hand_idx <= len(p.hand):
            p.hand.insert(hand_idx, suspended_state)
        else:
            p.hand.append(suspended_state)
