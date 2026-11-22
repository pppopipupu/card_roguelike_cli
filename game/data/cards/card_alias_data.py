CARD_ID_ALIASES = {
    "curse_pain": "curse_agony",
}

def resolve_card_id(card_id: str) -> str:
    return CARD_ID_ALIASES.get(card_id, card_id)
