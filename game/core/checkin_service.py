from datetime import datetime, timezone
from ..data.checkin_data import COLLECTION_CARDS, COLLECTION_ORDER, DAILY_BLESSINGS
from .daily_blessing import roll_daily_blessing


class CheckinService:
    def __init__(self, save_manager):
        self.save_manager = save_manager

    def utc_today(self, now=None) -> str:
        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        return current.astimezone(timezone.utc).strftime("%Y-%m-%d")

    def claim(self, user_id: str, choice=None, now=None) -> str:
        stats = self.save_manager.load_stats(user_id)
        today = self.utc_today(now)
        claimed_now = False
        if stats.last_checkin_date != today:
            stats.last_checkin_date = today
            stats.daily_blessing = roll_daily_blessing()
            stats.checkin_pending_stamp = True
            claimed_now = True
            self.save_manager.save_stats(user_id, stats)
        if choice is not None and str(choice).strip():
            return self._stamp(user_id, stats, str(choice).strip(), claimed_now)
        if claimed_now:
            return self._render_claim(stats)
        if stats.checkin_pending_stamp:
            return "今日已签到，请选择一张集换卡盖章：\n" + self._render_collection(stats)
        return "今日已签到。\n" + self._render_status(stats)

    def _stamp(self, user_id: str, stats, choice: str, claimed_now: bool) -> str:
        if not stats.checkin_pending_stamp:
            return "今日已签到，且今日的集换章已经盖过了。\n" + self._render_status(stats)
        card_id = self._resolve_choice(choice)
        if not card_id:
            return "❌ 未找到该集换卡。请重新选择：\n" + self._render_collection(stats)
        config = COLLECTION_CARDS[card_id]
        stamps = getattr(stats, "collection_stamps", {}) or {}
        current = int(stamps.get(card_id, 0)) + 1
        stamps[card_id] = current
        stats.collection_stamps = stamps
        stats.checkin_pending_stamp = False
        unlocked_now = False
        required = int(config.get("required", 1))
        if current >= required:
            unlock_card = config.get("unlock_card", card_id)
            unlocked = list(getattr(stats, "unlocked_new_cards", []) or [])
            if unlock_card not in unlocked:
                unlocked.append(unlock_card)
                stats.unlocked_new_cards = unlocked
                purchased = list(getattr(stats, "purchased_pool", []) or [])
                if unlock_card not in purchased:
                    purchased.append(unlock_card)
                stats.purchased_pool = purchased
                unlocked_now = True
        self.save_manager.save_stats(user_id, stats)
        prefix = "今日签到完成。\n" if claimed_now else ""
        lines = [
            prefix + f"🏷️ 你为【{config['name']}】盖上了 1 枚集换章。",
            f"当前集换章：{current}/{required}",
        ]
        if unlocked_now:
            lines.append(f"🎉 集换章达到 {required} 枚，已解锁【{config['name']}】！下一局初始牌组将带入该卡。")
        elif current < required:
            lines.append(f"还需 {required - current} 枚集换章解锁【{config['name']}】。")
        else:
            lines.append(f"【{config['name']}】已经解锁。")
        lines.append("")
        lines.append(self._render_status(stats))
        return "\n".join(lines)

    def _resolve_choice(self, choice: str):
        lowered = choice.lower()
        if lowered.isdigit():
            idx = int(lowered) - 1
            if 0 <= idx < len(COLLECTION_ORDER):
                return COLLECTION_ORDER[idx]
            return None
        for card_id in COLLECTION_ORDER:
            config = COLLECTION_CARDS[card_id]
            if choice == card_id or choice == config.get("name"):
                return card_id
            if lowered == card_id.lower() or lowered == config.get("name", "").lower():
                return card_id
        return None

    def _render_claim(self, stats) -> str:
        blessing_id = getattr(stats, "daily_blessing", "")
        blessing = DAILY_BLESSINGS.get(blessing_id, {})
        lines = [
            "📅 今日签到成功！",
            f"🌙 每日祝福：{blessing.get('name', '未知祝福')}",
            f"   {blessing.get('desc', '')}",
            "   该祝福只会在你下一局新游戏中生效，且只保留最新一次签到结果。",
            "",
            "请选择一张集换卡盖上今日的集换章：",
            self._render_collection(stats),
        ]
        return "\n".join(lines)

    def _render_collection(self, stats) -> str:
        lines = []
        stamps = getattr(stats, "collection_stamps", {}) or {}
        for idx, card_id in enumerate(COLLECTION_ORDER, 1):
            config = COLLECTION_CARDS[card_id]
            current = int(stamps.get(card_id, 0))
            required = int(config.get("required", 1))
            status = "已解锁" if current >= required else f"{current}/{required}"
            lines.append(f" {idx}. 【{config['name']}】 集换章：{status}")
        lines.append("输入 签到 <序号|卡牌名> 盖章。")
        return "\n".join(lines)

    def _render_status(self, stats) -> str:
        blessing_id = getattr(stats, "daily_blessing", "")
        blessing = DAILY_BLESSINGS.get(blessing_id, {})
        lines = [
            f"📅 上次签到：{getattr(stats, 'last_checkin_date', '') or '无'}",
            f"🌙 待生效每日祝福：{blessing.get('name', '无')}",
        ]
        if blessing:
            lines.append(f"   {blessing.get('desc', '')}")
        lines.append("🏷️ 集换章：")
        stamps = getattr(stats, "collection_stamps", {}) or {}
        for card_id in COLLECTION_ORDER:
            config = COLLECTION_CARDS[card_id]
            current = int(stamps.get(card_id, 0))
            required = int(config.get("required", 1))
            lines.append(f"   【{config['name']}】 {current}/{required}")
        return "\n".join(lines)
