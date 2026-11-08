MARKET_CARDS = {
    "warrior_blood_fury",
    "neutral_power_word_pain",
    "warrior_shield_bash",
    "wizard_antimagic_field",
    "neutral_power_word_stun",
    "warrior_hell_raider",
    "wizard_prismatic_wall",
    "wizard_time_ravage",
    "neutral_power_word_kill",
    "neutral_plane_shift",
    "elf_archer_xiaomei"
}

MARKET_SHELF_CARDS = [
    "warrior_blood_fury",
    "neutral_power_word_pain",
    "warrior_shield_bash",
    "wizard_antimagic_field",
    "neutral_power_word_stun",
    "warrior_hell_raider",
    "wizard_prismatic_wall",
    "wizard_time_ravage",
    "neutral_power_word_kill",
    "neutral_plane_shift",
    "elf_archer_xiaomei"
]

CARD_PRICE_OVERRIDES = {
    "elf_archer_xiaomei": 500
}

def get_market_price(cid: str, card_obj=None) -> int:
    clean_cid = cid.split(":replay:")[0].split(":fragile:")[0]
    if clean_cid.endswith("+"):
        clean_cid = clean_cid[:-1]
    if clean_cid in CARD_PRICE_OVERRIDES:
        return CARD_PRICE_OVERRIDES[clean_cid]
    if card_obj is None:
        from .base import ALL_CARDS
        card_obj = ALL_CARDS.get(clean_cid)
    rarity = getattr(card_obj, "rarity", "common")
    if rarity == "common":
        return 100
    if rarity == "rare":
        return 300
    return 700

def is_card_available(cid: str, stats) -> bool:
    if not cid:
        return False
    clean_cid = cid.split(":replay:")[0].split(":fragile:")[0]
    if clean_cid.endswith("+"):
        clean_cid = clean_cid[:-1]
    if clean_cid in MARKET_CARDS:
        if not stats:
            return False
        unlocked = set(getattr(stats, "unlocked_new_cards", []) or []) | set(getattr(stats, "purchased_pool", []) or [])
        return clean_cid in unlocked
    return True
