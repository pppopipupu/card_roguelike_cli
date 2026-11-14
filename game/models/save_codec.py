from dataclasses import asdict

from .state import GameRun, PlayerState, EnemyState, MinionState, AmuletState, BuffState, RoomState, EncounterSession, FloorMapState
from ..data.room_interact_data import BAG_DEFAULT_MAX_WEIGHT


class SaveCodecMixin:
    def to_dict(self, run: GameRun) -> dict:
        if not run:
            return {}
        scoped_order = None
        full_order = getattr(run, "_full_party_order", None)
        if full_order:
            scoped_order = list(run.party_order)
            run.party_order = list(full_order)
        logs = None
        owners = None
        if run.node_data is not None:
            if run.player_count() <= 1:
                logs = run.node_data.pop("battle_logs", None)
                owners = run.node_data.pop("battle_log_owners", None)
        try:
            res = asdict(run)
        finally:
            if scoped_order is not None:
                run.party_order = scoped_order
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
                source_uid=b.get("source_uid", ""),
                persistent=bool(b.get("persistent", False))
            ))
        p_persistent_buffs = []
        for b in p_data.get("persistent_buffs", []):
            p_persistent_buffs.append(BuffState(
                id=b["id"],
                name=b["name"],
                stacks=b.get("stacks", 1),
                stacks2=b.get("stacks2", None),
                desc=b.get("desc", ""),
                source_uid=b.get("source_uid", ""),
                persistent=True
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
        bag_max_weight = int(p_data.get("bag_max_weight", BAG_DEFAULT_MAX_WEIGHT) or BAG_DEFAULT_MAX_WEIGHT)
        if bag_max_weight < BAG_DEFAULT_MAX_WEIGHT:
            bag_max_weight = BAG_DEFAULT_MAX_WEIGHT
        player = PlayerState(
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
            relic_counters={k: int(v) for k, v in (p_data.get("relic_counters", {}) or {}).items()},
            subclass=p_data.get("subclass", ""),
            selected_class=p_data.get("selected_class", "法师"),
            potions=p_data.get("potions", []),
            daily_blessing_id=p_data.get("daily_blessing_id", ""),
            downed=p_data.get("downed", False),
            is_mercenary=bool(p_data.get("is_mercenary", False)),
            mercenary_id=p_data.get("mercenary_id", ""),
            mercenary_owner=p_data.get("mercenary_owner", ""),
            mercenary_timing=p_data.get("mercenary_timing", "before"),
            sp=p_data.get("sp", 10),
            max_sp=p_data.get("max_sp", 10),
            persistent_buffs=p_persistent_buffs,
            quest_relics=list(p_data.get("quest_relics", []) or []),
            bag_items=list(p_data.get("bag_items", []) or []),
            bag_max_weight=bag_max_weight,
        )
        legacy_ex = int(p_data.get("exhaustion", 0) or 0)
        if not p_persistent_buffs and legacy_ex > 0:
            player.exhaustion = legacy_ex
        return player

    def _parse_enemy_list(self, enemies_data: list) -> list:
        enemies = []
        if not enemies_data:
            return enemies
        from .state import EnemyIntentState
        for ed in enemies_data:
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
        return enemies

    def _parse_floor_map(self, fm_data):
        if not fm_data or not isinstance(fm_data, dict):
            return None
        rooms = {}
        for coord, rdata in (fm_data.get("rooms") or {}).items():
            rooms[coord] = RoomState(
                coord=rdata.get("coord", coord),
                room_type=rdata.get("room_type", "empty"),
                explored=bool(rdata.get("explored", False)),
                cleared=bool(rdata.get("cleared", False)),
                locked=bool(rdata.get("locked", False)),
                obstacle_sp=int(rdata.get("obstacle_sp", 0) or 0),
                is_high_danger=bool(rdata.get("is_high_danger", False)),
                landmark_id=rdata.get("landmark_id", ""),
                secret_unlocked=bool(rdata.get("secret_unlocked", False)),
                shared_payload=dict(rdata.get("shared_payload") or {}),
                env_id=rdata.get("env_id", ""),
                obstacle_style=rdata.get("obstacle_style", ""),
                npcs=list(rdata.get("npcs") or []),
                items=list(rdata.get("items") or []),
                props=list(rdata.get("props") or []),
                interacted_props=list(rdata.get("interacted_props") or []),
                defeated_npcs=list(rdata.get("defeated_npcs") or []),
            )
        sessions = {}
        for sid, sdata in (fm_data.get("active_sessions") or {}).items():
            sessions[sid] = EncounterSession(
                session_id=sdata.get("session_id", sid),
                coord=sdata.get("coord", ""),
                node_type=sdata.get("node_type", "battle"),
                participants=list(sdata.get("participants") or []),
                enemies=self._parse_enemy_list(sdata.get("enemies") or []),
                node_data=dict(sdata.get("node_data") or {}),
                status=sdata.get("status", "active"),
            )
        return FloorMapState(
            floor_index=int(fm_data.get("floor_index", 1) or 1),
            width=int(fm_data.get("width", 8) or 8),
            height=int(fm_data.get("height", 6) or 6),
            rooms=rooms,
            revealed_coords=list(fm_data.get("revealed_coords") or []),
            player_coords=dict(fm_data.get("player_coords") or {}),
            active_sessions=sessions,
            player_session_map=dict(fm_data.get("player_session_map") or {}),
            boss_coord=fm_data.get("boss_coord", ""),
            secret_boss_coord=fm_data.get("secret_boss_coord", ""),
            ritual_coord=fm_data.get("ritual_coord", ""),
            ritual_protocol=fm_data.get("ritual_protocol", ""),
            secret_unlocked=bool(fm_data.get("secret_unlocked", False)),
            secret_clue_found=bool(fm_data.get("secret_clue_found", False)),
            floor_flags=dict(fm_data.get("floor_flags") or {}),
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
        enemies = self._parse_enemy_list(d.get("enemies") or [])
        floor_map = self._parse_floor_map(d.get("floor_map"))
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
            players=players,
            floor_map=floor_map,
        )
