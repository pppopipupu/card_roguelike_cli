from ...models.state import Card
from .registry import register_card
from ...data.entities.buffs.buff_data import BUFF_CONFIG
from ...data.text.locale_data import get_locale_text
from ..tags import ReplayTag

KAPPA_CORE_STATS: dict[str, dict] = {
    "arc": {"dmg": 8, "upg_dmg": 3, "damage_type": "lightning", "target_type": "enemy"},
    "shield": {"shield": 9, "upg_shield": 3, "target_type": "self"},
    "prism": {"dmg": 5, "upg_dmg": 2, "draw": 1, "damage_type": "radiant", "aoe": True, "target_type": "self"},
}

KAPPA_MOD_STATS: dict[str, dict] = {
    "poison": {"poison": 3, "upg_poison": 1},
    "draw": {"draw": 2, "upg_draw": 1},
    "armor": {"shield": 6, "upg_shield": 2, "heal": 3, "upg_heal": 1},
}

KAPPA_POWER_STATS: dict[str, dict] = {
    "light": {"cost_a": 0, "exhaust": True, "replay": 0, "scale": 1.0},
    "std": {"cost_a": 1, "exhaust": False, "replay": 0, "scale": 1.0},
    "overload": {"cost_a": 2, "exhaust": False, "replay": 1, "scale": 1.5},
}


def parse_science_spec(spec: str) -> tuple[str, str, str]:
    parts = [p.strip() for p in str(spec or "").split("|") if p.strip()]
    core = parts[0] if len(parts) > 0 and parts[0] in KAPPA_CORE_STATS else "arc"
    mod = parts[1] if len(parts) > 1 and parts[1] in KAPPA_MOD_STATS else "draw"
    power = parts[2] if len(parts) > 2 and parts[2] in KAPPA_POWER_STATS else "std"
    return core, mod, power


def compute_science_numbers(spec: str, upgraded: bool = False) -> dict:
    core, mod, power = parse_science_spec(spec)
    c_cfg = KAPPA_CORE_STATS[core]
    m_cfg = KAPPA_MOD_STATS[mod]
    p_cfg = KAPPA_POWER_STATS[power]
    scale = float(p_cfg["scale"])
    dmg = int(c_cfg.get("dmg", 0)) + (int(c_cfg.get("upg_dmg", 0)) if upgraded else 0)
    if dmg > 0:
        dmg = max(1, int(round(dmg * scale)))
    core_shield = int(c_cfg.get("shield", 0)) + (int(c_cfg.get("upg_shield", 0)) if upgraded else 0)
    mod_shield = int(m_cfg.get("shield", 0)) + (int(m_cfg.get("upg_shield", 0)) if upgraded else 0)
    if core_shield > 0:
        core_shield = max(1, int(round(core_shield * scale)))
    if mod_shield > 0:
        mod_shield = max(1, int(round(mod_shield * scale)))
    heal = int(m_cfg.get("heal", 0)) + (int(m_cfg.get("upg_heal", 0)) if upgraded else 0)
    poison = int(m_cfg.get("poison", 0)) + (int(m_cfg.get("upg_poison", 0)) if upgraded else 0)
    core_draw = int(c_cfg.get("draw", 0))
    mod_draw = int(m_cfg.get("draw", 0)) + (int(m_cfg.get("upg_draw", 0)) if upgraded else 0)
    target_type = "enemy" if (c_cfg.get("target_type") == "enemy" or (mod == "poison" and not c_cfg.get("aoe"))) else "self"
    return {
        "core": core,
        "mod": mod,
        "power": power,
        "cost_a": int(p_cfg["cost_a"]),
        "exhaust": bool(p_cfg["exhaust"]),
        "replay": int(p_cfg["replay"]),
        "dmg": dmg,
        "damage_type": str(c_cfg.get("damage_type", "lightning")),
        "aoe": bool(c_cfg.get("aoe", False)),
        "core_shield": core_shield,
        "mod_shield": mod_shield,
        "heal": heal,
        "poison": poison,
        "core_draw": core_draw,
        "mod_draw": mod_draw,
        "target_type": target_type,
    }


def format_science_desc(spec: str, upgraded: bool = False) -> str:
    n = compute_science_numbers(spec, upgraded)
    frags: list[str] = []
    if n["core"] == "arc":
        frags.append(get_locale_text("i18n_kappa_pancake.kappa.card_frag_arc", dmg=n["dmg"]))
    elif n["core"] == "shield":
        frags.append(get_locale_text("i18n_kappa_pancake.kappa.card_frag_shield", shield=n["core_shield"]))
    else:
        frags.append(get_locale_text("i18n_kappa_pancake.kappa.card_frag_prism", dmg=n["dmg"], draw=n["core_draw"]))
    if n["mod"] == "poison":
        key = "i18n_kappa_pancake.kappa.card_frag_poison_all" if n["aoe"] else "i18n_kappa_pancake.kappa.card_frag_poison_single"
        frags.append(get_locale_text(key, poison=n["poison"]))
    elif n["mod"] == "draw":
        frags.append(get_locale_text("i18n_kappa_pancake.kappa.card_frag_draw", draw=n["mod_draw"]))
    elif n["mod"] == "armor":
        frags.append(get_locale_text("i18n_kappa_pancake.kappa.card_frag_armor", shield=n["mod_shield"], heal=n["heal"]))
    if n["exhaust"]:
        frags.append(get_locale_text("i18n_kappa_pancake.kappa.card_frag_exhaust"))
    sep = get_locale_text("i18n_kappa_pancake.kappa.card_sep")
    period = get_locale_text("i18n_kappa_pancake.kappa.card_period")
    desc = f"{sep.join(frags)}{period}"
    if n["replay"] > 0:
        from .base import add_replay_marker
        desc = add_replay_marker(desc, n["replay"])
    return desc


@register_card("science_device")
class ScienceDeviceCard(Card):
    def apply_card_state(self, card_state) -> None:
        spec = str(getattr(card_state, "custom_spec", "") or "").strip()
        if not spec:
            return
        upgraded = bool(getattr(card_state, "upgraded", False))
        n = compute_science_numbers(spec, upgraded)
        self.cost_a = n["cost_a"]
        self.cost_ba = 0
        self.exhaust = n["exhaust"]
        self.base_dmg = n["dmg"]
        self.damage_type = n["damage_type"]
        self.shield_amount = n["core_shield"] + n["mod_shield"]
        self.heal_amount = n["heal"]
        self.target_type = n["target_type"]
        self.desc = format_science_desc(spec, upgraded)
        if n["replay"] > 0:
            self.add_tag(ReplayTag("replay", n["replay"]))

    def execute(self, run, target, engine) -> str:
        c_state = getattr(self, "card_state", None)
        spec = str(getattr(c_state, "custom_spec", "") or "")
        upgraded = bool(getattr(self, "upgraded", False))
        n = compute_science_numbers(spec, upgraded)
        cr = engine.combat_resolver
        dmg = int(getattr(self, "base_dmg", n["dmg"]) or 0)
        if n["core"] == "arc" and dmg > 0:
            t_ref = target if (target and str(target).startswith("e")) else engine._get_first_alive_enemy(run)
            if t_ref:
                cr.damage_target(run, t_ref, dmg, source="p0", damage_type=n["damage_type"], card=self)
        elif n["core"] == "prism":
            if dmg > 0:
                for i, e in enumerate(run.enemies, 1):
                    if e.hp > 0:
                        cr.damage_target(run, f"e{i}", dmg, source="p0", damage_type=n["damage_type"], card=self)
            if n["core_draw"] > 0:
                engine.card_player.draw_cards(run.player, n["core_draw"], run)
        total_shield = int(getattr(self, "shield_amount", n["core_shield"] + n["mod_shield"]) or 0)
        if total_shield > 0:
            cr.gain_shield(run, "p0", total_shield)
        total_heal = int(getattr(self, "heal_amount", n["heal"]) or 0)
        if total_heal > 0:
            cr.heal_target(run, "p0", total_heal)
        if n["mod"] == "draw" and n["mod_draw"] > 0:
            engine.card_player.draw_cards(run.player, n["mod_draw"], run)
        elif n["mod"] == "poison" and n["poison"] > 0:
            pcfg = BUFF_CONFIG["poison"]
            if n["aoe"]:
                for e in run.enemies:
                    if e.hp > 0:
                        cr.add_buff_to(e, "poison", pcfg["name"], pcfg["desc"], n["poison"])
            else:
                t_ref = target if (target and str(target).startswith("e")) else engine._get_first_alive_enemy(run)
                if t_ref and str(t_ref).startswith("e"):
                    try:
                        idx = int(str(t_ref)[1:]) - 1
                        if 0 <= idx < len(run.enemies) and run.enemies[idx].hp > 0:
                            cr.add_buff_to(run.enemies[idx], "poison", pcfg["name"], pcfg["desc"], n["poison"])
                    except ValueError:
                        pass
        return get_locale_text("i18n_kappa_pancake.kappa.card_feedback", name=self.name)
