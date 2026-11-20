from .base import EventOption
from ...core.world.enchant_flow import apply_forced_event_enchant
from ...data.event_data import EVENT_CONFIG
from ...data.locale_data import get_locale_text


class EnchantAltarEchoOption(EventOption, action="enchant_altar_echo", text=get_locale_text("i18n_enchantment.events.enchant_altar_opt_echo")):
    def _run_effect(self, run, engine) -> str:
        cfg = EVENT_CONFIG.get("enchant_altar", {})
        hp_loss = int(cfg.get("echo_hp_cost", 5))
        run.player.hp = max(1, run.player.hp - hp_loss)
        applied = apply_forced_event_enchant(run, "echo")
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        if applied is None:
            return get_locale_text("i18n_enchantment.events.enchant_altar_no_cards")
        before_name, after_name, _ = applied
        return get_locale_text(
            "i18n_enchantment.events.enchant_altar_echo_res",
            hp_loss=hp_loss,
            before_name=before_name,
            after_name=after_name,
        )


class EnchantAltarChaosOption(EventOption, action="enchant_altar_chaos", text=get_locale_text("i18n_enchantment.events.enchant_altar_opt_chaos")):
    def _run_effect(self, run, engine) -> str:
        cfg = EVENT_CONFIG.get("enchant_altar", {})
        gold_gain = int(cfg.get("chaos_gold", 35))
        applied = apply_forced_event_enchant(run)
        run.player.gold += gold_gain
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        if applied is None:
            return get_locale_text("i18n_enchantment.events.enchant_altar_no_cards")
        before_name, after_name, enchant_name = applied
        return get_locale_text(
            "i18n_enchantment.events.enchant_altar_chaos_res",
            before_name=before_name,
            enchant_name=enchant_name,
            after_name=after_name,
            gold=gold_gain,
        )


class EnchantAltarEscapeOption(EventOption, action="enchant_altar_escape", text=get_locale_text("i18n_enchantment.events.enchant_altar_opt_escape")):
    def _run_effect(self, run, engine) -> str:
        cfg = EVENT_CONFIG.get("enchant_altar", {})
        hp_loss = int(cfg.get("escape_hp_cost", 8))
        run.player.hp = max(1, run.player.hp - hp_loss)
        engine.enter_next_stage(run)
        engine.save_manager.save_save(run.user_id, run)
        return get_locale_text("i18n_enchantment.events.enchant_altar_escape_res", hp_loss=hp_loss)
