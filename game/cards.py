from .entities.cards import ALL_CARDS
from .entities.minions import MINION_SKILLS
from .data.cards.card_data import CARD_CONFIG

def resolve_card_id(card_input: str) -> str | None:
    card_input = card_input.strip()
    if not card_input:
        return None
    if card_input.endswith("+"):
        card_input = card_input[:-1]
    if card_input in ALL_CARDS:
        return card_input
    card_input_lower = card_input.lower()
    for cid in list(ALL_CARDS.keys()):
        if cid.lower() == card_input_lower:
            return cid
    for cid, cfg in CARD_CONFIG.items():
        name = cfg.get("name", "")
        if card_input == name or card_input_lower == name.lower():
            return cid
    return None
