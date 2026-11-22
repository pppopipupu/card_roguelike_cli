from ....data.entities.gem_data import GEM_CONFIG
from ....data.text.locale_data import get_locale_text
from ....models.events import CardPlayEvent, CardPostPlayEvent, CardPlayedEvent, CardTurnEndResolveEvent, DamageCalculateEvent, ShieldGainEvent, HealEvent
from ..event_bus import PRIORITY_MODIFIER_ADD


class GemTriggerHandler:
    """按 GEM_CONFIG 数值修饰当前打出卡牌的伤害、护盾与治疗。"""

    def __init__(self, event_bus, engine):
        self.engine = engine
        event_bus.subscribe(DamageCalculateEvent, self.on_damage_calculate, PRIORITY_MODIFIER_ADD + 10)
        event_bus.subscribe(ShieldGainEvent, self.on_shield_gain, PRIORITY_MODIFIER_ADD + 10)
        event_bus.subscribe(HealEvent, self.on_heal, PRIORITY_MODIFIER_ADD + 10)
        event_bus.subscribe(CardPlayEvent, self.on_card_play)
        event_bus.subscribe(CardPostPlayEvent, self.on_card_post_play)
        event_bus.subscribe(CardPlayedEvent, self.on_card_played)
        event_bus.subscribe(CardTurnEndResolveEvent, self.on_card_turn_end_resolve)

    def on_card_play(self, event):
        event.run.node_data["card_played_triggered_dmg"] = False
        event.run.node_data["card_played_triggered_shield"] = False
        event.run.node_data["card_played_triggered_heal"] = False

    @staticmethod
    def _playing_card(run):
        cid = run.node_data.get("current_playing_card_cid")
        if not cid:
            return None
        from ....entities.cards import ALL_CARDS
        return ALL_CARDS.get(cid)

    def _gems(self, card):
        if card is None:
            return []
        return list(getattr(card, "gems", []) or [])

    def on_damage_calculate(self, event):
        source = event.source
        player_source = (
            source in ("p0", "player", "effect")
            or source.startswith("player:")
            or (len(source) > 1 and source[0] in ("p", "a") and source[1:].isdigit())
        )
        if not player_source:
            return
        card = event.card or self._playing_card(event.run)
        gems = self._gems(card)
        if not gems:
            return
        added = 0
        multiplier = 1
        for gem_id in gems:
            cfg = GEM_CONFIG.get(gem_id, {})
            added += int(cfg.get("damage_add", 0))
            multiplier *= int(cfg.get("damage_multiplier", 1))
        if added or multiplier != 1:
            event.modified_damage = (event.modified_damage + added) * multiplier

    def on_shield_gain(self, event):
        if event.target != "p0":
            return
        gems = self._gems(self._playing_card(event.run))
        added = sum(int(GEM_CONFIG.get(gem_id, {}).get("shield_add", 0)) for gem_id in gems)
        if added:
            event.modified_amount += added

    def on_heal(self, event):
        if event.target != "p0" and not event.target.startswith("p"):
            return
        gems = self._gems(self._playing_card(event.run))
        added = sum(int(GEM_CONFIG.get(gem_id, {}).get("heal_add", 0)) for gem_id in gems)
        if added:
            event.amount += added

    def on_card_post_play(self, event):
        run = event.run
        card = event.card
        gems = self._gems(card)
        if not gems:
            return
        if any(int(GEM_CONFIG.get(g, {}).get("shield_add", 0)) > 0 for g in gems) and not run.node_data.get("card_played_triggered_shield", False):
            self.engine.combat_resolver.gain_shield(run, "p0", 0)
        if any(int(GEM_CONFIG.get(g, {}).get("heal_add", 0)) > 0 for g in gems) and not run.node_data.get("card_played_triggered_heal", False):
            self.engine.combat_resolver.heal_target(run, "p0", 0)
        if any(int(GEM_CONFIG.get(g, {}).get("damage_add", 0)) > 0 for g in gems) and not run.node_data.get("card_played_triggered_dmg", False):
            dmg_target = event.target
            if not dmg_target or not dmg_target.startswith("e"):
                dmg_target = self.engine._get_first_alive_enemy(run)
            if dmg_target and dmg_target != "0" and dmg_target != "e0":
                self.engine.combat_resolver.damage_target(
                    run,
                    dmg_target,
                    0,
                    source="p0",
                    damage_type="effect",
                    card=card,
                )

    def on_card_played(self, event):
        run = event.run
        p = run.player
        card = event.card
        gems = self._gems(card)
        if not gems:
            return
        for gem_id in gems:
            if gem_id == "gem_gain_a_1":
                p.actions += 1
                self.engine._log_event(run, get_locale_text("i18n_battle_core.gem_gain_a_log"))
            elif gem_id == "gem_gain_a_1_ba_1":
                p.actions += 1
                p.bonus_actions += 1
                self.engine._log_event(run, get_locale_text("i18n_battle_core.gem_gain_a_ba_log"))
            elif gem_id == "gem_burn_gold":
                gp_gain = GEM_CONFIG.get("gem_burn_gold", {}).get("gp_gain", 5)
                uid = getattr(p, "mercenary_owner", "") if getattr(p, "is_mercenary", False) else (run.uid_for(p) or run.user_id)
                if uid and getattr(self.engine, "save_manager", None):
                    stats = self.engine.save_manager.load_stats(uid)
                    stats.gp = int(getattr(stats, "gp", 0) or 0) + gp_gain
                    self.engine.save_manager.save_stats(uid, stats)
                self.engine._log_event(run, get_locale_text("i18n_battle_core.gem_burn_gold_log", gp=gp_gain))
            elif gem_id in ("gem_vuln_1", "gem_weak_2"):
                target = event.target
                if not target or not target.startswith("e"):
                    target = self.engine._get_first_alive_enemy(run)
                if not target or not target.startswith("e"):
                    continue
                try:
                    idx = int(target[1:]) - 1
                except ValueError:
                    idx = -1
                if idx < 0 or idx >= len(run.enemies):
                    continue
                if gem_id == "gem_vuln_1":
                    self.engine.combat_resolver.add_buff_to(run.enemies[idx], "vulnerable", get_locale_text("i18n_battle_core.buff_vulnerable_name"), get_locale_text("i18n_battle_core.buff_vulnerable_desc"), 1)
                    self.engine._log_event(run, get_locale_text("i18n_battle_core.gem_vulnerable_log", name=run.enemies[idx].name))
                else:
                    self.engine.combat_resolver.add_buff_to(run.enemies[idx], "weak", get_locale_text("i18n_battle_core.buff_weak_name"), get_locale_text("i18n_battle_core.buff_weak_desc"), 2)
                    self.engine._log_event(run, get_locale_text("i18n_battle_core.gem_weak_log", name=run.enemies[idx].name))

    def on_card_turn_end_resolve(self, event):
        if "gem_retain" in list(getattr(event.card_state, "gems", []) or []):
            event.action = "retain"
