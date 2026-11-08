from .registry import CARD_CLASS_REGISTRY
import inspect

from . import neutral
from . import wizard
from . import legendary
from . import curse
from . import warrior

import copy

def _get_card_config():
    from ...data.neutral_card_data import NEUTRAL_CARD_CONFIG
    from ...data.wizard_card_data import WIZARD_CARD_CONFIG
    from ...data.warrior_card_data import WARRIOR_CARD_CONFIG
    cfg = {}
    cfg.update(NEUTRAL_CARD_CONFIG)
    cfg.update(WIZARD_CARD_CONFIG)
    cfg.update(WARRIOR_CARD_CONFIG)
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
            fragile_val = cfg.get("fragile", 0)
            if fragile_val > 0:
                from ...entities.tags import FragileTag
                inst.add_tag(FragileTag("fragile", fragile_val))
                if " (易碎 " not in inst.name:
                    inst.name = f"{inst.name} (易碎 {fragile_val})"
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
            for prop in ("base_dmg", "heal_amount", "shield_amount", "minion_hp", "minion_atk", "countdown", "amulet_desc"):
                if prop in up_cfg:
                    setattr(card, prop, up_cfg[prop])
            if " (易碎 " in card.name:
                parts = card.name.split(" (易碎 ")
                name_part = parts[0]
                fragile_part = " (易碎 " + parts[1]
                card.name = name_part + "+" + fragile_part
            else:
                if not card.name.endswith("+"):
                    card.name += "+"

        card.gems = list(card_state.gems)
        if card.gems:
            dmg_add = 0
            dmg_mul = 1
            shield_add = 0
            heal_add = 0
            ba_sub = 0
            for g in card.gems:
                if g == "gem_dmg_add_2":
                    dmg_add += 2
                elif g == "gem_dmg_mul_2":
                    dmg_mul *= 2
                elif g == "gem_dmg_mul_3":
                    dmg_mul *= 3
                elif g == "gem_shield_add_3":
                    shield_add += 3
                elif g == "gem_shield_add_8":
                    shield_add += 8
                elif g == "gem_heal_add_2":
                    heal_add += 2
                elif g == "gem_cost_ba_sub_1":
                    ba_sub += 1

            import re

            if dmg_add > 0 or dmg_mul > 1:
                state_data = {"has_dmg_text": False}
                def repl_dmg(match):
                    state_data["has_dmg_text"] = True
                    val = int(match.group(1))
                    return f"造成 {(val + dmg_add) * dmg_mul} 点"
                card.desc = re.sub(r"造成\s*(\d+)\s*点", repl_dmg, card.desc)
                if not state_data["has_dmg_text"] and dmg_add > 0:
                    final_fallback_dmg = dmg_add * dmg_mul
                    card.desc = card.desc + f"造成 {final_fallback_dmg} 点效果伤害。"

            if shield_add > 0:
                state_data_shield = {"has_shield_text": False}
                def repl_shield(match):
                    state_data_shield["has_shield_text"] = True
                    prefix = match.group(1)
                    val = int(match.group(2))
                    return f"{prefix} {val + shield_add} 点护盾"
                card.desc = re.sub(r"(获得|提供|产生)\s*(\d+)\s*点护盾", repl_shield, card.desc)
                if not state_data_shield["has_shield_text"]:
                    card.desc = card.desc + f"获得 {shield_add} 点护盾。"

            if heal_add > 0:
                state_data_heal = {"has_heal_text": False}
                def repl_heal(match):
                    state_data_heal["has_heal_text"] = True
                    prefix = match.group(1)
                    val = int(match.group(2))
                    return f"{prefix} {val + heal_add} 点生命"
                card.desc = re.sub(r"(回复|治疗)\s*(\d+)\s*点生命", repl_heal, card.desc)
                if not state_data_heal["has_heal_text"]:
                    card.desc = card.desc + f"回复 {heal_add} 点生命。"

            if ba_sub > 0:
                card.cost_ba = max(0, card.cost_ba - ba_sub)
                card.desc = card.desc + f"BA消耗减少 {ba_sub}。"

            for g in card.gems:
                if g == "gem_retain":
                    card.retain = True
                    if "保留。" not in card.desc:
                        if card.desc and not card.desc.endswith((".", "!", "。", "！")):
                            card.desc += "。"
                        card.desc += "保留。"
                elif g == "gem_vuln_1":
                    if "施加 1 层易伤" not in card.desc:
                        if card.desc and not card.desc.endswith((".", "!", "。", "！")):
                            card.desc += "。"
                        card.desc += "打出时对首个敌人施加 1 层易伤。"
                elif g == "gem_weak_2":
                    if "施加 2 层虚弱" not in card.desc:
                        if card.desc and not card.desc.endswith((".", "!", "。", "！")):
                            card.desc += "。"
                        card.desc += "打出时对首个敌人施加 2 层虚弱。"
                elif g == "gem_copy_1":
                    if "复制 1。" not in card.desc:
                        if card.desc and not card.desc.endswith((".", "!", "。", "！")):
                            card.desc += "。"
                        card.desc += "复制 1。"
                elif g == "gem_return_3":
                    if "返回 3。" not in card.desc:
                        if card.desc and not card.desc.endswith((".", "!", "。", "！")):
                            card.desc += "。"
                        card.desc += "返回 3。"
                elif g == "gem_return_5":
                    if "返回 5。" not in card.desc:
                        if card.desc and not card.desc.endswith((".", "!", "。", "！")):
                            card.desc += "。"
                        card.desc += "返回 5。"
                elif g == "gem_gain_a_1":
                    if "获得 1A" not in card.desc:
                        if card.desc and not card.desc.endswith((".", "!", "。", "！")):
                            card.desc += "。"
                        card.desc += "打出时获得 1A。"
                elif g == "gem_gain_a_1_ba_1":
                    if "获得 1A 1BA" not in card.desc:
                        if card.desc and not card.desc.endswith((".", "!", "。", "！")):
                            card.desc += "。"
                        card.desc += "打出时获得 1A 1BA。"

            from ...data.gem_data import GEM_CONFIG
            gem_descs = []
            for g in card.gems:
                if g in GEM_CONFIG:
                    gem_descs.append(f"<{GEM_CONFIG[g]['name']}>")
            if gem_descs:
                card.desc = card.desc + " （镶嵌：" + "，".join(gem_descs) + "）"

        if card_state.replay > 0:
            from ...entities.tags import ReplayTag
            card.add_tag(ReplayTag("replay", card_state.replay))
            import re
            clean_desc = re.sub(r"重放 \d+。", "", card.desc)
            if clean_desc.endswith("。") or clean_desc.endswith("！"):
                card.desc = clean_desc + f"重放 {card_state.replay}。"
            else:
                card.desc = clean_desc + f"。重放 {card_state.replay}。"

        if card_state.fragile > 0:
            from ...entities.tags import FragileTag
            card.add_tag(FragileTag("fragile", card_state.fragile))
            import re
            card.desc = re.sub(r"易碎 \d+。", f"易碎 {card_state.fragile}。", card.desc)
            if " (易碎 " in card.name:
                card.name = re.sub(r" \(易碎 \d+\)", f" (易碎 {card_state.fragile})", card.name)
            else:
                card.name = f"{card.name} (易碎 {card_state.fragile})"

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
            card.desc = card.desc + f" （魔力受损：效果降低 {penalty}）"

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
    fragile_val = cfg.get("fragile", 0)
    if fragile_val > 0:
        from ...entities.tags import FragileTag
        inst.add_tag(FragileTag("fragile", fragile_val))
        if " (易碎 " not in inst.name:
            inst.name = f"{inst.name} (易碎 {fragile_val})"
    ALL_CARDS[cid] = inst
