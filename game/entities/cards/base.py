from .registry import CARD_CLASS_REGISTRY
import inspect

from . import neutral
from . import wizard
from . import legendary
from . import curse
from . import warrior
from . import coop

import copy

from ...data.card_target_data import SELF_TARGET_SPELLS
from ...data.locale_data import get_locale_text

NUMERIC_CARD_FIELDS = (
    "base_dmg",
    "heal_amount",
    "shield_amount",
    "draw_count",
    "discard_count",
    "count",
    "hit_count",
    "gain_a",
    "gain_ba",
    "buff_stacks",
    "buff_turns",
    "hp_gain",
    "hp_loss",
    "self_hp_cost",
    "self_damage",
    "reflect_damage",
    "strength_gain",
    "multiplier",
    "action_gain",
    "bonus_action_gain",
    "curse_count",
    "hand_limit",
    "rally_threshold",
    "battlecry_damage",
    "ally_atk_bonus",
    "ally_hp_bonus",
    "minion_hp",
    "minion_atk",
    "token_hp",
    "token_atk",
    "countdown",
    "threshold",
    "fail_damage",
    "reduction",
    "replay_amount",
    "extra_turns",
    "hits",
    "dice_count",
    "die_size",
    "dice_threshold",
    "extra_true_damage",
    "burn_damage",
    "burn_turns",
    "stun_turns",
    "stun_multiplier",
    "crit_multiplier",
    "heal_ratio",
    "shield_ratio",
    "hp_threshold",
    "spell_damage_bonus",
    "damage_amount",
    "restore_amount",
    "bonus_damage",
    "gp_reward",
    "forbidden_stages",
    "max_count",
    "coef",
    "factor",
    "draw_divisor",
    "attack_actions",
    "effect_params",
)

GEM_DAMAGE_ADD = {
    "gem_dmg_add_2": 2,
}

GEM_DAMAGE_MUL = {
    "gem_dmg_mul_2": 2,
    "gem_dmg_mul_3": 3,
}

GEM_SHIELD_ADD = {
    "gem_shield_add_3": 3,
    "gem_shield_add_8": 8,
}

GEM_HEAL_ADD = {
    "gem_heal_add_2": 2,
}

GEM_BA_SUB = {
    "gem_cost_ba_sub_1": 1,
}

def _gem_effect_suffixes():
    return {
        "gem_retain": get_locale_text("i18n_card_runtime.cards.gem_effect.gem_retain"),
        "gem_vuln_1": get_locale_text("i18n_card_runtime.cards.gem_effect.gem_vuln_1"),
        "gem_weak_2": get_locale_text("i18n_card_runtime.cards.gem_effect.gem_weak_2"),
        "gem_copy_1": get_locale_text("i18n_card_runtime.cards.gem_effect.gem_copy_1"),
        "gem_return_3": get_locale_text("i18n_card_runtime.cards.gem_effect.gem_return_3"),
        "gem_return_5": get_locale_text("i18n_card_runtime.cards.gem_effect.gem_return_5"),
        "gem_gain_a_1": get_locale_text("i18n_card_runtime.cards.gem_effect.gem_gain_a_1"),
        "gem_gain_a_1_ba_1": get_locale_text("i18n_card_runtime.cards.gem_effect.gem_gain_a_1_ba_1"),
    }

def get_gem_numeric_modifiers(gems):
    dmg_add = 0
    dmg_mul = 1
    shield_add = 0
    heal_add = 0
    ba_sub = 0
    gain_a = 0
    gain_ba = 0
    for gem in gems or ():
        dmg_add += GEM_DAMAGE_ADD.get(gem, 0)
        dmg_mul *= GEM_DAMAGE_MUL.get(gem, 1)
        shield_add += GEM_SHIELD_ADD.get(gem, 0)
        heal_add += GEM_HEAL_ADD.get(gem, 0)
        ba_sub += GEM_BA_SUB.get(gem, 0)
        if gem == "gem_gain_a_1":
            gain_a += 1
        elif gem == "gem_gain_a_1_ba_1":
            gain_a += 1
            gain_ba += 1
    return {
        "dmg_add": dmg_add,
        "dmg_mul": dmg_mul,
        "shield_add": shield_add,
        "heal_add": heal_add,
        "ba_sub": ba_sub,
        "gain_a": gain_a,
        "gain_ba": gain_ba,
    }

def replace_structured_number(text, old_value, new_value, before_markers=(), after_markers=(), trim_after_space=False):
    if not text or old_value == new_value:
        return text
    old_token = str(old_value)
    search_from = 0
    while True:
        index = text.find(old_token, search_from)
        if index < 0:
            return text
        end = index + len(old_token)
        left_ok = index == 0 or not text[index - 1].isdigit()
        right_ok = end >= len(text) or not text[end].isdigit()
        if left_ok and right_ok:
            prefix = text[max(0, index - 12):index]
            suffix = text[end:end + 6]
            before_ok = not before_markers or any(marker in prefix for marker in before_markers)
            after_ok = not after_markers or any(marker in suffix for marker in after_markers)
            if before_ok and after_ok:
                replace_end = end
                if trim_after_space:
                    while replace_end < len(text) and text[replace_end].isspace():
                        replace_end += 1
                return text[:index] + str(new_value) + text[replace_end:]
        search_from = end

def append_card_suffix(desc, suffix):
    if not suffix:
        return desc
    if desc and not desc.endswith((".", "!", "。", "！")):
        sentence_period = get_locale_text("i18n_card_runtime.cards.sentence_period")
        desc = f"{desc}{sentence_period}"
    return f"{desc}{suffix}"

def replace_marker_number(desc, marker, value):
    marker_index = desc.find(marker)
    if marker_index < 0:
        return None
    cursor = marker_index + len(marker)
    while cursor < len(desc) and desc[cursor].isspace():
        cursor += 1
    start = cursor
    while cursor < len(desc) and desc[cursor].isdigit():
        cursor += 1
    if start == cursor:
        return None
    return f"{desc[:start]}{value}{desc[cursor:]}"

def add_fragile_marker(desc, fragile_val):
    if fragile_val <= 0:
        return desc
    fragile_label = get_locale_text("i18n_card_runtime.cards.fragile_label")
    if f"{fragile_label} {fragile_val}" in desc:
        return desc
    updated = replace_marker_number(desc, fragile_label, fragile_val)
    if updated is not None:
        return updated
    return append_card_suffix(desc, get_locale_text("i18n_card_runtime.cards.fragile_marker", value=fragile_val))

def add_replay_marker(desc, replay):
    if replay <= 0:
        return desc
    replay_label = get_locale_text("i18n_card_runtime.cards.replay_label")
    if f"{replay_label} {replay}" in desc:
        return desc
    updated = replace_marker_number(desc, replay_label, replay)
    if updated is not None:
        return updated
    return append_card_suffix(desc, get_locale_text("i18n_card_runtime.cards.replay_marker", value=replay))

def _get_card_config():
    from ...data.neutral_card_data import NEUTRAL_CARD_CONFIG
    from ...data.wizard_card_data import WIZARD_CARD_CONFIG
    from ...data.warrior_card_data import WARRIOR_CARD_CONFIG
    from ...data.coop_card_data import COOP_CARD_CONFIG
    cfg = {}
    cfg.update(NEUTRAL_CARD_CONFIG)
    cfg.update(WIZARD_CARD_CONFIG)
    cfg.update(WARRIOR_CARD_CONFIG)
    cfg.update(COOP_CARD_CONFIG)
    return cfg

class CardRegistryDict(dict):
    def _lazy_load_card(self, key):
        card_config = _get_card_config()
        if key in card_config:
            cfg = card_config[key]
            name = cfg["name"]
            color = cfg["color"]
            ctype = cfg["type"]
            cost_a = cfg["cost_a"]
            cost_ba = cfg["cost_ba"]
            desc = cfg["desc"]
            rarity = cfg.get("rarity", "common")
            exhaust = cfg.get("exhaust", False)
            fleeting = cfg.get("fleeting", False)
            agile = cfg.get("agile", False)
            retain = cfg.get("retain", False)

            from ...models.state import Card
            from .registry import CARD_CLASS_REGISTRY
            import inspect
            if key in CARD_CLASS_REGISTRY:
                cls, decorator_kwargs = CARD_CLASS_REGISTRY[key]
            else:
                cls = Card
                decorator_kwargs = {}

            inst_kwargs = {
                "id": key,
                "name": name,
                "color": color,
                "type": ctype,
                "cost_a": cost_a,
                "cost_ba": cost_ba,
                "desc": desc,
            }
            for prop in ("base_dmg", "heal_amount", "countdown", "amulet_desc", "minion_hp", "minion_atk", "exhaust", "damage_type"):
                if prop in cfg:
                    inst_kwargs[prop] = cfg[prop]
            inst_kwargs.update(decorator_kwargs)
            
            sig = inspect.signature(cls.__init__)
            has_kwargs = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
            if has_kwargs:
                filtered = inst_kwargs
            else:
                filtered = {k: v for k, v in inst_kwargs.items() if k in sig.parameters}
            
            inst = cls(**filtered)
            for prop in NUMERIC_CARD_FIELDS:
                if prop in cfg:
                    setattr(inst, prop, cfg[prop])
            base_id = key.split("+")[0]
            inst.target_type = cfg.get("target_type") or ("self" if cfg.get("id", base_id) in SELF_TARGET_SPELLS else "enemy")
            inst.rarity = rarity
            inst.exhaust = exhaust
            inst.fleeting = fleeting
            inst.agile = agile
            inst.retain = retain
            inst.innate = cfg.get("innate", False)
            inst.ethereal = cfg.get("ethereal", False)
            inst.unplayable = cfg.get("unplayable", False)
            inst.damage_type = cfg.get("damage_type", "effect")
            inst.instant_summon = cfg.get("instant_summon", False)
            inst.instant_summon_thresholds = tuple(cfg.get("instant_summon_thresholds", ()))
            inst.instant_summon_piles = tuple(cfg.get("instant_summon_piles", ()))
            inst.coop_only = cfg.get("coop_only", False)
            fragile_val = cfg.get("fragile", 0)
            if fragile_val > 0:
                from ...entities.tags import FragileTag
                inst.add_tag(FragileTag("fragile", fragile_val))
                inst.desc = add_fragile_marker(inst.desc, fragile_val)
            self[key] = inst
            return inst
        return None

    def __iter__(self):
        card_config = _get_card_config()
        for k in card_config.keys():
            if k not in self:
                self._lazy_load_card(k)
        return super().__iter__()

    def keys(self):
        card_config = _get_card_config()
        for k in card_config.keys():
            if k not in self:
                self._lazy_load_card(k)
        return super().keys()

    def values(self):
        card_config = _get_card_config()
        for k in card_config.keys():
            if k not in self:
                self._lazy_load_card(k)
        return super().values()

    def items(self):
        card_config = _get_card_config()
        for k in card_config.keys():
            if k not in self:
                self._lazy_load_card(k)
        return super().items()

    def __len__(self):
        card_config = _get_card_config()
        for k in card_config.keys():
            if k not in self:
                self._lazy_load_card(k)
        return super().__len__()

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def __getitem__(self, key):
        from ...models.state import CardState, _parse_old_cid
        if isinstance(key, str) and ":" not in key and not key.endswith("+"):
            if key not in self:
                self._lazy_load_card(key)
            if key not in self:
                raise KeyError(key)
            return super().__getitem__(key)
        if isinstance(key, str):
            card_state = _parse_old_cid(key)
        elif isinstance(key, dict):
            from ...models.state import ensure_card_state
            card_state = ensure_card_state(key)
        elif isinstance(key, CardState):
            card_state = key
        else:
            return super().__getitem__(key)

        base_key = card_state.id
        if base_key not in self:
            self._lazy_load_card(base_key)
        if base_key not in self:
            raise KeyError(key)

        base_card = super().__getitem__(base_key)
        import copy
        card = copy.copy(base_card)
        card.id = base_key
        card.tags = [copy.copy(t) for t in base_card.tags]

        if card_state.upgraded:
            card.upgraded = True
            from ...data.card_upgrade_data import CARD_UPGRADE_CONFIG
            up_cfg = CARD_UPGRADE_CONFIG.get(base_key, {})
            if "cost_a" in up_cfg:
                card.cost_a = up_cfg["cost_a"]
            if "cost_ba" in up_cfg:
                card.cost_ba = up_cfg["cost_ba"]
            if "desc" in up_cfg:
                card.desc = up_cfg["desc"]
            if "innate" in up_cfg:
                card.innate = up_cfg["innate"]
            if "exhaust" in up_cfg:
                card.exhaust = up_cfg["exhaust"]
            for prop in (*NUMERIC_CARD_FIELDS, "amulet_desc"):
                if prop in up_cfg:
                    setattr(card, prop, up_cfg[prop])
            if not card.name.endswith("+"):
                card.name += "+"

        card.gems = list(card_state.gems)
        if card.gems:
            modifiers = get_gem_numeric_modifiers(card.gems)
            dmg_add = modifiers["dmg_add"]
            dmg_mul = modifiers["dmg_mul"]
            shield_add = modifiers["shield_add"]
            heal_add = modifiers["heal_add"]
            ba_sub = modifiers["ba_sub"]

            if dmg_add > 0 or dmg_mul > 1:
                base_dmg = int(getattr(card, "base_dmg", 0) or 0)
                if base_dmg > 0:
                    final_dmg = (base_dmg + dmg_add) * dmg_mul
                    updated_desc = replace_structured_number(card.desc, base_dmg, final_dmg, ("造成",), ("点",))
                    if updated_desc != card.desc:
                        card.desc = updated_desc
                    elif dmg_add > 0 and "{base_dmg}" not in card.desc:
                        card.desc = append_card_suffix(card.desc, get_locale_text("i18n_card_runtime.cards.gem_damage_upgrade", damage=final_dmg))
                elif dmg_add > 0 and "{base_dmg}" not in card.desc:
                    final_fallback_dmg = dmg_add * dmg_mul
                    card.desc = append_card_suffix(card.desc, get_locale_text("i18n_card_runtime.cards.gem_damage_fallback", damage=final_fallback_dmg))

            if shield_add > 0:
                base_shield = int(getattr(card, "shield_amount", 0) or 0)
                if base_shield > 0:
                    final_shield = base_shield + shield_add
                    updated_desc = replace_structured_number(card.desc, base_shield, final_shield, ("获得", "提供", "产生"), ("点护盾",))
                    if updated_desc != card.desc:
                        card.desc = updated_desc
                    elif "{shield_amount}" not in card.desc:
                        card.desc = append_card_suffix(card.desc, get_locale_text("i18n_card_runtime.cards.gem_shield_upgrade", shield=final_shield))
                elif "{shield_amount}" not in card.desc:
                    card.desc = append_card_suffix(card.desc, get_locale_text("i18n_card_runtime.cards.gem_shield_gain", shield=shield_add))

            if heal_add > 0:
                base_heal = int(getattr(card, "heal_amount", 0) or 0)
                if base_heal > 0:
                    final_heal = base_heal + heal_add
                    updated_desc = replace_structured_number(card.desc, base_heal, final_heal, ("回复", "治疗", "恢复"), ("点生命",))
                    if updated_desc != card.desc:
                        card.desc = updated_desc
                    elif "{heal_amount}" not in card.desc:
                        card.desc = append_card_suffix(card.desc, get_locale_text("i18n_card_runtime.cards.gem_heal_upgrade", heal=final_heal))
                elif "{heal_amount}" not in card.desc:
                    card.desc = append_card_suffix(card.desc, get_locale_text("i18n_card_runtime.cards.gem_heal_gain", heal=heal_add))

            if ba_sub > 0:
                card.cost_ba = max(0, card.cost_ba - ba_sub)
                card.desc = append_card_suffix(card.desc, get_locale_text("i18n_card_runtime.cards.gem_ba_reduction", amount=ba_sub))

            gem_effect_suffixes = _gem_effect_suffixes()
            for g in card.gems:
                effect_suffix = gem_effect_suffixes.get(g)
                if not effect_suffix:
                    continue
                if g == "gem_retain":
                    card.retain = True
                effect_marker = effect_suffix.rstrip("。")
                if effect_marker not in card.desc:
                    card.desc = append_card_suffix(card.desc, effect_suffix)

            from ...data.gem_data import GEM_CONFIG
            gem_descs = []
            for g in card.gems:
                if g in GEM_CONFIG:
                    gem_descs.append(f"<{GEM_CONFIG[g]['name']}>")
            if gem_descs:
                gem_inlay_separator = get_locale_text("i18n_card_runtime.cards.gem_inlay_separator")
                card.desc = card.desc + get_locale_text("i18n_card_runtime.cards.gem_inlay", gems=gem_inlay_separator.join(gem_descs))

        if card_state.replay > 0:
            from ...entities.tags import ReplayTag
            card.add_tag(ReplayTag("replay", card_state.replay))
            card.desc = add_replay_marker(card.desc, card_state.replay)

        if card_state.fragile > 0:
            from ...entities.tags import FragileTag
            card.add_tag(FragileTag("fragile", card_state.fragile))
            card.desc = add_fragile_marker(card.desc, card_state.fragile)

        card.return_left = card_state.return_left
        card.no_copy = card_state.no_copy
        if card_state.no_copy:
            card.copy = 0

        if getattr(card_state, "power_penalty", 0) > 0:
            penalty = card_state.power_penalty
            if getattr(card, "base_dmg", 0) > 0:
                card.base_dmg = max(0, card.base_dmg - penalty)
            if getattr(card, "heal_amount", 0) > 0:
                card.heal_amount = max(0, card.heal_amount - penalty)
            if getattr(card, "shield_amount", 0) > 0:
                card.shield_amount = max(0, card.shield_amount - penalty)
            card.desc = card.desc + get_locale_text("i18n_card_runtime.cards.power_penalty", penalty=penalty)

        return card

    def __contains__(self, key):
        from ...models.state import CardState, _parse_old_cid
        if isinstance(key, str):
            card_state = _parse_old_cid(key)
        elif isinstance(key, dict):
            from ...models.state import ensure_card_state
            card_state = ensure_card_state(key)
        elif isinstance(key, CardState):
            card_state = key
        else:
            return super().__contains__(key)
        base_key = card_state.id
        if super().__contains__(base_key):
            return True
        card_config = _get_card_config()
        return base_key in card_config


ALL_CARDS = CardRegistryDict()

for cid, cfg in _get_card_config().items():
    name = cfg["name"]
    color = cfg["color"]
    ctype = cfg["type"]
    cost_a = cfg["cost_a"]
    cost_ba = cfg["cost_ba"]
    desc = cfg["desc"]
    rarity = cfg.get("rarity", "common")
    exhaust = cfg.get("exhaust", False)
    fleeting = cfg.get("fleeting", False)
    agile = cfg.get("agile", False)
    retain = cfg.get("retain", False)

    from ...models.state import Card
    if cid in CARD_CLASS_REGISTRY:
        cls, decorator_kwargs = CARD_CLASS_REGISTRY[cid]
    else:
        cls = Card
        decorator_kwargs = {}

    inst_kwargs = {
        "id": cid,
        "name": name,
        "color": color,
        "type": ctype,
        "cost_a": cost_a,
        "cost_ba": cost_ba,
        "desc": desc,
    }
    for key in ("base_dmg", "heal_amount", "countdown", "amulet_desc", "minion_hp", "minion_atk", "exhaust", "damage_type"):
        if key in cfg:
            inst_kwargs[key] = cfg[key]
    inst_kwargs.update(decorator_kwargs)
    
    sig = inspect.signature(cls.__init__)
    has_kwargs = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())
    if has_kwargs:
        filtered = inst_kwargs
    else:
        filtered = {k: v for k, v in inst_kwargs.items() if k in sig.parameters}
    inst = cls(**filtered)
    for prop in NUMERIC_CARD_FIELDS:
        if prop in cfg:
            setattr(inst, prop, cfg[prop])
    inst.target_type = cfg.get("target_type") or ("self" if cfg.get("id", cid) in SELF_TARGET_SPELLS else "enemy")
    inst.rarity = rarity
    inst.exhaust = exhaust
    inst.fleeting = fleeting
    inst.agile = agile
    inst.retain = retain
    inst.innate = cfg.get("innate", False)
    inst.ethereal = cfg.get("ethereal", False)
    inst.unplayable = cfg.get("unplayable", False)
    inst.damage_type = cfg.get("damage_type", "effect")
    inst.instant_summon = cfg.get("instant_summon", False)
    inst.instant_summon_thresholds = tuple(cfg.get("instant_summon_thresholds", ()))
    inst.instant_summon_piles = tuple(cfg.get("instant_summon_piles", ()))
    inst.coop_only = cfg.get("coop_only", False)
    fragile_val = cfg.get("fragile", 0)
    if fragile_val > 0:
        from ...entities.tags import FragileTag
        inst.add_tag(FragileTag("fragile", fragile_val))
        inst.desc = add_fragile_marker(inst.desc, fragile_val)
    ALL_CARDS[cid] = inst
