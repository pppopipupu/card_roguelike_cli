from ....data.content.chaos_expansion_data import CHAOS_NPCS
from ....data.text.locale_data import get_locale_raw, get_locale_text

EXISTING_NPC_GREETING_KEYS = {
    "wandering_smith": "i18n_room_interact.dialog.smith_greetings",
    "smuggler_broker": "i18n_room_interact.dialog.broker_greetings",
    "lost_scholar": "i18n_room_interact.dialog.scholar_greetings",
    "wounded_scout": "i18n_room_interact.dialog.scout_greetings",
    "shrine_keeper": "i18n_room_interact.dialog.keeper_greetings",
}


def get_chaos_dialog_content(run, save_manager=None):
    return None


def handle_chaos_dialog_choice(map_engine, run, idx, close_fn, start_combat_fn, reveal_fn):
    return None
