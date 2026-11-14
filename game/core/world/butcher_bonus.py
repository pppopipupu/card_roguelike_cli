from ...data.temple_config import BUTCHER_BONUS_CARDS


def apply_butcher_bonus(p_state, flags):
    if not flags.get("butcher_path"):
        return
    p_state.deck.extend(BUTCHER_BONUS_CARDS)
    p_state.draw_pile.extend(BUTCHER_BONUS_CARDS)
