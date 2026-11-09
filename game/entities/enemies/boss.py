from typing import Tuple, List
from .base import EnemyTemplate, register_enemy
from ...data.enemy_data import ENEMY_CONFIG

@register_enemy("远古红龙")
class BossRedDragonTemplate(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List['EnemyIntentState']:
        from ...models.state import EnemyIntentState
        import random
        cfg = ENEMY_CONFIG.get("远古红龙", {})
        intents = cfg.get("intents", [])
        intents_list = []
        for _ in range(enemy.max_actions):
            chosen = random.choice(intents)
            intents_list.append(EnemyIntentState(
                type=chosen["id"],
                val=chosen["val"],
                desc=chosen["desc"],
                cost_a=1,
                cost_ba=0
            ))
        for _ in range(enemy.max_bonus_actions):
            chosen = random.choice(intents)
            intents_list.append(EnemyIntentState(
                type=chosen["id"],
                val=chosen["val"],
                desc=chosen["desc"],
                cost_a=0,
                cost_ba=1
            ))
        return intents_list

    def execute_intent(self, run, engine, enemy, intent, logs: List[str] = None):
        if logs is None:
            logs = intent
            from ...models.state import EnemyIntentState
            intent = EnemyIntentState(
                type=getattr(enemy, "intent_type", ""),
                val=getattr(enemy, "intent_val", 0),
                desc=getattr(enemy, "intent_desc", ""),
                cost_a=1,
                cost_ba=0
            )
        p = run.player
        import random
        if intent.type == "attack":
            strength = 0
            if getattr(enemy, "buffs", None):
                for b in enemy.buffs:
                    if b.id == "strength":
                        strength += b.stacks
            dmg = intent.val + strength
            self._perform_attack(run, engine, enemy, dmg, logs)
        elif intent.type == "defend":
            enemy.shield += intent.val
            logs.append(f"敌方领主【{enemy.name}】进行防守，获得 {intent.val} 点护盾。")
        elif intent.type == "summon":
            from ...models.state import EnemyState, EnemyIntentState
            cfg = ENEMY_CONFIG.get("远古红龙", {})
            sg = cfg.get("summon_goblin", {})
            new_goblin = EnemyState(
                name=sg.get("name", "魔仆"),
                hp=sg.get("hp", 5),
                max_hp=sg.get("max_hp", 5),
                shield=0,
                actions=1,
                bonus_actions=0,
                is_summon=True,
                max_actions=1,
                max_bonus_actions=0,
                intents=[EnemyIntentState(
                    type="attack",
                    val=sg.get("intent_val", 1),
                    desc=sg.get("intent_desc", "准备攻击 (造成 1 伤害)"),
                    cost_a=1,
                    cost_ba=0
                )]
            )
            run.enemies.append(new_goblin)
            logs.append(f"敌方领主【{enemy.name}】召唤了一个【魔仆】。")
        elif intent.type == "attack_all":
            strength = 0
            if getattr(enemy, "buffs", None):
                for b in enemy.buffs:
                    if b.id == "strength":
                        strength += b.stacks
            dmg = intent.val + strength
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", dmg, source=f"enemy:{enemy.name}", damage_type="bludgeoning")
            after_logs = run.node_data.get("battle_logs", [])
            if len(after_logs) > before_len:
                dmg_msg = after_logs.pop()
                logs.append(f"敌方领主【{enemy.name}】扫尾攻击玩家。{dmg_msg}")
            for mk in list(p.minions.keys()):
                if mk not in p.minions:
                    continue
                m_name = p.minions[mk].name
                before_len = len(run.node_data.get("battle_logs", []))
                engine._damage_target(run, f"p{mk}", dmg, source=f"enemy:{enemy.name}", damage_type="bludgeoning")
                after_logs = run.node_data.get("battle_logs", [])
                if len(after_logs) > before_len:
                    dmg_msg = after_logs.pop()
                    logs.append(f"我方随从【{m_name}】受到扫尾波及。{dmg_msg}")
        return "\n".join(logs)

@register_enemy("腐化之心")
class BossCorruptedHeartTemplate(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List['EnemyIntentState']:
        from ...models.state import EnemyIntentState
        turn = run.node_data.get("heart_turn", 1)
        cycle = (turn - 1) % 4 + 1
        intents_list = []
        
        if cycle == 1:
            itype, val, desc = "debuff", 0, "邪恶之语 (将晕眩与苦恼放入玩家牌组)"
        elif cycle == 2:
            itype, val, desc = "multi_attack", 2, "血弹喷射 (造成 2 点伤害，重复 8 次)"
        elif cycle == 3:
            itype, val, desc = "big_attack", 20, "毁灭之痛 (造成 20 点伤害)"
        else:
            itype, val, desc = "strength_buff", 2, "充能 (获得 2 层力量，使后续伤害增加 2)"
        intents_list.append(EnemyIntentState(type=itype, val=val, desc=desc, cost_a=1, cost_ba=0))
        
        if cycle == 1:
            itype, val, desc = "defend_large", 15, "暗影护盾 (获得 15 护盾)"
        elif cycle == 2:
            itype, val, desc = "defend_normal", 10, "护盾 (获得 10 护盾)"
        elif cycle == 3:
            itype, val, desc = "defend_normal", 10, "护盾 (获得 10 护盾)"
        else:
            itype, val, desc = "defend_large", 20, "暗影护盾 (获得 20 护盾)"
        intents_list.append(EnemyIntentState(type=itype, val=val, desc=desc, cost_a=0, cost_ba=1))
        
        if cycle == 1:
            itype, val, desc = "drain_ba", 1, "虚空之歌 (使玩家下回合失去 1BA)"
        elif cycle == 2:
            itype, val, desc = "heart_strike", 4, "心跳重击 (造成 4 伤害)"
        elif cycle == 3:
            itype, val, desc = "gaze_discard", 1, "虚无凝视 (迫使玩家随机丢弃 1 张手牌)"
        else:
            itype, val, desc = "heart_heal", 10, "回潮 (恢复 10 生命)"
        intents_list.append(EnemyIntentState(type=itype, val=val, desc=desc, cost_a=0, cost_ba=1))
        
        return intents_list

    def execute_intent(self, run, engine, enemy, intent, logs: List[str] = None):
        if logs is None:
            logs = intent
            from ...models.state import EnemyIntentState
            intent = EnemyIntentState(
                type=getattr(enemy, "intent_type", ""),
                val=getattr(enemy, "intent_val", 0),
                desc=getattr(enemy, "intent_desc", ""),
                cost_a=1,
                cost_ba=0
            )
            from ...models.state import EnemyIntentState
            intent = EnemyIntentState(
                type=getattr(enemy, "intent_type", ""),
                val=getattr(enemy, "intent_val", 0),
                desc=getattr(enemy, "intent_desc", ""),
                cost_a=1,
                cost_ba=0
            )
        p = run.player
        import random
        
        strength = 0
        for b in enemy.buffs:
            if b.id == "strength":
                strength += b.stacks

        if intent.type == "debuff":
            p.draw_pile.append("curse_dazed")
            p.draw_pile.append("curse_agony")
            random.shuffle(p.draw_pile)
            logs.append(f"【{enemy.name}】施放了【邪恶之语】，将【晕眩】与【苦恼】放入了玩家的抽牌堆并进行了洗牌。")
            
        elif intent.type == "multi_attack":
            dmg = intent.val + strength
            logs.append(f"【{enemy.name}】释放【血弹喷射】，发动 8 次攻击（每次 {dmg} 伤害）：")
            for _ in range(8):
                if enemy.hp <= 0:
                    break
                self._perform_attack(run, engine, enemy, dmg, logs)
                
        elif intent.type == "big_attack":
            dmg = intent.val + strength
            self._perform_attack(run, engine, enemy, dmg, logs)
            
        elif intent.type == "strength_buff":
            engine._add_buff_to(enemy, "strength", "力量", f"造成的伤害增加 {intent.val} 点", intent.val)
            logs.append(f"【{enemy.name}】进行【充能】，力量提升了 {intent.val} 点。")
            
        elif intent.type in ("defend_large", "defend_normal"):
            enemy.shield += intent.val
            logs.append(f"【{enemy.name}】获得 {intent.val} 点护盾。")
            
        elif intent.type == "drain_ba":
            engine._add_buff_to(run.player, "drain_ba", "虚空纠缠", "在下一回合开始时，你将失去等同于此状态层数的附赠动作点 (BA)", 1)
            logs.append(f"【{enemy.name}】吟唱【虚空之歌】，使玩家在下一回合失去 1 个附赠动作点 (BA)。")
            
        elif intent.type == "heart_strike":
            dmg = intent.val + strength
            self._perform_attack(run, engine, enemy, dmg, logs)
            
        elif intent.type == "gaze_discard":
            engine._add_buff_to(run.player, "discard_next_turn", "下回合弃牌", "在下一回合开始时，你将随机丢弃等同于此状态层数的手牌", 1)
            logs.append(f"【{enemy.name}】虚无凝视，使玩家在下一回合开始时将被迫随机丢弃 1 张手牌。")
                
        elif intent.type == "heart_heal":
            enemy.hp = min(enemy.max_hp, enemy.hp + intent.val)
            logs.append(f"【{enemy.name}】自我回潮，恢复了 {intent.val} 点生命值。")
        return "\n".join(logs)

@register_enemy("Icerainboww")
class BossIcerainbowwTemplate(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List['EnemyIntentState']:
        from ...models.state import EnemyIntentState
        turn = run.node_data.get("icerainboww_turn", 1)
        cycle = (turn - 1) % 4 + 1
        intents_list = []
        
        if cycle == 1:
            itype, val, desc = "icerain_shoot", 2, "冰雨弓射击 (造成 2 寒冷伤害，使玩家下回合失去 1A)"
        elif cycle == 2:
            itype, val, desc = "winter_gaze", 4, "寒冬凝视 (造成 4 心灵伤害，并使玩家受到轻度寒冷易伤)"
        elif cycle == 3:
            itype, val, desc = "smash_attack", 10, "粉碎攻击 (造成 10 寒冷伤害，并使玩家受到轻度寒冷易伤)"
        else:
            itype, val, desc = "frost_blast", 6, "冰霜爆震 (对玩家与所有我方随从造成 6 寒冷伤害)"
        intents_list.append(EnemyIntentState(type=itype, val=val, desc=desc, cost_a=1, cost_ba=0))
        
        if cycle == 1:
            itype, val, desc = "fury", 1, "愤怒 (获得 1 层愤怒buff，被打出珍奇或传奇卡牌激怒时自身增伤)"
        elif cycle == 2:
            itype, val, desc = "aurora_shield", 12, "极光屏障 (获得 12 护盾并净化 1 负面 Buff，无负面时额外获得 4 护盾)"
        elif cycle == 3:
            itype, val, desc = "icerain_shoot", 2, "冰雨弓射击 (造成 2 寒冷伤害，使玩家下回合失去 1A)"
        else:
            itype, val, desc = "fury", 1, "愤怒 (获得 1 层愤怒buff，被打出珍奇或传奇卡牌激怒时自身增伤)"
        intents_list.append(EnemyIntentState(type=itype, val=val, desc=desc, cost_a=1, cost_ba=0))
        
        return intents_list

    def execute_intent(self, run, engine, enemy, intent, logs: List[str] = None):
        if logs is None:
            logs = intent
            from ...models.state import EnemyIntentState
            intent = EnemyIntentState(
                type=getattr(enemy, "intent_type", ""),
                val=getattr(enemy, "intent_val", 0),
                desc=getattr(enemy, "intent_desc", ""),
                cost_a=1,
                cost_ba=0
            )
            from ...models.state import EnemyIntentState
            intent = EnemyIntentState(
                type=getattr(enemy, "intent_type", ""),
                val=getattr(enemy, "intent_val", 0),
                desc=getattr(enemy, "intent_desc", ""),
                cost_a=1,
                cost_ba=0
            )
        p = run.player
        import random
        
        strength = 0
        for b in enemy.buffs:
            if b.id == "strength":
                strength += b.stacks
 
        val = intent.val + strength
 
        if intent.type == "icerain_shoot":
            if p.minions and random.random() < 0.5:
                target_key = random.choice(list(p.minions.keys()))
                target = p.minions[target_key]
                m_name = target.name
                before_len = len(run.node_data.get("battle_logs", []))
                engine._damage_target(run, f"p{target_key}", val, source=f"enemy:{enemy.name}", damage_type="cold")
                after_logs = run.node_data.get("battle_logs", [])
                if len(after_logs) > before_len:
                    dmg_msg = after_logs.pop()
                    logs.append(f"【{enemy.name}】用冰雨弓攻击了我方随从【{m_name}】。{dmg_msg}")
            else:
                before_len = len(run.node_data.get("battle_logs", []))
                engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="cold")
                after_logs = run.node_data.get("battle_logs", [])
                if len(after_logs) > before_len:
                    dmg_msg = after_logs.pop()
                    logs.append(f"【{enemy.name}】用冰雨弓攻击玩家。{dmg_msg}")
            engine._add_buff_to(run.player, "drain_a", "时间纠缠", "在下一回合开始时，你将失去等同于此状态层数的动作点 (A)", 1)
            logs.append(f"【{enemy.name}】射出冰雨弓，使玩家在下一回合失去 1 个动作点 (A)。")
 
        elif intent.type == "fury":
            engine._add_buff_to(enemy, "fury", "愤怒", "玩家使用珍奇或传奇卡牌时，该怪物获得等同于愤怒层数的力量", 1)
            logs.append(f"【{enemy.name}】获得了 1 层【愤怒】Buff！")
 
        elif intent.type == "smash_attack":
            if p.minions and random.random() < 0.5:
                target_key = random.choice(list(p.minions.keys()))
                target = p.minions[target_key]
                m_name = target.name
                before_len = len(run.node_data.get("battle_logs", []))
                engine._damage_target(run, f"p{target_key}", val, source=f"enemy:{enemy.name}", damage_type="cold")
                after_logs = run.node_data.get("battle_logs", [])
                if len(after_logs) > before_len:
                    dmg_msg = after_logs.pop()
                    logs.append(f"【{enemy.name}】对随从【{m_name}】施展粉碎攻击。{dmg_msg}")
            else:
                before_len = len(run.node_data.get("battle_logs", []))
                engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="cold")
                after_logs = run.node_data.get("battle_logs", [])
                if len(after_logs) > before_len:
                    dmg_msg = after_logs.pop()
                    logs.append(f"【{enemy.name}】对玩家施展粉碎攻击。{dmg_msg}")
            engine._add_buff_to(p, "minor_vulnerable_cold", "轻度寒冷易伤", "受到的寒冷伤害增加 50%", 2)
            logs.append(f"【{enemy.name}】的粉碎攻击使玩家获得了 2 层【轻度寒冷易伤】状态。")
 
        elif intent.type == "aurora_shield":
            neg_buff = next((b for b in enemy.buffs if b.id == "stun"), None)
            shield_gain = intent.val
            if neg_buff:
                neg_name = neg_buff.name
                neg_buff.stacks -= 1
                if neg_buff.stacks <= 0:
                    enemy.buffs.remove(neg_buff)
                engine._sync_enemy_intents(enemy)
                logs.append(f"【{enemy.name}】施展【极光屏障】，获得 {shield_gain} 点护盾，并解除了自身的负面状态【{neg_name}】！")
            else:
                shield_gain += 4
                logs.append(f"【{enemy.name}】施展【极光屏障】，由于没有负面状态，额外获得了 4 点护盾，总计获得 {shield_gain} 点护盾。")
            enemy.shield += shield_gain
 
        elif intent.type == "winter_gaze":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="psychic")
            after_logs = run.node_data.get("battle_logs", [])
            if len(after_logs) > before_len:
                dmg_msg = after_logs.pop()
                logs.append(f"【{enemy.name}】投射【寒冬凝视】。{dmg_msg}")
            engine._add_buff_to(p, "minor_vulnerable_cold", "轻度寒冷易伤", "受到的寒冷伤害增加 50%", 1)
            logs.append(f"【{enemy.name}】的寒冬凝视使玩家获得了 1 层【轻度寒冷易伤】状态。")
 
        elif intent.type == "frost_blast":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="cold")
            after_logs = run.node_data.get("battle_logs", [])
            if len(after_logs) > before_len:
                dmg_msg = after_logs.pop()
                logs.append(f"【{enemy.name}】释放【冰霜爆震】对玩家造成伤害。{dmg_msg}")
            for mk in list(p.minions.keys()):
                if mk not in p.minions:
                    continue
                m_name = p.minions[mk].name
                before_len = len(run.node_data.get("battle_logs", []))
                engine._damage_target(run, f"p{mk}", val, source=f"enemy:{enemy.name}", damage_type="cold")
                after_logs = run.node_data.get("battle_logs", [])
                if len(after_logs) > before_len:
                    dmg_msg = after_logs.pop()
                    logs.append(f"我方随从【{m_name}】受到冰霜爆震波及。{dmg_msg}")
        return "\n".join(logs)

@register_enemy("雷霆领主")
class BossThunderLordTemplate(EnemyTemplate):
    def roll_intents(self, run, engine, enemy) -> List['EnemyIntentState']:
        from ...models.state import EnemyIntentState
        if run.node_data.get("thunder_lord_overloaded"):
            enemy.actions = max(0, enemy.actions - 1)
            run.node_data["thunder_lord_overloaded"] = False
        turn = run.node_data.get("thunder_lord_turn", 1)
        cycle = (turn - 1) % 4 + 1
        intents_list = []
        if cycle == 1:
            itype, val, desc = "thunder_strike", 8, "雷鸣重击 (造成 8 雷鸣伤害，并对玩家施加 2 层电击)"
        elif cycle == 2:
            itype, val, desc = "lightning_shield", 12, "闪电护壳 (获得 12 护盾并获得闪电护体)"
        elif cycle == 3:
            itype, val, desc = "storm_summon", 0, "呼唤雷云 (召唤一只雷影魔仆)"
        else:
            itype, val, desc = "electric_overload", 6, "电能超载 (获得 2 层力量，造成 6 闪电伤害，下回合失去 1A)"
        intents_list.append(EnemyIntentState(type=itype, val=val, desc=desc, cost_a=1, cost_ba=0))

        if cycle == 1:
            itype, val, desc = "lightning_shield", 10, "闪电护壳 (获得 10 护盾并获得闪电护体)"
        elif cycle == 2:
            itype, val, desc = "thunder_strike", 6, "雷鸣重击 (造成 6 雷鸣伤害，并对玩家施加 2 层电击)"
        elif cycle == 3:
            itype, val, desc = "defend", 8, "聚能防护 (获得 8 护盾)"
        else:
            itype, val, desc = "thunder_strike", 8, "雷鸣重击 (造成 8 雷鸣伤害，并对玩家施加 2 层电击)"
        intents_list.append(EnemyIntentState(type=itype, val=val, desc=desc, cost_a=0, cost_ba=1))

        if cycle == 1:
            itype, val, desc = "defend", 6, "聚能防护 (获得 6 护盾)"
        elif cycle == 2:
            itype, val, desc = "defend", 6, "聚能防护 (获得 6 护盾)"
        elif cycle == 3:
            itype, val, desc = "thunder_strike", 6, "雷鸣重击 (造成 6 雷鸣伤害，并对玩家施加 2 层电击)"
        else:
            itype, val, desc = "defend", 10, "聚能防护 (获得 10 护盾)"
        intents_list.append(EnemyIntentState(type=itype, val=val, desc=desc, cost_a=0, cost_ba=1))
        return intents_list

    def execute_intent(self, run, engine, enemy, intent, logs: List[str] = None):
        if logs is None:
            logs = intent
            from ...models.state import EnemyIntentState
            intent = EnemyIntentState(
                type=getattr(enemy, "intent_type", ""),
                val=getattr(enemy, "intent_val", 0),
                desc=getattr(enemy, "intent_desc", ""),
                cost_a=1,
                cost_ba=0
            )
        strength = 0
        for b in enemy.buffs:
            if b.id == "strength":
                strength += b.stacks
        val = intent.val + strength

        if intent.type == "thunder_strike":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="thunder")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            engine._add_buff_to(run.player, "shock", "电击", "受到的闪电和雷鸣伤害每层增加 1 点", 2)
            logs.append(f"【{enemy.name}】施展雷鸣重击。{dmg_msg}")
        elif intent.type == "lightning_shield":
            enemy.shield += intent.val
            engine._add_buff_to(enemy, "lightning_shield", "闪电护体", "受到伤害时反弹 2 点闪电伤害并施加 1 层电击", 1)
            logs.append(f"【{enemy.name}】施展闪电护壳，获得 {intent.val} 点护盾并获得闪电护体。")
        elif intent.type == "storm_summon":
            from ...models.state import EnemyState, EnemyIntentState
            new_minion = EnemyState(
                name="雷影魔仆",
                hp=12,
                max_hp=12,
                shield=0,
                actions=1,
                bonus_actions=0,
                is_summon=True,
                max_actions=1,
                max_bonus_actions=0,
                intents=[EnemyIntentState(
                    type="lightning_strike",
                    val=4,
                    desc="闪电击 (造成 4 闪电伤害，并施加 1 层电击)",
                    cost_a=1,
                    cost_ba=0
                )]
            )
            run.enemies.append(new_minion)
            logs.append(f"【{enemy.name}】呼唤雷云，召唤了一只【雷影魔仆】加入战场。")
        elif intent.type == "electric_overload":
            engine._add_buff_to(enemy, "strength", "力量", "造成的伤害增加", 2)
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="lightning")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            run.node_data["thunder_lord_overloaded"] = True
            logs.append(f"【{enemy.name}】释放电能超载。{dmg_msg}")
        elif intent.type == "defend":
            enemy.shield += intent.val
            logs.append(f"【{enemy.name}】凝聚雷电防护，获得 {intent.val} 点护盾。")
        return "\n".join(logs)

@register_enemy("虚空之门·尤格-索托斯")
class BossYogSothothTemplate(EnemyTemplate):
    def on_turn_start(self, event, enemy, engine):
        if not event.is_player:
            return
        run = event.run
        p = run.player
        run.node_data["merchant_collection_free_cards"] = []
        if run.node_data.get("yog_sothoth_phase", 1) == 4:
            run.node_data["yog_sothoth_turn"] = run.node_data.get("yog_sothoth_turn", 0) + 1
            import random
            npc_options = [
                ("Guide_Elder", "elder_guidance", "👴 向导长老：‘老夫活了这把年纪，什么大风大浪没见过！区区虚空，岂能断我人族薪火！孩子，看好了，这是历代先驱指引的光芒！’"),
                ("Blacksmith_Ironclad", "ironclad_rampart", "🔨 铁匠艾恩克拉德：‘喂！臭小子！接着这个！这可是老子用太阳之火和九天陨铁融了三天三夜打造的精钢壁垒！别给我打碎了！’"),
                ("Bartender_Jack", "jack_brew", "🍺 酒保杰克：‘哈！看来我来得正是时候！战斗结束了我们再痛饮，但现在——把这壶我藏了百年的“秘密佳酿”喝下去！给我站起来！’"),
                ("Market_Merchant", "merchant_collection", "🃏 卡牌商人：‘嘿！别小看了商人的野心！虚空又如何？既然是卡牌的对决，我的货架上就永远有能逆转战局的神话藏品！收下它！’"),
                ("Lost_Bard", "bard_epic", "🎵 迷路的诗人：‘琴弦虽已在虚空中沙哑，但我听见了你胸腔中不屈的律动！在这终焉的余烬里，我将为你弹奏最后一曲英雄史诗！高歌吧！’")
            ]
            chosen_npc = random.choice(npc_options)
            npc_id, card_id, quote = chosen_npc
            from ...models.state import CardState
            npc_card_state = CardState(id=card_id, upgraded=True)
            p.hand.append(npc_card_state)
            card_name = "专属助战卡"
            if card_id == "elder_guidance":
                card_name = "长老的先古指引"
            elif card_id == "ironclad_rampart":
                card_name = "艾恩克拉德的壁垒"
            elif card_id == "jack_brew":
                card_name = "杰克的烈性黑啤"
            elif card_id == "merchant_collection":
                card_name = "商人的神话藏品"
            elif card_id == "bard_epic":
                card_name = "诗人的绝响之歌"
            engine._log_event(run, f"🌟 {quote}\n🎁 助战卡牌【{card_name}】已加入你的手牌！")

    def on_card_play(self, event, enemy, engine):
        run = event.run
        p = run.player
        card = event.card
        if run.node_data.get("intangible_whisper_active"):
            run.node_data.pop("intangible_whisper_active", None)
            import random
            if card.type == "spell" and getattr(card, "base_dmg", 0) > 0:
                my_targets = ["p0"] + [f"p{k}" for k in p.minions.keys()]
                event.target = random.choice(my_targets)
                engine._log_event(run, f"🌀 [无形低语重定向] 你的心智被耳边的低语重塑！你原本指向敌人的法术【{card.name}】被强行偏转，指向了【{engine._get_target_name(run, event.target)}】！")
            elif card.type == "spell" and getattr(card, "heal_amount", 0) > 0:
                if run.enemies:
                    event.target = f"e{random.randint(1, len(run.enemies))}"
                    engine._log_event(run, f"🌀 [无形低语重定向] 混乱的魔力让你敌友不分！你治愈生命的秘法被强行偏转，为敌人【{engine._get_target_name(run, event.target)}】注入了活力！")
            elif card.type == "attack" or card.id.startswith("warrior_"):
                my_targets = ["p0"] + [f"p{k}" for k in p.minions.keys()]
                event.target = random.choice(my_targets)
                engine._log_event(run, f"🌀 [无形低语重定向] 你的心智被低语重塑！你原本的物理攻击【{card.name}】被强行偏转，指向了【{engine._get_target_name(run, event.target)}】！")

        if card.id in run.node_data.get("merchant_collection_free_cards", []):
            event.cost_a = 0
            event.cost_ba = 0

        if run.node_data.get("yog_sothoth_phase", 1) == 4 and card.type == "spell":
            import random
            if random.random() < 0.30:
                event.cancel()
                p.actions = max(0, p.actions - event.cost_a)
                p.bonus_actions = max(0, p.bonus_actions - event.cost_ba)
                hand_idx = run.node_data.get("current_playing_card_hand_idx", 0)
                if 0 <= hand_idx < len(p.hand):
                    c_state = p.hand.pop(hand_idx)
                else:
                    c_state = None
                if c_state:
                    p.exhaust_pile.append(c_state)
                    from ...models.events import CardExhaustEvent
                    exhaust_evt = CardExhaustEvent(run, c_state, "void_distortion_cancel")
                    engine.event_bus.dispatch(exhaust_evt)
                engine._log_event(run, f"⚠️ [时空紊乱] 尤格-索托斯的真理力场扭曲，【{card.name}】还未释放便被强制消耗！")
                run.node_data["cards_played_this_turn"] = run.node_data.get("cards_played_this_turn", 0) + 1
                engine.save_manager.save_save(run.user_id, run)

    def on_turn_end(self, event, enemy, engine):
        if not event.is_player:
            return
        run = event.run
        p = run.player
        if run.node_data.get("yog_sothoth_phase", 1) == 4 and len(p.hand) == 0:
            engine.combat_resolver.damage_target(run, "p0", 10, source="yog_sothoth_passive", damage_type="true")
            engine._log_event(run, "⚠️ [万物归一] 由于回合结束时你没有任何手牌，受到了尤格-索托斯【万物归一】的 10 点真实伤害！")
        for cs in p.hand:
            if cs.id == "curse_intangible_whisper":
                run.node_data["intangible_whisper_active"] = True

    def on_enemy_before_death(self, run, enemy, event, engine):
        if enemy.name == "虚空之门·尤格-索托斯":
            event.cancel()
            enemy.hp = 1
            enemy.shield = 0
            if "pending_transitions" not in run.node_data:
                run.node_data["pending_transitions"] = {}
            run.node_data["pending_transitions"][enemy.name] = 2
            from ...models.state import BuffState, EnemyIntentState
            enemy.buffs.append(BuffState(id="phase_transition_immune", name="转换阶段", stacks=1, desc="处于转换阶段状态，免疫所有伤害"))
            enemy.intents.clear()
            enemy.intents.append(EnemyIntentState(
                type="phase_transition",
                val=0,
                desc="能量奔流 (转换阶段：虚空重组中，此回合免疫所有伤害)",
                cost_a=1,
                cost_ba=0
            ))
            engine.enemy_controller.sync_enemy_intents(enemy)
            engine._log_event(run, "⚠️ 虚空之门·尤格-索托斯受到了致命伤，即将触发第二阶段觉醒！它正凝聚力场进入转换阶段...")
        elif enemy.name == "【觉醒】虚空之门·尤格-索托斯":
            event.cancel()
            enemy.hp = 1
            enemy.shield = 0
            if "pending_transitions" not in run.node_data:
                run.node_data["pending_transitions"] = {}
            run.node_data["pending_transitions"][enemy.name] = 3
            from ...models.state import BuffState, EnemyIntentState
            enemy.buffs.append(BuffState(id="phase_transition_immune", name="转换阶段", stacks=1, desc="处于转换阶段状态，免疫所有伤害"))
            enemy.intents.clear()
            enemy.intents.append(EnemyIntentState(
                type="phase_transition",
                val=0,
                desc="终焉显化 (转换阶段：终焉临界中，此回合免疫所有伤害)",
                cost_a=1,
                cost_ba=0
            ))
            engine.enemy_controller.sync_enemy_intents(enemy)
            engine._log_event(run, "⚠️ 【觉醒】虚空之门·尤格-索托斯受到了致命伤，即将触发第三阶段觉醒！它正凝聚力场进入转换阶段...")
        elif enemy.name == "【终焉】虚空之门·尤格-索托斯":
            event.cancel()
            enemy.hp = 1
            enemy.shield = 0
            if "pending_transitions" not in run.node_data:
                run.node_data["pending_transitions"] = {}
            run.node_data["pending_transitions"][enemy.name] = 4
            from ...models.state import BuffState, EnemyIntentState
            enemy.buffs.append(BuffState(id="phase_transition_immune", name="转换阶段", stacks=1, desc="处于转换阶段状态，免疫所有伤害"))
            enemy.intents.clear()
            enemy.intents.append(EnemyIntentState(
                type="phase_transition",
                val=0,
                desc="万物归一 (转换阶段：维度代码崩溃，万物收敛中，此回合免疫所有伤害)",
                cost_a=1,
                cost_ba=0
            ))
            engine.enemy_controller.sync_enemy_intents(enemy)
            engine._log_event(run, "⚠️ 【终焉】虚空之门·尤格-索托斯受到了致命伤，即将触发第四阶段觉醒！它正凝聚力场进入转换阶段...")

    def apply_phase_transition(self, run, enemy, target_phase: int, engine, logs: list):
        from ...models.state import BuffState
        if target_phase == 2:
            enemy.name = "【觉醒】虚空之门·尤格-索托斯"
            enemy.max_hp = 260
            enemy.hp = 260
            enemy.shield = 30
            enemy.actions = 2
            enemy.bonus_actions = 2
            enemy.max_actions = 2
            enemy.max_bonus_actions = 2
            enemy.buffs.clear()
            enemy.buffs.append(BuffState(id="end_gate_passive", name="终焉之门", stacks=1, desc="每回合开始获得 15 点护盾并清除自身负面效果；拥有护盾时，受到伤害会反弹 1 点真实伤害"))
            enemy.buffs.append(BuffState(id="phase_transition_immune", name="转换阶段", stacks=1, desc="处于转换阶段状态，免疫所有伤害"))
            run.node_data["yog_sothoth_phase"] = 2
            run.node_data["yog_sothoth_turn"] = 0
            run.node_data["is_void_corrupted"] = True
            logs.append("🌟 虚空之门·尤格-索托斯破裂了！狂暴的虚空能量从中倾泻而出，虚空之门在坍缩中重新觉醒！进入了觉醒形态！")
            logs.append(f"💬 【觉醒】虚空之门·尤格-索托斯：‘{run.player.name}，你的挣扎在无光之海中毫无意义。虚空已将 you 锁死，直面你的终焉吧！’")
        elif target_phase == 3:
            enemy.name = "【终焉】虚空之门·尤格-索托斯"
            enemy.max_hp = 300
            enemy.hp = 300
            enemy.shield = 50
            enemy.actions = 3
            enemy.bonus_actions = 2
            enemy.max_actions = 3
            enemy.max_bonus_actions = 2
            enemy.buffs.clear()
            from ...models.state import BuffState, EnemyIntentState
            enemy.buffs.append(BuffState(id="doomsday_gate_passive", name="终焉庇护", stacks=1, desc="每回合开始获得 20 护盾与 2 层力量；拥有护盾时，受到伤害会反弹 1 点真实伤害与 2 点力场伤害"))
            enemy.buffs.append(BuffState(id="phase_transition_immune", name="转换阶段", stacks=1, desc="处于转换阶段状态，免疫所有伤害"))
            run.node_data["yog_sothoth_phase"] = 3
            run.node_data["yog_sothoth_turn"] = 0
            run.node_data["is_void_corrupted"] = True
            enemy.intents.clear()
            enemy.intents.append(EnemyIntentState(
                type="phase_transition",
                val=0,
                desc="终焉显化 (转换阶段：终焉临界中，此回合免疫所有伤害)",
                cost_a=1,
                cost_ba=0
            ))
            engine.enemy_controller.sync_enemy_intents(enemy)
            engine._log_event(run, "🌟 虚空之门爆发出极具毁灭性的光华，次元壁垒彻底粉碎！门扉之中显露出难以名状的混沌本质——终焉降临！")
            engine._log_event(run, f"💬 【终焉】虚空之门·尤格-索托斯：‘万物归于虚无。{run.player.name}，化为这片坍缩维度的一部分吧！’")
        elif target_phase == 4:
            enemy.name = "【万物归一】虚空之门·尤格-索托斯"
            enemy.max_hp = 2147483647
            enemy.hp = 2147483647
            enemy.shield = 80
            enemy.actions = 3
            enemy.bonus_actions = 3
            enemy.max_actions = 3
            enemy.max_bonus_actions = 3
            enemy.buffs.clear()
            from ...models.state import BuffState, EnemyIntentState
            enemy.buffs.append(BuffState(id="transcendence_passive", name="万物归一", stacks=1, desc="每回合开始获得 30 护盾，净化自身负面 Buff。任何被打出的法术卡牌有 30% 几率因为时空紊乱直接被消耗且无效果。每回合结束时，玩家如果没有任何手牌则受到 10 点真实伤害。"))
            enemy.buffs.append(BuffState(id="phase_transition_immune", name="转换阶段", stacks=1, desc="处于转换阶段状态，免疫所有伤害"))
            run.node_data["yog_sothoth_phase"] = 4
            run.node_data["yog_sothoth_turn"] = 0
            run.node_data["is_void_corrupted"] = True
            enemy.intents.clear()
            enemy.intents.append(EnemyIntentState(
                type="phase_transition",
                val=0,
                desc="万物归一 (转换阶段：维度代码崩溃，万物收敛中，此回合免疫所有伤害)",
                cost_a=1,
                cost_ba=0
            ))
            logs.append("🌟 虚空之门彻底失去控制，整个战场的时空维度开始崩解！不可名状的终极恐怖——万物归一，降临了！")
            logs.append(f"💬 【万物归一】虚空之门·尤格-索托斯：‘万物归一……这是你们注定的归宿。’")
            engine.enemy_controller.sync_enemy_intents(enemy)
            stats = engine.save_manager.load_stats(run.user_id)
            challenge_count = getattr(stats, "yog_sothoth_challenge_count", 1)
            engine._log_event(run, "🌟 警告：检测到未捕获的致命异常！时空封印已被彻底从内存中抹除！尤格-索托斯将其本体跨过碎裂的时空屏障，游戏数据已被强行改写——进入第四阶段——【万物归一】！")
            if challenge_count == 1:
                engine._log_event(run, f"💬 【万物归一】虚空之门·尤格-索托斯：‘愚蠢的观测者，你以为这仅仅是一场游戏？你的手牌、你的属性、连同你在这个插件里的整个生涯存档……都将收敛为万物归一的尘埃！’")
            else:
                engine._log_event(run, f"💬 【万物归一】虚空之门·尤格-索托斯：‘你还没有放弃吗？在你无数次的失败尝试中，这行改写代码已经被执行了成千上万次。这一次，老友，我们将迎来永恒的归一！’")
            engine._log_event(run, "🌟 虚空开始剧烈震荡，系统的代码和物理法则已经濒临崩溃……就在此时，你身后亮起了一道温暖的金光，是先古主城的守护者和居民们！他们穿越了破碎的次元裂缝，前来助你一力！")


    def roll_intents(self, run, engine, enemy) -> List['EnemyIntentState']:
        from ...models.state import EnemyIntentState
        phase = run.node_data.get("yog_sothoth_phase", 1)
        turn = run.node_data.get("yog_sothoth_turn", 1)
        run.node_data["yog_sothoth_turn"] = turn + 1
        cycle = (turn - 1) % 4 + 1
        intents_list = []
        if phase == 1:
            if cycle == 1:
                intents_list.append(EnemyIntentState(type="gate_gaze", val=12, desc="门之凝视 (造成 12 点心灵伤害，对随机随从造成 8 点力场伤害，玩家下回合无法抽牌)", cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="void_corruption", val=8, desc="虚空腐蚀 (造成 8 点强酸伤害并施加 1 层虚空虚弱)", cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="void_exhaust", val=1, desc="虚空耗竭 (使玩家获得 1 层虚空耗竭 Buff)", cost_a=0, cost_ba=1))
            elif cycle == 2:
                intents_list.append(EnemyIntentState(type="void_storm", val=10, desc="虚空风暴 (对玩家与所有我方随从造成 10 点力场伤害)", cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="gravity_press", val=10, desc="重力压迫 (造成 10 点钝击伤害，如果玩家身上有护盾，额外损失 5 点护盾；对随机随关造成 6 点钝击伤害)", cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="decay_whisper", val=2, desc="衰退低语 (使玩家获得 2 层虚空虚弱 Buff)", cost_a=0, cost_ba=1))
            elif cycle == 3:
                intents_list.append(EnemyIntentState(type="ancient_resonance", val=20, desc="先古共鸣 (获得 20 点护盾，且下回合获得 2 层力量)", cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="void_storm", val=8, desc="虚空风暴 (对玩家与所有我方随从造成 8 点力场伤害)", cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="mana_block", val=1, desc="魔力阻断 (使玩家获得 1 层魔力泄漏 Buff)", cost_a=0, cost_ba=1))
            else:
                intents_list.append(EnemyIntentState(type="gate_gaze", val=12, desc="门之凝视 (造成 12 点心灵伤害，对随机随从造成 8 点力场伤害，玩家下回合无法抽牌)", cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="gravity_press", val=10, desc="重力压迫 (造成 10 点钝击伤害，如果玩家身上有护盾，额外损失 5 点护盾；对随机随从造成 6 点钝击伤害)", cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="dimensional_distortion", val=15, desc="维度扭曲 (获得 15 点护盾)", cost_a=0, cost_ba=1))
        elif phase == 2:
            if cycle == 1:
                intents_list.append(EnemyIntentState(type="time_collapse", val=14, desc="时空坍缩 (造成 14 点力场伤害，玩家下回合动作减少 1A 1BA，且洗入 2 张空间撕裂)", cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="chaos_beam", val=10, desc="混乱光束 (造成 10 点光耀伤害，对所有随从造成 6 点光耀伤害)", cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="void_shield_large", val=20, desc="虚空大盾 (获得 20 点护盾并净化自身 1 负面 Buff)", cost_a=0, cost_ba=1))
                intents_list.append(EnemyIntentState(type="abyss_exhaust", val=1, desc="深渊耗竭 (使玩家获得 1 层虚空耗竭 Buff)", cost_a=0, cost_ba=1))
            elif cycle == 2:
                intents_list.append(EnemyIntentState(type="all_gates_open", val=20, desc="万门齐开 (召唤 2 个虚空潜伏者，敌方全体获得 2 层力量；若格子满则造成 20 点心灵伤害)", cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="abyss_gaze", val=12, desc="深渊凝视 (造成 12 点心灵伤害，使玩家下回合少抽 2 张牌)", cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="strength_infuse", val=2, desc="力量注入 (敌方全体获得 2 层力量)", cost_a=0, cost_ba=1))
                intents_list.append(EnemyIntentState(type="end_whisper", val=6, desc="终焉低语 (造成 6 点心灵伤害，且迫使玩家随机丢弃 1 张手牌)", cost_a=0, cost_ba=1))
            elif cycle == 3:
                intents_list.append(EnemyIntentState(type="doomsday_tide", val=12, desc="灭世之潮 (对玩家与所有随从造成 12 点真实伤害，穿透护盾，并恢复自身 15 点生命值)", cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="time_collapse", val=10, desc="时空坍缩 (造成 10 点力场伤害，玩家下回合动作减少 1A 1BA，且洗入 2 张空间撕裂)", cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="mana_block", val=1, desc="魔力阻断 (使玩家获得 1 层魔力泄漏 Buff)", cost_a=0, cost_ba=1))
                intents_list.append(EnemyIntentState(type="reality_shatter", val=8, desc="现实碎裂 (造成 8 点真实伤害)", cost_a=0, cost_ba=1))
            else:
                intents_list.append(EnemyIntentState(type="chaos_beam", val=12, desc="混乱光束 (造成 12 点光耀伤害，对所有随从造成 6 点光耀伤害)", cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="doomsday_tide", val=10, desc="灭世之潮 (对玩家与所有随从造成 10 点真实伤害，穿透护盾，并恢复自身 15 点生命值)", cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="strength_infuse", val=2, desc="力量注入 (敌方全体获得 2 层力量)", cost_a=0, cost_ba=1))
                intents_list.append(EnemyIntentState(type="void_shield_large", val=20, desc="虚空大盾 (获得 20 点护盾并净化自身 1 负面 Buff)", cost_a=0, cost_ba=1))
        elif phase == 3:
            if cycle == 1:
                intents_list.append(EnemyIntentState(type="time_collapse", val=14, desc="时空坍缩 (造成 14 点力场伤害，玩家下回合动作减少 1A 1BA，且洗入 2 张空间撕裂)", cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="doomsday_tide", val=12, desc="灭世之潮 (对玩家与所有随从造成 12 点真实伤害，穿透护盾，并恢复自身 15 点生命值)", cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="chaos_beam", val=10, desc="混乱光束 (造成 10 点光耀伤害，对所有随从造成 6 点光耀伤害)", cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="void_shield_large", val=20, desc="虚空大盾 (获得 20 点护盾并净化自身 1 负面 Buff)", cost_a=0, cost_ba=1))
                intents_list.append(EnemyIntentState(type="abyss_exhaust", val=1, desc="深渊耗竭 (使玩家获得 1 层虚空耗竭 Buff)", cost_a=0, cost_ba=1))
            elif cycle == 2:
                intents_list.append(EnemyIntentState(type="all_gates_open", val=20, desc="万门齐开 (召唤 2 个虚空潜伏者，敌方全体获得 2 层力量；若格子满则造成 20 点心灵伤害)", cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="doomsday_tide", val=12, desc="灭世之潮 (对玩家与所有随随造成 12 点真实伤害，穿透护盾，并恢复自身 15 点生命值)", cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="abyss_gaze", val=12, desc="深渊凝视 (造成 12 点心灵伤害，使玩家下回合少抽 2 张牌)", cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="strength_infuse", val=2, desc="力量注入 (敌方全体获得 2 层力量)", cost_a=0, cost_ba=1))
                intents_list.append(EnemyIntentState(type="end_whisper", val=6, desc="终焉低语 (造成 6 点心灵伤害，且迫使玩家随机丢弃 1 张手牌)", cost_a=0, cost_ba=1))
            elif cycle == 3:
                intents_list.append(EnemyIntentState(type="doomsday_tide", val=12, desc="灭世之潮 (对玩家与所有随从造成 12 点真实伤害，穿透护盾，并恢复自身 15 点生命值)", cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="time_collapse", val=10, desc="时空坍缩 (造成 10 点力场伤害，玩家下回合动作减少 1A 1BA，且洗入 2 张空间撕裂)", cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="chaos_beam", val=10, desc="混乱光束 (造成 10 点光耀伤害，对所有随从造成 6 点光耀伤害)", cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="mana_block", val=1, desc="魔力阻断 (使玩家获得 1 层魔力泄漏 Buff)", cost_a=0, cost_ba=1))
                intents_list.append(EnemyIntentState(type="reality_shatter", val=8, desc="现实碎裂 (造成 8 点真实伤害)", cost_a=0, cost_ba=1))
            else:
                intents_list.append(EnemyIntentState(type="all_gates_open", val=20, desc="万门齐开 (召唤 2 个虚空潜伏者，敌方全体获得 2 层力量；若格子满则造成 20 点心灵伤害)", cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="chaos_beam", val=12, desc="混乱光束 (造成 12 点光耀伤害，对所有随从造成 6 点光耀伤害)", cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="doomsday_tide", val=10, desc="灭世之潮 (对玩家与所有随从造成 10 点真实伤害，穿透护盾，并恢复自身 15 点生命值)", cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="strength_infuse", val=2, desc="力量注入 (敌方全体获得 2 层力量)", cost_a=0, cost_ba=1))
                intents_list.append(EnemyIntentState(type="void_shield_large", val=20, desc="虚空大盾 (获得 20 点护盾并净化自身 1 负面 Buff)", cost_a=0, cost_ba=1))
        else:
            if cycle == 1:
                intents_list.append(EnemyIntentState(type="meta_code_injection", val=15, desc="底层代码篡改 (造成 15 点心灵伤害，注入恶意 Traceback 数据，并伪造删除卡牌警告)", cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="void_storm", val=12, desc="虚空风暴 (对玩家与所有我方随从造成 12 点力场伤害)", cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="input_hijack", val=12, desc="指令输入劫持 (造成 12 点心灵伤害，洗入 2 张【无形低语】)", cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="void_shield_large", val=30, desc="虚空大盾 (获得 30 点护盾并清除 1 个负面 Buff)", cost_a=0, cost_ba=1))
            elif cycle == 2:
                intents_list.append(EnemyIntentState(type="data_overflow", val=15, desc="数据溢出攻击 (造成 3 次 5 点力场伤害，且混淆界面生命数值显示)", cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="doomsday_tide", val=15, desc="灭世之潮 (对玩家及所有随从造成 15 点真实伤害，自身恢复 20 生命)", cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="strength_infuse", val=3, desc="力量注入 (敌方全体获得 3 层力量)", cost_a=0, cost_ba=1))
                intents_list.append(EnemyIntentState(type="end_whisper", val=8, desc="终焉低语 (造成 8 点心灵伤害，迫使下回合随机弃 2 张牌)", cost_a=0, cost_ba=1))
            elif cycle == 3:
                intents_list.append(EnemyIntentState(type="save_erase", val=0, desc="存档抹除 (获得 35 护盾，并尝试抹除 5 枚金币；若无金币则扣除生命上限)", cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="time_collapse", val=15, desc="时空坍缩 (造成 15 点力场伤害，玩家下回合减少 1A 1BA，洗入 2 张空间撕裂)", cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="mana_block", val=2, desc="魔力阻断 (使玩家获得 2 层魔力泄漏 Buff)", cost_a=0, cost_ba=1))
                intents_list.append(EnemyIntentState(type="reality_shatter", val=12, desc="现实碎裂 (造成 12 点真实伤害)", cost_a=0, cost_ba=1))
            else:
                intents_list.append(EnemyIntentState(type="meta_code_injection", val=15, desc="底层代码篡改 (造成 15 点心灵伤害，注入恶意 Traceback)", cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="data_overflow", val=15, desc="数据溢出攻击 (造成 15 点力场伤害，生命混淆)", cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="input_hijack", val=12, desc="指令输入劫持 (造成 12 点心灵伤害，洗入 2 张【无形低语】)", cost_a=1, cost_ba=0))
                intents_list.append(EnemyIntentState(type="void_shield_large", val=30, desc="虚空大盾 (获得 30 点护盾)", cost_a=0, cost_ba=1))
        return intents_list

        return intents_list


    def execute_intent(self, run, engine, enemy, intent, logs: List[str] = None):
        if logs is None:
            logs = intent
            from ...models.state import EnemyIntentState
            intent = EnemyIntentState(
                type=getattr(enemy, "intent_type", ""),
                val=getattr(enemy, "intent_val", 0),
                desc=getattr(enemy, "intent_desc", ""),
                cost_a=1,
                cost_ba=0
            )
        p = run.player
        import random
        from ..buffs import is_debuff

        strength = 0
        for b in enemy.buffs:
            if b.id == "strength":
                strength += b.stacks
        val = intent.val + strength

        if intent.type == "gate_gaze":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="psychic")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            logs.append(f"【{enemy.name}】对玩家施展门之凝视。{dmg_msg}")
            if p.minions:
                target_key = random.choice(list(p.minions.keys()))
                m_name = p.minions[target_key].name
                before_len = len(run.node_data.get("battle_logs", []))
                engine._damage_target(run, f"p{target_key}", 8, source=f"enemy:{enemy.name}", damage_type="force")
                after_logs = run.node_data.get("battle_logs", [])
                dmg_msg_m = after_logs.pop() if len(after_logs) > before_len else ""
                logs.append(f"随从【{m_name}】受到波及。{dmg_msg_m}")
            engine._add_buff_to(run.player, "tactical_focus", "无法抽牌", "本回合无法再抽牌", 1)
            logs.append(f"【{enemy.name}】的心灵波动使玩家在下一回合【无法抽牌】。")

        elif intent.type == "void_storm":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="force")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            logs.append(f"【{enemy.name}】引发虚空风暴。{dmg_msg}")
            for mk in list(p.minions.keys()):
                if mk not in p.minions:
                    continue
                m_name = p.minions[mk].name
                before_len = len(run.node_data.get("battle_logs", []))
                engine._damage_target(run, f"p{mk}", val, source=f"enemy:{enemy.name}", damage_type="force")
                after_logs = run.node_data.get("battle_logs", [])
                dmg_msg_m = after_logs.pop() if len(after_logs) > before_len else ""
                logs.append(f"我方随从【{m_name}】受到虚空风暴波及。{dmg_msg_m}")

        elif intent.type == "ancient_resonance":
            enemy.shield += intent.val
            engine._add_buff_to(enemy, "strength", "力量", "造成的伤害增加", 2)
            logs.append(f"【{enemy.name}】进行先古共鸣，获得 {intent.val} 点护盾，且攻击力量提升 2 点。")

        elif intent.type == "void_corruption":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="acid")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            engine._add_buff_to(run.player, "void_weakness", "虚空虚弱", "造成的法术伤害减少 3 点，回合结束时层数减少 1", 1)
            logs.append(f"【{enemy.name}】引发虚空腐蚀对玩家造成酸蚀。{dmg_msg}")
            logs.append(f"玩家获得了 1 层【虚空虚弱】状态。")

        elif intent.type == "gravity_press":
            lost_shield_msg = ""
            if p.shield > 0:
                lost_amount = min(5, p.shield)
                p.shield -= lost_amount
                lost_shield_msg = f"（重力场额外压碎了玩家 {lost_amount} 点护盾）"
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="bludgeoning")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            logs.append(f"【{enemy.name}】施展重力压迫。{dmg_msg}{lost_shield_msg}")
            if p.minions:
                target_key = random.choice(list(p.minions.keys()))
                m_name = p.minions[target_key].name
                before_len = len(run.node_data.get("battle_logs", []))
                engine._damage_target(run, f"p{target_key}", 6, source=f"enemy:{enemy.name}", damage_type="bludgeoning")
                after_logs = run.node_data.get("battle_logs", [])
                dmg_msg_m = after_logs.pop() if len(after_logs) > before_len else ""
                logs.append(f"我方随从【{m_name}】受到重力余波打击。{dmg_msg_m}")

        elif intent.type in ("void_exhaust", "abyss_exhaust"):
            engine._add_buff_to(run.player, "void_exhaustion", "虚空耗竭", "本回合内打出的所有非随从和护符卡牌都会在结算后被强制消耗移入消耗堆", 1)
            logs.append(f"【{enemy.name}】引动了虚空耗竭，玩家被施加了 1 层【虚空耗竭】状态！")

        elif intent.type == "decay_whisper":
            engine._add_buff_to(run.player, "void_weakness", "虚空虚弱", "造成的法术伤害减少 3 点，回合结束时层数减少 1", 2)
            logs.append(f"【{enemy.name}】低吟起衰退歌谣，使玩家获得了 2 层【虚空虚弱】状态。")

        elif intent.type == "mana_block":
            engine._add_buff_to(run.player, "mana_leak", "魔力泄漏", "你打出的法术卡牌需要额外消耗 1BA，且造成的法术伤害减少 2 点", 1)
            logs.append(f"【{enemy.name}】施加魔力阻断，使玩家获得了 1 层【魔力泄漏】状态。")

        elif intent.type == "dimensional_distortion":
            enemy.shield += intent.val
            logs.append(f"【{enemy.name}】扭曲周围的维度，获得了 {intent.val} 点护盾。")

        elif intent.type == "time_collapse":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="force")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            engine._add_buff_to(run.player, "drain_a", "时间纠缠", "在下一回合开始时，你将失去等同于此状态层数的动作点 (A)", 1)
            engine._add_buff_to(run.player, "drain_ba", "虚空纠缠", "在下一回合开始时，你将失去等同于此状态层数的附赠动作点 (BA)", 1)
            p.draw_pile.append("curse_dimensional_tear")
            p.draw_pile.append("curse_dimensional_tear")
            random.shuffle(p.draw_pile)
            logs.append(f"【{enemy.name}】施展时空坍缩，使玩家在下一回合失去 1A 1BA，且洗入 2 张【空间撕裂】。{dmg_msg}")

        elif intent.type == "chaos_beam":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="radiant")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            logs.append(f"【{enemy.name}】射出混乱光束。{dmg_msg}")
            for mk in list(p.minions.keys()):
                if mk not in p.minions:
                    continue
                m_name = p.minions[mk].name
                before_len = len(run.node_data.get("battle_logs", []))
                engine._damage_target(run, f"p{mk}", 6, source=f"enemy:{enemy.name}", damage_type="radiant")
                after_logs = run.node_data.get("battle_logs", [])
                dmg_msg_m = after_logs.pop() if len(after_logs) > before_len else ""
                logs.append(f"我方随从【{m_name}】受到混乱光束穿透。{dmg_msg_m}")

        elif intent.type == "void_shield_large":
            enemy.shield += intent.val
            neg_buff = next((b for b in enemy.buffs if is_debuff(b.id)), None)
            if neg_buff:
                neg_name = neg_buff.name
                neg_buff.stacks -= 1
                if neg_buff.stacks <= 0:
                    enemy.buffs.remove(neg_buff)
                engine._sync_enemy_intents(enemy)
                logs.append(f"【{enemy.name}】施展虚空大盾，获得 {intent.val} 点护盾，并解除了 1 层自身的负面状态【{neg_name}】！")
            else:
                logs.append(f"【{enemy.name}】施展虚空大盾，获得 {intent.val} 点护盾。")

        elif intent.type == "all_gates_open":
            empty_slots = 6 - len(run.enemies)
            summon_count = min(2, empty_slots)
            from ...models.state import EnemyState, EnemyIntentState
            for _ in range(summon_count):
                new_minion = EnemyState(
                    name="虚空潜伏者",
                    hp=20,
                    max_hp=20,
                    shield=0,
                    actions=1,
                    bonus_actions=0,
                    is_summon=True,
                    max_actions=1,
                    max_bonus_actions=0,
                    intents=[EnemyIntentState(
                        type="void_strike",
                        val=6,
                        desc="虚空打击 (造成 6 点黯蚀伤害)",
                        cost_a=1,
                        cost_ba=0
                    )]
                )
                run.enemies.append(new_minion)
            for e in run.enemies:
                engine._add_buff_to(e, "strength", "力量", "造成的伤害增加", 2)
            logs.append(f"【{enemy.name}】开启了万门，召唤了 {summon_count} 个【虚空潜伏者】，且敌方全体力量提升了 2 点。")
            if summon_count < 2:
                before_len = len(run.node_data.get("battle_logs", []))
                engine._damage_target(run, "p0", 20, source=f"enemy:{enemy.name}", damage_type="psychic")
                after_logs = run.node_data.get("battle_logs", [])
                dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
                logs.append(f"由于传送门受阻，虚空能量直接冲击玩家。{dmg_msg}")

        elif intent.type == "abyss_gaze":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="psychic")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            run.node_data["draw_penalty_next_turn"] = 2
            logs.append(f"【{enemy.name}】投射深渊凝视，玩家下回合少抽 2 张牌。{dmg_msg}")

        elif intent.type == "strength_infuse":
            for e in run.enemies:
                engine._add_buff_to(e, "strength", "力量", "造成的伤害增加", 2)
            logs.append(f"【{enemy.name}】进行力量注入，敌方全体力量提升 2 点。")

        elif intent.type == "end_whisper":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="psychic")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            engine._add_buff_to(run.player, "discard_next_turn", "下回合弃牌", "在下一回合开始时，你将随机丢弃等同于此状态层数的手牌", 1)
            logs.append(f"【{enemy.name}】发出终焉低语。{dmg_msg}，且使玩家在下一回合开始时将被迫随机丢弃 1 张手牌。")

        elif intent.type == "doomsday_tide":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="true")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            logs.append(f"【{enemy.name}】释放了灭世之潮！造成真实伤害。{dmg_msg}")
            for mk in list(p.minions.keys()):
                if mk not in p.minions:
                    continue
                m_name = p.minions[mk].name
                before_len = len(run.node_data.get("battle_logs", []))
                engine._damage_target(run, f"p{mk}", val, source=f"enemy:{enemy.name}", damage_type="true")
                after_logs = run.node_data.get("battle_logs", [])
                dmg_msg_m = after_logs.pop() if len(after_logs) > before_len else ""
                logs.append(f"我方随从【{m_name}】受到真实伤害波及。{dmg_msg_m}")
            enemy.hp = min(enemy.max_hp, enemy.hp + 15)
            logs.append(f"【{enemy.name}】吸取了生命力，恢复了 15 点生命值。")

        elif intent.type == "reality_shatter":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="true")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            logs.append(f"【{enemy.name}】引爆现实碎裂，对玩家造成真实伤害。{dmg_msg}")

        elif intent.type == "meta_code_injection":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="psychic")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            logs.append(f"【{enemy.name}】引动了底层代码篡改。{dmg_msg}")
            logs.append(
                "Traceback (most recent call last):\n"
                "  File \"game/core/battle_engine.py\", line 212, in run_combat_turn\n"
                "    raise DimensionCollapseError(\"Yog-Sothoth injected malicious bytes into GameRun.state.\")\n"
                "game.core.battle.exceptions.DimensionCollapseError: 维度坍缩：存档已损坏？不，尤格-索托斯篡改了底层代码！\n"
                "💬 【万物归一】虚空之门·尤格-索托斯：‘在我的真理之下，你们的代码不过是虚无的泥潭。下一个回合，如果你没有打出任何一张【防御】卡牌，我将从你的卡组中删去最珍贵的一张卡！’"
            )

        elif intent.type == "data_overflow":
            before_len = len(run.node_data.get("battle_logs", []))
            for _ in range(3):
                engine._damage_target(run, "p0", 5, source=f"enemy:{enemy.name}", damage_type="force")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msgs = []
            while len(after_logs) > before_len:
                dmg_msgs.append(after_logs.pop())
            dmg_msgs.reverse()
            dmg_summary = " ".join(dmg_msgs)
            logs.append(f"【{enemy.name}】引爆了数据溢出攻击！{dmg_summary}")
            logs.append(
                "⚠️ 【数据溢出警告】\n"
                "SYSTEM_DETECTED_ERROR: PLAYER_HP_OVERFLOW [HP: -9999 / 9999]\n"
                "但由于先古守护的底层数据冗余重构，你的实际生命值未受影响。"
            )

        elif intent.type == "save_erase":
            enemy.shield += 35
            gold_removed = 0
            hp_limit_removed = 0
            if p.gold >= 5:
                p.gold -= 5
                gold_removed = 5
            else:
                p.hp = max(1, p.hp - 5)
                p.max_hp = max(10, p.max_hp - 5)
                hp_limit_removed = 5
            if gold_removed:
                logs.append(
                    f"【{enemy.name}】施展了时空抹除，试图擦除你的存在，获得了 35 点护盾！\n"
                    "⚠️ 尤格-索托斯正在读取你的存档... 试图执行 delete_save()...\n"
                    "🛡️ 先古防火墙防御成功！但你仍丢失了 5 枚金币！"
                )
            else:
                logs.append(
                    f"【{enemy.name}】施展了时空抹除，试图擦除你的存在，获得了 35 点护盾！\n"
                    "⚠️ 尤格-索托斯正在读取你的存档... 试图执行 delete_save()...\n"
                    f"🛡️ 先古防火墙防御成功！但时空抹除的余波导致你的生命上限被永久削减了 {hp_limit_removed} 点！"
                )

        elif intent.type == "input_hijack":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="psychic")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            p.draw_pile.append("curse_intangible_whisper")
            p.draw_pile.append("curse_intangible_whisper")
            random.shuffle(p.draw_pile)
            logs.append(f"【{enemy.name}】引动了指令输入劫持。{dmg_msg}，且将 2 张【无形低语】洗入了你的抽牌堆！")

        return "\n".join(logs)

register_enemy("【觉醒】虚空之门·尤格-索托斯")(BossYogSothothTemplate)
register_enemy("【终焉】虚空之门·尤格-索托斯")(BossYogSothothTemplate)
register_enemy("【万物归一】虚空之门·尤格-索托斯")(BossYogSothothTemplate)

@register_enemy("亚弗戈蒙")
class BossAforgomonTemplate(EnemyTemplate):
    def on_enemy_before_death(self, run, enemy, event, engine):
        if enemy.name == "亚弗戈蒙":
            event.cancel()
            enemy.hp = 1
            enemy.shield = 0
            if "pending_transitions" not in run.node_data:
                run.node_data["pending_transitions"] = {}
            run.node_data["pending_transitions"][enemy.name] = 2
            from ...models.state import BuffState, EnemyIntentState
            enemy.buffs.append(BuffState(id="phase_transition_immune", name="转换阶段", stacks=1, desc="处于转换阶段状态，免疫所有伤害"))
            enemy.intents.clear()
            enemy.intents.append(EnemyIntentState(
                type="phase_transition",
                val=0,
                desc="时空回切 (转换阶段：无上时空正在重塑维度，此回合免疫所有伤害)",
                cost_a=1,
                cost_ba=0
            ))
            engine.enemy_controller.sync_enemy_intents(enemy)
            engine._log_event(run, "⚠️ 亚弗戈蒙受到了致命伤，即将触发形态觉醒！它凝聚周围的时空裂隙进入转换阶段...")

    def apply_phase_transition(self, run, enemy, target_phase: int, engine, logs: list):
        from ...models.state import BuffState
        if target_phase == 2:
            enemy.name = "【时空主宰】亚弗戈蒙"
            enemy.max_hp = 220
            enemy.hp = 220
            enemy.shield = 40
            enemy.actions = 3
            enemy.bonus_actions = 1
            enemy.max_actions = 3
            enemy.max_bonus_actions = 1
            enemy.buffs.clear()
            enemy.buffs.append(BuffState(id="time_lord_passive", name="时空主宰", stacks=1, desc="每回合开始获得 20 护盾，且清除自身所有负面效果；受到伤害时 50% 几率召唤时空残影；分担 50% 伤害"))
            enemy.buffs.append(BuffState(id="phase_transition_immune", name="转换阶段", stacks=1, desc="处于转换阶段状态，免疫所有伤害"))
            engine._add_buff_to(run.player, "pendulum_resonance", "钟摆共振", "回合结束时若动作点全光则受打出牌数*2点真伤惩罚，保留至少1A 1BA则获得额外抽取2张牌的奖赏", 1)
            run.node_data["aforgomon_phase"] = 2
            run.node_data["aforgomon_turn"] = 0
            logs.append("⏳ 虚空中回荡起清脆的钟鸣，亚弗戈蒙的身影在无数个平行时空交错叠加，最终汇聚为无法名状的伟岸实体！")
            logs.append(f"💬 【时空主宰】亚弗戈蒙：‘时间的织网已被你扯碎，{run.player.name}。现在，在无尽轮回的钟摆共鸣中，化为微尘吧！’")

    def roll_intents(self, run, engine, enemy) -> List['EnemyIntentState']:
        from ...models.state import EnemyIntentState
        import random
        phase = run.node_data.get("aforgomon_phase", 1)
        turn = run.node_data.get("aforgomon_turn", 1)
        run.node_data["aforgomon_turn"] = turn + 1
        intents_list = []
        if phase == 1:
            for _ in range(enemy.max_actions):
                chosen = random.choice([
                    {"id": "chain_of_time", "val": 8, "desc": "时间之链 (造成 8 点力场伤害，使玩家下回合减少 1A)"},
                    {"id": "portal_implosion", "val": 15, "desc": "门扉内爆 (造成 15 点钝击伤害，若玩家有护盾额外造成 5 点伤害)"}
                ])
                intents_list.append(EnemyIntentState(
                    type=chosen["id"],
                    val=chosen["val"],
                    desc=chosen["desc"],
                    cost_a=1,
                    cost_ba=0
                ))
            for _ in range(enemy.max_bonus_actions):
                intents_list.append(EnemyIntentState(
                    type="time_warp",
                    val=15,
                    desc="时空扭曲 (获得 15 点护盾，下回合获得 1 层力量)",
                    cost_a=0,
                    cost_ba=1
                ))
        else:
            for _ in range(enemy.max_actions):
                chosen = random.choice([
                    {"id": "time_fracture", "val": 12, "desc": "时序断裂 (造成 12 点力场伤害，并使玩家手牌除首张外全部获得【易碎 1】磨损)"},
                    {"id": "silver_bell_clang", "val": 15, "desc": "银钟轰鸣 (造成 15 点雷鸣伤害，若玩家已受【钟摆共振】则额外造成 5 点真实伤害，否则对其施加【钟摆共振】)"},
                    {"id": "time_reflux", "val": 0, "desc": "时空回退 (获得 20 点护盾并恢复自身 25 点生命值)"}
                ])
                intents_list.append(EnemyIntentState(
                    type=chosen["id"],
                    val=chosen["val"],
                    desc=chosen["desc"],
                    cost_a=1,
                    cost_ba=0
                ))
            for _ in range(enemy.max_bonus_actions):
                intents_list.append(EnemyIntentState(
                    type="temporal_lock",
                    val=5,
                    desc="时间锁定 (造成 5 点心灵伤害，且迫使玩家随机丢弃 1 张手牌)",
                    cost_a=0,
                    cost_ba=1
                ))
        return intents_list

    def execute_intent(self, run, engine, enemy, intent, logs: List[str] = None):
        if logs is None:
            logs = intent
            from ...models.state import EnemyIntentState
            intent = EnemyIntentState(
                type=getattr(enemy, "intent_type", ""),
                val=getattr(enemy, "intent_val", 0),
                desc=getattr(enemy, "intent_desc", ""),
                cost_a=1,
                cost_ba=0
            )
        p = run.player
        strength = 0
        for b in enemy.buffs:
            if b.id == "strength":
                strength += b.stacks
        val = intent.val + strength

        if intent.type == "chain_of_time":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="force")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            engine._add_buff_to(run.player, "drain_a", "时间纠缠", "在下一回合开始时，你将失去等同于此状态层数的动作点 (A)", 1)
            logs.append(f"【{enemy.name}】施展时间之链对玩家造成伤害。{dmg_msg}，且使玩家在下一回合失去 1 个动作点 (A)。")
        elif intent.type == "portal_implosion":
            extra = 5 if p.shield > 0 else 0
            final_val = val + extra
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", final_val, source=f"enemy:{enemy.name}", damage_type="bludgeoning")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            logs.append(f"【{enemy.name}】引动门扉内爆。{dmg_msg}")
        elif intent.type == "time_warp":
            enemy.shield += intent.val
            engine._add_buff_to(enemy, "strength", "力量", "造成的伤害增加", 1)
            logs.append(f"【{enemy.name}】施展时空扭曲，获得 15 点护盾，且力量提升了 1 点。")
        elif intent.type == "time_fracture":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="force")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            logs.append(f"【{enemy.name}】施展时序断裂，虚空能量粉碎了局部时序。{dmg_msg}")
            affected = []
            if len(p.hand) > 1:
                for card in p.hand[1:]:
                    card.fragile = max(card.fragile, 1)
                    from ...entities import ALL_CARDS
                    card_name = "未知卡牌"
                    if card in ALL_CARDS:
                        card_name = ALL_CARDS[card].name
                    elif card.id in ALL_CARDS:
                        card_name = ALL_CARDS[card.id].name
                    affected.append(f"【{card_name}】")
            if affected:
                logs.append(f"⏳ 时序断裂的余波磨损了你的手牌，使等同于 {'、'.join(affected)} 的卡牌附着了【易碎 1】状态！")
        elif intent.type == "silver_bell_clang":
            has_resonance = any(b.id == "pendulum_resonance" for b in p.buffs)
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="thunder")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            logs.append(f"【{enemy.name}】敲响银钟，低沉的银钟轰鸣震荡灵魂。{dmg_msg}")
            if has_resonance:
                before_len2 = len(run.node_data.get("battle_logs", []))
                engine._damage_target(run, "p0", 5, source=f"enemy:{enemy.name}", damage_type="true")
                after_logs2 = run.node_data.get("battle_logs", [])
                dmg_msg2 = after_logs2.pop() if len(after_logs2) > before_len2 else ""
                logs.append(f"🔔 钟摆产生剧烈共振！对你额外造成了 5 点真实伤害！{dmg_msg2}")
            else:
                engine._add_buff_to(p, "pendulum_resonance", "钟摆共振", "回合结束时若动作点全光则受打出牌数*2点真伤惩罚，保留至少1A 1BA则获得额外抽取2张牌的奖赏", 1)
                logs.append("⏳ 银钟鸣响，你被施加了【钟摆共振】状态！")
        elif intent.type == "time_reflux":
            enemy.shield += 20
            enemy.hp = min(enemy.max_hp, enemy.hp + 25)
            logs.append(f"【{enemy.name}】发动时空回退，获得了 20 点护盾，并恢复了 25 点生命值。")
            from ..buffs import is_debuff
            neg_buff = next((b for b in enemy.buffs if is_debuff(b.id)), None)
            if neg_buff:
                neg_name = neg_buff.name
                neg_buff.stacks -= 1
                if neg_buff.stacks <= 0:
                    enemy.buffs.remove(neg_buff)
                engine._sync_enemy_intents(enemy)
                logs.append(f"⏳ 时空回退使【{enemy.name}】清除了 1 层自身的负面状态【{neg_name}】！")
        elif intent.type == "temporal_lock":
            before_len = len(run.node_data.get("battle_logs", []))
            engine._damage_target(run, "p0", val, source=f"enemy:{enemy.name}", damage_type="psychic")
            after_logs = run.node_data.get("battle_logs", [])
            dmg_msg = after_logs.pop() if len(after_logs) > before_len else ""
            engine._add_buff_to(run.player, "discard_next_turn", "下回合弃牌", "在下一回合开始时，你将随机丢弃等同于此状态层数的手牌", 1)
            logs.append(f"【{enemy.name}】施展时间锁定。{dmg_msg}，且使玩家在下一回合开始时将被迫随机丢弃 1 张手牌。")
        return "\n".join(logs)

register_enemy("【时空主宰】亚弗戈蒙")(BossAforgomonTemplate)

