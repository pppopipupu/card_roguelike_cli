import random
from typing import Callable, Dict, Optional
from ...data.text.locale_data import get_locale_raw, get_locale_text
from ...data.entities.potion_data import roll_potion
from ...data.world.room_interact_data import ROGUE_ITEMS
from ..world.persistent_buffs import add_persistent_buff
from ..world.sp_system import reduce_exhaustion, restore_sp

CHAOS_ITEM_HANDLERS: Dict[str, Callable] = {}


def register_chaos_item(*item_ids: str):
    def decorator(fn: Callable):
        for iid in item_ids:
            CHAOS_ITEM_HANDLERS[iid] = fn
        return fn

    return decorator


def try_use_chaos_item(engine, run, item_id: str, cfg: dict, add_bag_item_fn, reveal_fn) -> Optional[str]:
    handler = CHAOS_ITEM_HANDLERS.get(item_id)
    if handler is None:
        return None
    return handler(engine, run, item_id, cfg, add_bag_item_fn, reveal_fn)


def _apply_aoe_damage(engine, run, dmg: int, damage_type: str = "force", debuff: Optional[tuple] = None) -> None:
    be = getattr(engine, "battle_engine", engine)
    for idx, enemy in enumerate(list(getattr(run, "enemies", []) or []), 1):
        if enemy.hp <= 0:
            continue
        be._damage_target(run, f"e{idx}", dmg, source="player:item", damage_type=damage_type)
        if debuff and enemy.hp > 0:
            bid, stacks = debuff
            bname = get_locale_text(f"i18n_chaos_expansion.enemies.buff_{bid}_name") or bid
            bdesc = get_locale_text(f"i18n_chaos_expansion.enemies.buff_{bid}_desc") or bid
            be._add_buff_to(enemy, bid, bname, bdesc, stacks)


@register_chaos_item("yin_yang_orb")
def _use_yin_yang_orb(engine, run, item_id: str, cfg: dict, add_bag_item_fn, reveal_fn) -> str:
    p = run.player
    p.bag_items.remove(item_id)
    if run.node_type == "battle" and getattr(run, "enemies", None):
        dmg = int(cfg.get("damage", 14))
        shield = int(cfg.get("shield", 8))
        _apply_aoe_damage(engine, run, dmg, damage_type="force")
        p.shield = int(getattr(p, "shield", 0)) + shield
        return get_locale_text("i18n_chaos_expansion.items.yin_yang_orb.use_battle", dmg=dmg, shield=shield)
    fm = getattr(run, "floor_map", None)
    revealed = reveal_fn(fm, 2) if fm is not None else []
    sp = restore_sp(p, int(cfg.get("sp_gain", 2)))
    return get_locale_text("i18n_chaos_expansion.items.yin_yang_orb.use_map", count=len(revealed), sp=sp)


@register_chaos_item("mini_hakkero")
def _use_mini_hakkero(engine, run, item_id: str, cfg: dict, add_bag_item_fn, reveal_fn) -> str:
    if run.node_type != "battle" or not getattr(run, "enemies", None):
        return get_locale_text("i18n_room_interact.bag.use_cannot_here", name=get_locale_text(cfg["name_key"]))
    p = run.player
    p.bag_items.remove(item_id)
    dmg = int(cfg.get("damage", 28))
    burn = int(cfg.get("burn_stacks", 3))
    _apply_aoe_damage(engine, run, dmg, damage_type="force", debuff=("burning", burn))
    return get_locale_text("i18n_chaos_expansion.items.mini_hakkero.use_battle", dmg=dmg, burn=burn)


@register_chaos_item("magic_mushroom")
def _use_magic_mushroom(engine, run, item_id: str, cfg: dict, add_bag_item_fn, reveal_fn) -> str:
    p = run.player
    p.bag_items.remove(item_id)
    outcomes = get_locale_raw("i18n_chaos_expansion.items.magic_mushroom.use_outcomes", [])
    idx = random.randint(0, 2)
    if idx == 0:
        before = p.hp
        p.hp = min(p.max_hp, p.hp + int(cfg.get("heal", 10)))
        sp = restore_sp(p, int(cfg.get("sp_gain", 3)))
        tpl = outcomes[0] if len(outcomes) > 0 else ""
        return str(tpl).format(heal=p.hp - before, sp=sp)
    if idx == 1:
        dmg = min(2, max(0, p.hp - 1))
        p.hp = max(1, p.hp - dmg)
        shield = int(cfg.get("shield", 10))
        p.shield = int(getattr(p, "shield", 0)) + shield
        tpl = outcomes[1] if len(outcomes) > 1 else ""
        return str(tpl).format(dmg=dmg, shield=shield)
    sp = restore_sp(p, int(cfg.get("sp_gain", 3)))
    p.gold += 25
    tpl = outcomes[2] if len(outcomes) > 2 else ""
    return str(tpl).format(sp=sp)


@register_chaos_item("grief_seed")
def _use_grief_seed(engine, run, item_id: str, cfg: dict, add_bag_item_fn, reveal_fn) -> str:
    p = run.player
    p.bag_items.remove(item_id)
    sp = restore_sp(p, int(cfg.get("sp_gain", 5)))
    old_ex = getattr(p, "exhaustion", 0)
    new_ex = reduce_exhaustion(p, int(cfg.get("exhaustion_cure", 2)))
    gold = int(cfg.get("gold_bonus", 12))
    p.gold += gold
    if run.node_type == "battle":
        bad_ids = {"weak", "severe_weak", "burning", "bleed", "poison", "shock", "drain_ba", "void_weakness"}
        p.buffs = [b for b in getattr(p, "buffs", []) if b.id not in bad_ids]
        p.shield = int(getattr(p, "shield", 0)) + 8
    return get_locale_text(
        "i18n_chaos_expansion.items.grief_seed.use_ok",
        sp=sp,
        cured=max(0, old_ex - new_ex),
        gold=gold,
    )


@register_chaos_item("kyubey_contract")
def _use_kyubey_contract(engine, run, item_id: str, cfg: dict, add_bag_item_fn, reveal_fn) -> str:
    p = run.player
    p.bag_items.remove(item_id)
    hp_cost = min(int(cfg.get("hp_cost", 6)), max(0, p.hp - 1))
    p.hp = max(1, p.hp - hp_cost)
    gold = int(cfg.get("gold_gain", 45))
    p.gold += gold
    sp = restore_sp(p, int(cfg.get("sp_gain", 4)))
    if run.node_type == "battle":
        p.actions = int(getattr(p, "actions", 0)) + 1
        p.bonus_actions = int(getattr(p, "bonus_actions", 0)) + 1
    pid = roll_potion(getattr(p, "selected_class", "warrior"))
    ok, _ = add_bag_item_fn(p, f"potion:{pid}")
    if ok:
        return get_locale_text(
            "i18n_chaos_expansion.items.kyubey_contract.use_ok",
            hp_lost=hp_cost,
            gold=gold,
            sp=sp,
        )
    return get_locale_text(
        "i18n_chaos_expansion.items.kyubey_contract.use_no_space",
        hp_lost=hp_cost,
        gold=gold,
        sp=sp,
    )


@register_chaos_item("mana_cartridge")
def _use_mana_cartridge(engine, run, item_id: str, cfg: dict, add_bag_item_fn, reveal_fn) -> str:
    p = run.player
    p.bag_items.remove(item_id)
    shield = int(cfg.get("shield", 6))
    if run.node_type == "battle" and getattr(run, "enemies", None):
        dmg = int(cfg.get("damage", 18))
        _apply_aoe_damage(engine, run, dmg, damage_type="force")
        p.actions = int(getattr(p, "actions", 0)) + 1
        p.bonus_actions = int(getattr(p, "bonus_actions", 0)) + 1
        p.shield = int(getattr(p, "shield", 0)) + shield
        return get_locale_text("i18n_chaos_expansion.items.mana_cartridge.use_battle", dmg=dmg, shield=shield)
    sp = restore_sp(p, int(cfg.get("sp_gain", 3)))
    p.shield = int(getattr(p, "shield", 0)) + shield
    add_persistent_buff(p, "ancient_ward", 1)
    return get_locale_text("i18n_chaos_expansion.items.mana_cartridge.use_map", sp=sp, shield=shield)
