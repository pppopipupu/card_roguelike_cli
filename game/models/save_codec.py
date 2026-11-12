from dataclasses import asdict

from .state import GameRun, PlayerState, EnemyState, MinionState, AmuletState, BuffState


class SaveCodecMixin:
    def to_dict(self, run: GameRun) -> dict:
        if not run:
            return {}
        logs = None
        owners = None
        if run.node_data is not None:
            if run.player_count() <= 1:
                logs = run.node_data.pop("battle_logs", None)
                owners = run.node_data.pop("battle_log_owners", None)
        try:
            res = asdict(run)
        finally:
            if run.node_data is not None:
                if logs is not None:
                    run.node_data["battle_logs"] = logs
                if owners is not None:
                    run.node_data["battle_log_owners"] = owners
        return res

    def _parse_player_state(self, p_data: dict) -> PlayerState:
        if not p_data:
            return None
        p_minions = {}
        for k, v in p_data.get("minions", {}).items():
            m_buffs = []
            for b in v.get("buffs", []):
                if b.get("id") == "summon_sickness":
                    continue
                m_buffs.append(BuffState(
                    id=b["id"],
                    name=b["name"],
                    stacks=b.get("stacks", 1),
                    stacks2=b.get("stacks2", None),
                    desc=b.get("desc", ""),
                    source_uid=b.get("source_uid", "")
                ))
            p_minions[k] = MinionState(
                id=v["id"],
                name=v["name"],
                hp=v["hp"],
                max_hp=v["max_hp"],
                atk=v["atk"],
                actions=v.get("actions", 1),
                bonus_actions=v.get("bonus_actions", 1),
                attack_actions=v.get("attack_actions", 1),
                buffs=m_buffs
            )
        p_amulets = {k: AmuletState(**v) for k, v in p_data.get("amulets", {}).items()}
        p_buffs = []
        for b in p_data.get("buffs", []):
            if b.get("id") == "summon_sickness":
                continue
            p_buffs.append(BuffState(
                id=b["id"],
                name=b["name"],
                stacks=b.get("stacks", 1),
                stacks2=b.get("stacks2", None),
                desc=b.get("desc", ""),
                source_uid=b.get("source_uid", "")
            ))
        minion_gy = list(p_data.get("minion_graveyard", []))
        enemy_gy = list(p_data.get("enemy_graveyard", []))
        if not minion_gy and not enemy_gy and "graveyard" in p_data:
            for item in p_data["graveyard"]:
                if item.startswith("minion:"):
                    minion_gy.append(item[len("minion:"):])
                elif item.startswith("enemy:"):
                    enemy_gy.append(item[len("enemy:"):])
                else:
                    enemy_gy.append(item)
        return PlayerState(
            hp=p_data["hp"],
            max_hp=p_data["max_hp"],
            shield=p_data["shield"],
            gold=p_data["gold"],
            stage=p_data["stage"],
            name=p_data.get("name", "玩家"),
            deck=p_data.get("deck", []),
            draw_pile=p_data.get("draw_pile", []),
            discard_pile=p_data.get("discard_pile", []),
            exhaust_pile=p_data.get("exhaust_pile", []),
            graveyard=p_data.get("graveyard", []),
            minion_graveyard=minion_gy,
            enemy_graveyard=enemy_gy,
            hand=p_data.get("hand", []),
            actions=p_data.get("actions", 1),
            bonus_actions=p_data.get("bonus_actions", 1),
            minions=p_minions,
            amulets=p_amulets,
            abilities=p_data.get("abilities", []),
            fold_guide=p_data.get("fold_guide", False),
            buffs=p_buffs,
            relics=p_data.get("relics", []),
            subclass=p_data.get("subclass", ""),
            selected_class=p_data.get("selected_class", "法师"),
            potions=p_data.get("potions", []),
            daily_blessing_id=p_data.get("daily_blessing_id", ""),
            downed=p_data.get("downed", False),
            is_mercenary=bool(p_data.get("is_mercenary", False)),
            mercenary_id=p_data.get("mercenary_id", ""),
            mercenary_owner=p_data.get("mercenary_owner", ""),
            mercenary_timing=p_data.get("mercenary_timing", "before")
        )

    def from_dict(self, d: dict) -> GameRun:
        if not d:
            return None
        player = self._parse_player_state(d["player"])
        player2 = self._parse_player_state(d.get("player2"))
        players = {}
        for uid, pdata in (d.get("players") or {}).items():
            parsed = self._parse_player_state(pdata)
            if parsed is not None:
                players[uid] = parsed
        enemies = []
        if "enemies" in d:
            from .state import EnemyIntentState
            for ed in d["enemies"]:
                e_buffs = []
                for b in ed.get("buffs", []):
                    if b.get("id") == "summon_sickness":
                        continue
                    e_buffs.append(BuffState(
                        id=b["id"],
                        name=b["name"],
                        stacks=b.get("stacks", 1),
                        stacks2=b.get("stacks2", None),
                        desc=b.get("desc", ""),
                        source_uid=b.get("source_uid", "")
                    ))
                intent_list = []
                if "intents" in ed:
                    for it in ed["intents"]:
                        intent_list.append(EnemyIntentState(
                            type=it.get("type", ""),
                            val=it.get("val", 0),
                            desc=it.get("desc", ""),
                            cost_a=it.get("cost_a", 1),
                            cost_ba=it.get("cost_ba", 0),
                            cancelled=it.get("cancelled", False),
                            cancelled_desc=it.get("cancelled_desc", "")
                        ))
                enemies.append(EnemyState(
                    name=ed["name"],
                    hp=ed["hp"],
                    max_hp=ed["max_hp"],
                    shield=ed["shield"],
                    actions=ed.get("actions", 1),
                    bonus_actions=ed.get("bonus_actions", 1),
                    buffs=e_buffs,
                    is_summon=ed.get("is_summon", False),
                    max_actions=ed.get("max_actions", 1),
                    max_bonus_actions=ed.get("max_bonus_actions", 0),
                    intents=intent_list,
                    intent_type=ed.get("intent_type", ""),
                    intent_val=ed.get("intent_val", 0),
                    intent_desc=ed.get("intent_desc", ""),
                    intent_a_type=ed.get("intent_a_type", ""),
                    intent_a_val=ed.get("intent_a_val", 0),
                    intent_a_desc=ed.get("intent_a_desc", ""),
                    intent_a2_type=ed.get("intent_a2_type", ""),
                    intent_a2_val=ed.get("intent_a2_val", 0),
                    intent_a2_desc=ed.get("intent_a2_desc", ""),
                    intent_ba_type=ed.get("intent_ba_type", ""),
                    intent_ba_val=ed.get("intent_ba_val", 0),
                    intent_ba_desc=ed.get("intent_ba_desc", ""),
                    intent_ba2_type=ed.get("intent_ba2_type", ""),
                    intent_ba2_val=ed.get("intent_ba2_val", 0),
                    intent_ba2_desc=ed.get("intent_ba2_desc", "")
                ))
        return GameRun(
            user_id=d["user_id"],
            node_type=d["node_type"],
            player=player,
            enemies=enemies,
            node_data=d.get("node_data", {}),
            map_data=d.get("map_data", {}),
            player2=player2,
            coop_id=d.get("coop_id", ""),
            leader_id=d.get("leader_id", ""),
            party_order=d.get("party_order", []),
            players=players
        )
