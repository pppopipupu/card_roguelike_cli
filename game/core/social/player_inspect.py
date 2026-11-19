from typing import Optional

from ...entities import get_relic_desc
from ...models.state import GameRun, PlayerState, UserStats
from ...renderer.formatters import format_buff_list, format_relic_name_with_counter
from ...renderer.menu import render_deck
from ..inventory.bag_service import (
    calc_bag_items_weight,
    format_weight,
    get_bag_max_weight,
    get_item_desc,
    get_item_display_name,
    get_item_rarity_label,
    get_item_weight,
)
from ..text.events import JoinedText, LocaleText, RenderedText, TextPayload
from ..world.open_world.loadout_service import OpenWorldLoadoutService
from ..world.presence import WorldPresenceService, active_service

VIEW_PARTS = {
    "deck": "deck",
    "card": "deck",
    "cards": "deck",
    "卡组": "deck",
    "牌组": "deck",
    "bag": "bag",
    "inventory": "bag",
    "背包": "bag",
    "行囊": "bag",
    "relic": "relic",
    "relics": "relic",
    "遗物": "relic",
}


def t(key: str, **params) -> LocaleText:
    return LocaleText(key=key, params=params)


def join(parts: list, separator: str = "\n") -> JoinedText:
    return JoinedText(parts=[part for part in parts if part is not None], separator=separator)


def _resolve_presence_target(
    presence: WorldPresenceService,
    uid: str,
    query: str,
    run: Optional[GameRun] = None,
) -> Optional[dict]:
    location = presence.resolve_location(uid, run=run)
    if location is None:
        return None
    world, coord = location
    raw = str(query or "").strip().lower()
    if not raw:
        return None
    entries = presence.players(world, coord=coord, exclude_uid=uid)
    for entry in sorted(entries, key=lambda item: len(str(item.get("name", ""))), reverse=True):
        names = {str(entry.get("name", "")), str(entry.get("player_id", ""))}
        for name in names:
            if name and raw == name.lower():
                return entry
    return None


class PlayerInspectService:
    def __init__(self, save_manager, world_social=None):
        self.save_manager = save_manager
        self.world_social = world_social

    def _presence(self) -> Optional[WorldPresenceService]:
        if self.world_social is not None:
            return self.world_social.presence
        return active_service()

    def resolve_target(self, uid: str, query: str, run: Optional[GameRun] = None) -> Optional[dict]:
        presence = self._presence()
        if presence is None:
            return None
        return _resolve_presence_target(presence, uid, query, run=run)

    def target_state(self, target_uid: str) -> tuple[PlayerState, UserStats]:
        stats = self.save_manager.load_stats(target_uid)
        run = self.save_manager.load_save(target_uid)
        if run is not None:
            player = run.players.get(target_uid) or run.player
            if player is not None:
                return player, stats
        player = OpenWorldLoadoutService.build_player_state(target_uid, stats)
        return player, stats

    def touch_target(self, uid: str, query: str, run: Optional[GameRun] = None) -> Optional[TextPayload]:
        target = self.resolve_target(uid, query, run=run)
        if target is None:
            return None
        target_uid = str(target.get("user_id", ""))
        player, stats = self.target_state(target_uid)
        return self.status_node(target, player, stats)

    def _class_text(self, stats: UserStats) -> tuple[str, str]:
        base = getattr(stats, "selected_class", "") or "-"
        sub = getattr(stats, "selected_subclass", "") or ""
        return base, sub

    def status_node(self, target: dict, player: PlayerState, stats: UserStats) -> JoinedText:
        name = str(target.get("name") or getattr(stats, "player_name", "") or "-")
        base, sub = self._class_text(stats)
        persistent = getattr(player, "persistent_buffs", None) or []
        battle_buffs = getattr(player, "buffs", None) or []
        persistent_text = (
            RenderedText(text=format_buff_list(persistent))
            if persistent
            else t("i18n_trade.status_none")
        )
        class_text: TextPayload = RenderedText(text=base)
        if sub:
            class_text = join([RenderedText(text=base), RenderedText(text=sub)], " / ")
        parts: list[TextPayload] = [
            t("i18n_trade.status_header", name=name),
            t("i18n_trade.status_class", class_text=class_text),
            t("i18n_trade.status_hp", hp=player.hp, max_hp=player.max_hp),
            t("i18n_trade.status_sp", sp=player.sp, max_sp=player.max_sp),
            t("i18n_trade.status_gold", gold=player.gold),
            t("i18n_trade.status_shield", shield=player.shield),
            t("i18n_trade.status_persistent", buffs=persistent_text),
        ]
        if battle_buffs:
            parts.append(t("i18n_trade.status_buffs", buffs=RenderedText(text=format_buff_list(battle_buffs))))
        parts.append(
            t(
                "i18n_trade.status_assets",
                deck=len(getattr(player, "deck", None) or []),
                relics=len(getattr(player, "relics", None) or []),
                items=len(getattr(player, "bag_items", None) or []),
            )
        )
        if getattr(player, "downed", False):
            parts.append(t("i18n_trade.status_downed"))
        parts.append(t("i18n_trade.status_hint"))
        return join(parts)

    def _relic_nodes(self, player: PlayerState) -> list[TextPayload]:
        relics = list(getattr(player, "relics", None) or [])
        if not relics:
            return [t("i18n_trade.view_relic_empty")]
        counters = getattr(player, "relic_counters", None) or {}
        return [
            t(
                "i18n_trade.view_relic_line",
                name=format_relic_name_with_counter(relic_id, counters),
                desc=get_relic_desc(relic_id),
            )
            for relic_id in relics
        ]

    def _bag_nodes(self, player: PlayerState) -> list[TextPayload]:
        items = list(getattr(player, "bag_items", None) or [])
        used = calc_bag_items_weight(items)
        nodes: list[TextPayload] = [
            t(
                "i18n_trade.view_bag_weight",
                used=format_weight(used),
                max=get_bag_max_weight(player),
            )
        ]
        if not items:
            nodes.append(t("i18n_trade.view_bag_empty"))
            return nodes
        counts = {}
        order = []
        for item_id in items:
            if item_id not in counts:
                counts[item_id] = 0
                order.append(item_id)
            counts[item_id] += 1
        for item_id in order:
            count = counts[item_id]
            key = "i18n_trade.view_bag_line_count" if count > 1 else "i18n_trade.view_bag_line"
            nodes.append(
                t(
                    key,
                    name=get_item_display_name(item_id),
                    rarity=get_item_rarity_label(item_id),
                    weight=format_weight(get_item_weight(item_id)),
                    count=count,
                    desc=get_item_desc(item_id),
                )
            )
        return nodes

    def inventory_node(self, target_uid: str, part: str = "") -> TextPayload:
        player, stats = self.target_state(target_uid)
        name = getattr(stats, "player_name", "") or target_uid
        tmp_run = GameRun(user_id=target_uid, node_type="town", player=player)
        sections: list[TextPayload] = [t("i18n_trade.view_header", name=name)]
        if part in ("", "deck"):
            sections.append(t("i18n_trade.view_deck_header", name=name))
            sections.append(RenderedText(text=render_deck(tmp_run)))
        if part in ("", "bag"):
            sections.append(t("i18n_trade.view_bag_header", name=name))
            sections.extend(self._bag_nodes(player))
        if part in ("", "relic"):
            sections.append(t("i18n_trade.view_relic_header", name=name))
            sections.extend(self._relic_nodes(player))
        sections.append(t("i18n_trade.view_hint", name=name))
        return join(sections)

    def view_part(self, raw: str) -> str:
        return VIEW_PARTS.get(str(raw or "").strip().lower(), "")


def touch_player_status(save_manager, uid: str, query: str, run: Optional[GameRun] = None) -> Optional[str]:
    service = PlayerInspectService(save_manager)
    node = service.touch_target(uid, query, run=run)
    if node is None:
        return None
    from ..text.pipeline import render_text_node

    return render_text_node(node)
