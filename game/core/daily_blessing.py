import random
from ..data.checkin_data import DAILY_BLESSINGS
from ..data.locale_data import get_locale_text
from ..models.state import CardState
from ..models.events import BattleStartEvent, DamageCalculateEvent, CardPlayedEvent
from ..entities.cards.market import is_card_available, is_coop_only


def roll_daily_blessing() -> str:
    return random.choice(list(DAILY_BLESSINGS.keys()))


def get_daily_blessing(blessing_id: str):
    return DAILY_BLESSINGS.get(blessing_id)


def _pick_random_card(card_filter: str, stats):
    from ..entities.cards.base import ALL_CARDS
    candidates = []
    for cid, card in ALL_CARDS.items():
        if cid.endswith("+") or cid.startswith("curse_") or cid.startswith("duel_") or is_coop_only(cid):
            continue
        if not is_card_available(cid, stats):
            continue
        if card_filter == "rare_minion":
            if card.type == "minion" and getattr(card, "rarity", "common") == "rare":
                candidates.append(cid)
        elif card_filter == "rare":
            if getattr(card, "rarity", "common") == "rare":
                candidates.append(cid)
        elif card_filter == "zero_cost":
            if getattr(card, "cost_a", 1) == 0 and getattr(card, "cost_ba", 1) == 0 and not getattr(card, "unplayable", False):
                candidates.append(cid)
    if not candidates:
        candidates = [
            cid for cid, card in ALL_CARDS.items()
            if not cid.endswith("+")
            and not cid.startswith("curse_")
            and not cid.startswith("duel_")
            and not is_coop_only(cid)
            and is_card_available(cid, stats)
        ]
    return random.choice(candidates) if candidates else None


def apply_pending_blessing(run, stats) -> str:
    blessing_id = getattr(stats, "daily_blessing", "")
    config = DAILY_BLESSINGS.get(blessing_id)
    if not config:
        stats.daily_blessing = ""
        return ""
    run.node_data["daily_blessing_id"] = blessing_id
    p = run.player
    p.daily_blessing_id = blessing_id
    for effect in config.get("effects", []):
        effect_type = effect.get("type")
        if effect_type == "max_hp":
            value = int(effect.get("value", 0))
            p.max_hp += value
            p.hp += value
        elif effect_type == "gold":
            p.gold += int(effect.get("value", 0))
        elif effect_type == "add_random_card":
            cid = _pick_random_card(effect.get("filter", ""), stats)
            if cid:
                p.deck.append(CardState(id=cid))
                run.node_data.setdefault("daily_blessing_added_cards", []).append(cid)
        elif effect_type == "upgrade_random":
            candidates = [card for card in p.deck if not card.upgraded]
            if candidates:
                chosen = random.choice(candidates)
                chosen.upgraded = True
                run.node_data["daily_blessing_upgraded_card"] = chosen.id
    stats.daily_blessing = ""
    return blessing_id


class DailyBlessingHandler:
    def __init__(self, event_bus, engine):
        self.engine = engine
        event_bus.subscribe(BattleStartEvent, self.on_battle_start)
        event_bus.subscribe(DamageCalculateEvent, self.on_damage_calculate)
        event_bus.subscribe(CardPlayedEvent, self.on_card_played)

    def _effects(self, run):
        blessing_id = getattr(run.player, "daily_blessing_id", "") or run.node_data.get("daily_blessing_id", "")
        config = DAILY_BLESSINGS.get(blessing_id, {})
        return config.get("effects", [])

    def on_battle_start(self, event):
        run = event.run
        p = run.player
        for effect in self._effects(run):
            effect_type = effect.get("type")
            if effect_type == "battle_shield":
                p.shield += int(effect.get("value", 0))
            elif effect_type == "battle_actions":
                p.actions += int(effect.get("value", 0))
            elif effect_type == "battle_bonus_actions":
                p.bonus_actions += int(effect.get("value", 0))
            elif effect_type == "battle_draw":
                self.engine._draw_cards(p, int(effect.get("value", 0)), run)
            elif effect_type == "battle_buff":
                self.engine._add_buff_to(
                    p,
                    effect.get("buff_id", ""),
                    effect.get("buff_name", ""),
                    effect.get("buff_desc", ""),
                    int(effect.get("stacks", 1)),
                )
            elif effect_type == "first_exhaust_draw":
                run.node_data["daily_first_exhaust_used"] = False

    def on_damage_calculate(self, event):
        if event.source != "p0" and not event.source.startswith("p"):
            return
        for effect in self._effects(event.run):
            effect_type = effect.get("type")
            if effect_type == "damage_type_bonus":
                if event.damage_type == effect.get("damage_type"):
                    event.modified_damage += int(effect.get("value", 0))
            elif effect_type == "card_name_bonus":
                if event.card and effect.get("keyword", "") in event.card.name:
                    event.modified_damage += int(effect.get("value", 0))

    def on_card_played(self, event):
        for effect in self._effects(event.run):
            if effect.get("type") != "first_exhaust_draw":
                continue
            if event.run.node_data.get("daily_first_exhaust_used", False):
                continue
            if not getattr(event.card, "exhaust", False):
                continue
            event.run.node_data["daily_first_exhaust_used"] = True
            draw_count = int(effect.get("draw", 0))
            action_count = int(effect.get("actions", 0))
            if draw_count > 0:
                self.engine._draw_cards(event.run.player, draw_count, event.run)
            if action_count > 0:
                event.run.player.actions += action_count
            self.engine._log_event(
                event.run,
                get_locale_text(
                    "i18n_social.daily_blessing.first_exhaust_log",
                    draw_count=draw_count,
                    action_count=action_count,
                ),
            )
