class StatsTracker:
    KEY = "_stats_pending"

    @staticmethod
    def _buckets(run):
        if run is None:
            return None
        node_data = getattr(run, "node_data", None)
        if not isinstance(node_data, dict):
            return None
        pending = node_data.get(StatsTracker.KEY)
        if not isinstance(pending, dict):
            pending = {}
            node_data[StatsTracker.KEY] = pending
        damage = pending.get("damage")
        if not isinstance(damage, dict):
            damage = {}
            pending["damage"] = damage
        kills = pending.get("kills")
        if not isinstance(kills, dict):
            kills = {}
            pending["kills"] = kills
        return damage, kills

    @staticmethod
    def record_damage(run, uid, amount):
        if not uid:
            return
        try:
            amount = int(amount)
        except (TypeError, ValueError):
            return
        if amount <= 0:
            return
        buckets = StatsTracker._buckets(run)
        if buckets is None:
            return
        damage = buckets[0]
        damage[uid] = damage.get(uid, 0) + amount

    @staticmethod
    def record_kill(run, uid):
        if not uid:
            return
        buckets = StatsTracker._buckets(run)
        if buckets is None:
            return
        kills = buckets[1]
        kills[uid] = kills.get(uid, 0) + 1

    @staticmethod
    def flush(save_manager, run):
        if save_manager is None or run is None:
            return
        if not getattr(run, "user_id", ""):
            return
        node_data = getattr(run, "node_data", None)
        if not isinstance(node_data, dict):
            return
        pending = node_data.get(StatsTracker.KEY)
        if not isinstance(pending, dict):
            return
        damage = pending.get("damage")
        damage = damage if isinstance(damage, dict) else {}
        kills = pending.get("kills")
        kills = kills if isinstance(kills, dict) else {}
        uids = []
        for source in (damage, kills):
            for uid in source:
                if uid and uid not in uids:
                    uids.append(uid)
        for uid in uids:
            stats = save_manager.load_stats(uid)
            if stats is None:
                continue
            dmg = damage.get(uid, 0)
            if isinstance(dmg, int) and dmg > 0:
                stats.total_damage = getattr(stats, "total_damage", 0) + dmg
            kill_count = kills.get(uid, 0)
            if isinstance(kill_count, int) and kill_count > 0:
                stats.total_kills = getattr(stats, "total_kills", 0) + kill_count
            save_manager.save_stats(uid, stats)
        node_data.pop(StatsTracker.KEY, None)
