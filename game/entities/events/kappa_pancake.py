from .base import EventOption
from ...core.inventory.relic_service import grant_relic
from ...core.party.coordinator import finish_player_node
from ...data.text.locale_data import get_locale_text
from ...data.world.event_data import EVENT_CONFIG
from ...entities import ALL_CARDS
from ...models.state import CardState
from ...renderer.menu import get_card_cost_str


def _render_current_event(run) -> str:
    from ...renderer import GameRenderer
    return GameRenderer.render_game(run)


def _advance_kappa_step2(run, engine, core: str) -> str:
    run.node_data["kappa_core"] = core
    run.node_data["description"] = get_locale_text("i18n_kappa_pancake.kappa.step2_desc")
    run.node_data["options"] = [
        {"text": get_locale_text("i18n_kappa_pancake.kappa.opt_mod_poison"), "action": "kappa_mod_poison"},
        {"text": get_locale_text("i18n_kappa_pancake.kappa.opt_mod_draw"), "action": "kappa_mod_draw"},
        {"text": get_locale_text("i18n_kappa_pancake.kappa.opt_mod_armor"), "action": "kappa_mod_armor"},
    ]
    engine.save_manager.save_save(run.user_id, run)
    return _render_current_event(run)


def _advance_kappa_step3(run, engine, mod: str) -> str:
    run.node_data["kappa_mod"] = mod
    run.node_data["description"] = get_locale_text("i18n_kappa_pancake.kappa.step3_desc")
    run.node_data["options"] = [
        {"text": get_locale_text("i18n_kappa_pancake.kappa.opt_power_light"), "action": "kappa_power_light"},
        {"text": get_locale_text("i18n_kappa_pancake.kappa.opt_power_std"), "action": "kappa_power_std"},
        {"text": get_locale_text("i18n_kappa_pancake.kappa.opt_power_overload"), "action": "kappa_power_overload"},
    ]
    engine.save_manager.save_save(run.user_id, run)
    return _render_current_event(run)


def _finish_kappa_device(run, engine, power: str) -> str:
    core = str(run.node_data.get("kappa_core") or "arc")
    mod = str(run.node_data.get("kappa_mod") or "draw")
    spec = f"{core}|{mod}|{power}"
    c_state = CardState(id="science_device", custom_spec=spec)
    run.player.deck.append(c_state)
    card_obj = ALL_CARDS[c_state]
    msg = get_locale_text(
        "i18n_kappa_pancake.kappa.res_done",
        name=card_obj.name,
        cost=get_card_cost_str(card_obj),
        desc=card_obj.desc,
    )
    return finish_player_node(engine.save_manager, engine, run, run.user_id, msg)


class KappaCoreArcOption(EventOption, action="kappa_core_arc"):
    def _run_effect(self, run, engine) -> str:
        return _advance_kappa_step2(run, engine, "arc")


class KappaCoreShieldOption(EventOption, action="kappa_core_shield"):
    def _run_effect(self, run, engine) -> str:
        return _advance_kappa_step2(run, engine, "shield")


class KappaCorePrismOption(EventOption, action="kappa_core_prism"):
    def _run_effect(self, run, engine) -> str:
        return _advance_kappa_step2(run, engine, "prism")


class KappaLeaveOption(EventOption, action="kappa_leave"):
    def _run_effect(self, run, engine) -> str:
        msg = get_locale_text("i18n_kappa_pancake.kappa.res_leave")
        return finish_player_node(engine.save_manager, engine, run, run.user_id, msg)


class KappaModPoisonOption(EventOption, action="kappa_mod_poison"):
    def _run_effect(self, run, engine) -> str:
        return _advance_kappa_step3(run, engine, "poison")


class KappaModDrawOption(EventOption, action="kappa_mod_draw"):
    def _run_effect(self, run, engine) -> str:
        return _advance_kappa_step3(run, engine, "draw")


class KappaModArmorOption(EventOption, action="kappa_mod_armor"):
    def _run_effect(self, run, engine) -> str:
        return _advance_kappa_step3(run, engine, "armor")


class KappaPowerLightOption(EventOption, action="kappa_power_light"):
    def _run_effect(self, run, engine) -> str:
        return _finish_kappa_device(run, engine, "light")


class KappaPowerStdOption(EventOption, action="kappa_power_std"):
    def _run_effect(self, run, engine) -> str:
        return _finish_kappa_device(run, engine, "std")


class KappaPowerOverloadOption(EventOption, action="kappa_power_overload"):
    def _run_effect(self, run, engine) -> str:
        return _finish_kappa_device(run, engine, "overload")


class PancakePayGoldOption(EventOption, action="pancake_pay_gold"):
    def _run_effect(self, run, engine) -> str:
        cfg = EVENT_CONFIG.get("pancake_stack_event", {})
        gold_cost = int(cfg.get("gold_cost", 65))
        if run.player.gold < gold_cost:
            return get_locale_text("i18n_kappa_pancake.pancake.err_no_gold")
        run.player.gold -= gold_cost
        grant_relic(run.player, "pancake_stack")
        msg = get_locale_text("i18n_kappa_pancake.pancake.res_pay_gold", gold=gold_cost)
        return finish_player_node(engine.save_manager, engine, run, run.user_id, msg)


class PancakePayHpOption(EventOption, action="pancake_pay_hp"):
    def _run_effect(self, run, engine) -> str:
        cfg = EVENT_CONFIG.get("pancake_stack_event", {})
        hp_cost = int(cfg.get("hp_cost", 10))
        run.player.hp = max(1, run.player.hp - hp_cost)
        grant_relic(run.player, "pancake_stack")
        msg = get_locale_text("i18n_kappa_pancake.pancake.res_pay_hp", hp=hp_cost)
        return finish_player_node(engine.save_manager, engine, run, run.user_id, msg)


class PancakeLeaveOption(EventOption, action="pancake_leave"):
    def _run_effect(self, run, engine) -> str:
        msg = get_locale_text("i18n_kappa_pancake.pancake.res_leave")
        return finish_player_node(engine.save_manager, engine, run, run.user_id, msg)
