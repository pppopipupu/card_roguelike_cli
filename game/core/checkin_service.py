from datetime import datetime, timezone
from ..data.checkin_data import (
    CHECKIN_STAMP_REQUIRED_FALLBACK,
    CHECKIN_STAMPS_PER_CLAIM,
    COLLECTION_CARDS,
    COLLECTION_ORDER,
    DAILY_BLESSINGS,
)
from ..data.locale_data import get_locale_text
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
            return get_locale_text("i18n_social.checkin.claim_pending") + self._render_collection(stats)
        return get_locale_text("i18n_social.checkin.claim_done") + self._render_status(stats)

    def _stamp(self, user_id: str, stats, choice: str, claimed_now: bool) -> str:
        if not stats.checkin_pending_stamp:
            return get_locale_text("i18n_social.checkin.stamp_already") + self._render_status(stats)
        card_id = self._resolve_choice(choice)
        if not card_id:
            return get_locale_text("i18n_social.checkin.stamp_not_found") + self._render_collection(stats)
        config = COLLECTION_CARDS[card_id]
        stamps = getattr(stats, "collection_stamps", {}) or {}
        current = int(stamps.get(card_id, 0)) + CHECKIN_STAMPS_PER_CLAIM
        stamps[card_id] = current
        stats.collection_stamps = stamps
        stats.checkin_pending_stamp = False
        unlocked_now = False
        required = int(config.get("required", CHECKIN_STAMP_REQUIRED_FALLBACK))
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
        prefix = get_locale_text("i18n_social.checkin.stamp_prefix") if claimed_now else ""
        lines = [
            prefix
            + get_locale_text(
                "i18n_social.checkin.stamped",
                name=config["name"],
                count=CHECKIN_STAMPS_PER_CLAIM,
            ),
            get_locale_text("i18n_social.checkin.current", current=current, required=required),
        ]
        if unlocked_now:
            lines.append(
                get_locale_text(
                    "i18n_social.checkin.unlocked",
                    required=required,
                    name=config["name"],
                )
            )
        elif current < required:
            lines.append(
                get_locale_text(
                    "i18n_social.checkin.remaining",
                    remaining=required - current,
                    name=config["name"],
                )
            )
        else:
            lines.append(get_locale_text("i18n_social.checkin.already_unlocked", name=config["name"]))
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
            get_locale_text("i18n_social.checkin.render_claim_title"),
            get_locale_text(
                "i18n_social.checkin.render_claim_blessing",
                name=blessing.get("name", get_locale_text("i18n_social.checkin.unknown_blessing")),
            ),
            get_locale_text("i18n_social.checkin.desc_indent", desc=blessing.get("desc", "")),
            get_locale_text("i18n_social.checkin.render_claim_note"),
            "",
            get_locale_text("i18n_social.checkin.render_claim_choose"),
            self._render_collection(stats),
        ]
        return "\n".join(lines)

    def _render_collection(self, stats) -> str:
        lines = []
        stamps = getattr(stats, "collection_stamps", {}) or {}
        for idx, card_id in enumerate(COLLECTION_ORDER, 1):
            config = COLLECTION_CARDS[card_id]
            current = int(stamps.get(card_id, 0))
            required = int(config.get("required", CHECKIN_STAMP_REQUIRED_FALLBACK))
            status = (
                get_locale_text("i18n_social.checkin.collection_unlocked")
                if current >= required
                else get_locale_text(
                    "i18n_social.checkin.collection_progress",
                    current=current,
                    required=required,
                )
            )
            lines.append(
                get_locale_text(
                    "i18n_social.checkin.collection_entry",
                    index=idx,
                    name=config["name"],
                    status=status,
                )
            )
        lines.append(get_locale_text("i18n_social.checkin.collection_hint"))
        return "\n".join(lines)

    def _render_status(self, stats) -> str:
        blessing_id = getattr(stats, "daily_blessing", "")
        blessing = DAILY_BLESSINGS.get(blessing_id, {})
        lines = [
            get_locale_text(
                "i18n_social.checkin.status_last",
                date=getattr(stats, "last_checkin_date", "") or get_locale_text("i18n_social.common.none"),
            ),
            get_locale_text(
                "i18n_social.checkin.status_blessing",
                name=blessing.get("name", get_locale_text("i18n_social.common.none")),
            ),
        ]
        if blessing:
            lines.append(get_locale_text("i18n_social.checkin.desc_indent", desc=blessing.get("desc", "")))
        lines.append(get_locale_text("i18n_social.checkin.status_title"))
        stamps = getattr(stats, "collection_stamps", {}) or {}
        for card_id in COLLECTION_ORDER:
            config = COLLECTION_CARDS[card_id]
            current = int(stamps.get(card_id, 0))
            required = int(config.get("required", CHECKIN_STAMP_REQUIRED_FALLBACK))
            lines.append(
                get_locale_text(
                    "i18n_social.checkin.status_entry",
                    name=config["name"],
                    current=current,
                    required=required,
                )
            )
        return "\n".join(lines)
