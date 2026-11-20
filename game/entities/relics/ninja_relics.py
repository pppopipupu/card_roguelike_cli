from ...data.locale_data import get_locale_text
from ..cards.ninja_base import add_ninja_buff, add_random_food_to_hand, change_lex_kela, has_ninja_tag
from .base import RelicImpl
from .registry import register_relic


@register_relic("lotus_box")
class LotusBoxRelic(RelicImpl):
    def on_battle_start(self, run, engine):
        change_lex_kela(engine, run, run.player, 2, reason="lotus_box")
        engine._log_event(run, get_locale_text("i18n_cards_ninja.lotus_box_trigger"))


@register_relic("xiang_piao_piao")
class XiangPiaoPiaoRelic(RelicImpl):
    def on_turn_start(self, event, run, engine):
        if not event.is_player:
            return
        change_lex_kela(engine, run, run.player, 2, reason="xiang_piao_piao")
        engine._log_event(run, get_locale_text("i18n_cards_ninja.xiang_piao_piao_trigger"))


@register_relic("kfc")
class KfcRelic(RelicImpl):
    def on_battle_start(self, run, engine):
        run.node_data[run.turn_key("kfc_foods", run.player)] = []

    def on_turn_start(self, event, run, engine):
        if not event.is_player:
            return
        turn_count = int(run.node_data.get("turn_count", 1) or 1)
        if turn_count % 3 == 0:
            key = run.turn_key("kfc_foods", run.player)
            eaten = list(run.node_data.get(key, []) or [])
            name = add_random_food_to_hand(engine, run, run.player, exclude=tuple(eaten))
            eaten.append(name)
            run.node_data[key] = eaten
            engine._log_event(run, get_locale_text("i18n_cards_ninja.kfc_trigger", name=name))


@register_relic("dim_dead_tree")
class DimDeadTreeRelic(RelicImpl):
    def on_turn_start(self, event, run, engine):
        if not event.is_player:
            return
        add_ninja_buff(engine, run.player, "free_ninjutsu", 1)
        engine._log_event(run, get_locale_text("i18n_cards_ninja.dim_dead_tree_trigger"))


@register_relic("reaper_hand")
class ReaperHandRelic(RelicImpl):
    def on_card_played(self, event, run, engine):
        if not has_ninja_tag(event.card, "hand"):
            return
        grid = engine.combat_resolver.summon_minion(
            run,
            "ninja_clone",
            get_locale_text("i18n_cards_ninja.clone_minion_name"),
            6,
            4,
            0,
        )
        if grid:
            engine._log_event(run, get_locale_text("i18n_cards_ninja.reaper_hand_summon", grid=grid))


@register_relic("machine_ninja")
class MachineNinjaRelic(RelicImpl):
    def on_turn_start(self, event, run, engine):
        if not event.is_player:
            return
        existing = next((b for b in run.player.buffs if getattr(b, "id", "") == "science_double"), None)
        if existing is not None:
            existing.stacks = 1
        else:
            add_ninja_buff(engine, run.player, "science_double", 1)
        engine._log_event(run, get_locale_text("i18n_cards_ninja.machine_ninja_trigger"))


@register_relic("sarira")
class SariraRelic(RelicImpl):
    pass


@register_relic("three_duuz")
class ThreeDuuzRelic(RelicImpl):
    def on_turn_start(self, event, run, engine):
        if event.is_player:
            run.node_data[run.turn_key("three_duuz_used", run.player)] = False

    def on_card_played(self, event, run, engine):
        if not has_ninja_tag(event.card, "ninjutsu"):
            return
        key = run.turn_key("three_duuz_used", run.player)
        if run.node_data.get(key):
            return
        run.node_data[key] = True
        engine.card_player.draw_cards(run.player, 2, run)
        engine._log_event(run, get_locale_text("i18n_cards_ninja.three_duuz_trigger"))


@register_relic("toilet_water")
class ToiletWaterRelic(RelicImpl):
    def on_battle_start(self, run, engine):
        run.node_data[run.turn_key("toilet_water_count", run.player)] = 2
