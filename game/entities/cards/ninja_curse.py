from ...data.text.locale_data import get_locale_text
from .ninja_base import NinjaCard, add_ninja_buff
from .registry import register_card


@register_card("ninja_i_see_you")
class NinjaISeeYouCard(NinjaCard):
    def on_turn_end_in_hand(self, event, card_state):
        run = event.run
        p = run.player
        add_ninja_buff(event.engine, p, "vulnerable", 1)
        event.engine._log_event(run, get_locale_text("i18n_cards_ninja.i_see_you_tick"))


@register_card("ninja_hamood_kill_all")
class NinjaHamoodKillAllCard(NinjaCard):
    def on_turn_end_in_hand(self, event, card_state):
        run = event.run
        p = run.player
        engine = event.engine
        humans = list(run.all_human_uids())
        n_players = max(1, len(humans))
        dmg = int("9" * (n_players + 1))
        if humans:
            for uid in humans:
                pl = run.players.get(uid)
                if pl is not None and not pl.downed and pl.hp > 0:
                    intangible = any(b.id == "intangible" and b.stacks > 0 for b in pl.buffs)
                    actual = 1 if intangible else dmg
                    pl.hp = max(0, pl.hp - actual)
                    if pl.hp <= 0:
                        from ...core.battle.party_battle import mark_downed
                        mark_downed(engine, run, pl)
        else:
            actual = 1 if any(b.id == "intangible" and b.stacks > 0 for b in p.buffs) else dmg
            p.hp = max(0, p.hp - actual)
        for e in run.enemies:
            if e.hp > 0:
                e.hp = max(0, e.hp - dmg)
        engine._log_event(run, get_locale_text("i18n_cards_ninja.hamood_doom", dmg=dmg))
