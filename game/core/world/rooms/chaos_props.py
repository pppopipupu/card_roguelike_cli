import random
from ....data.content.chaos_expansion_data import CHAOS_GROUND_ITEMS
from ....data.text.locale_data import get_locale_text
from ...inventory.bag_service import add_bag_item, get_item_display_name
from ..persistent_buffs import add_persistent_buff
from ..sp_system import reduce_exhaustion, restore_sp
from .big_room import add_effective_item
from .interact import _reveal_any_special, register_prop_handler


@register_prop_handler("saisen_box")
def _touch_saisen_box(run, room, cfg, p, fm, coord) -> str:
    cost = int(cfg.get("cost_gold", 10))
    if p.gold >= cost:
        if random.random() < 0.7:
            p.gold -= cost
            add_persistent_buff(p, "ancient_ward", 1)
            sp = restore_sp(p, 2)
            return get_locale_text("i18n_chaos_expansion.props.saisen_box.touch_bless", cost=cost, sp=sp)
        item_id = random.choice(["yin_yang_orb", "sugar_cube_pack"])
        gold_back = 12
        p.gold += gold_back
        ok, _ = add_bag_item(p, item_id)
        if not ok:
            add_effective_item(fm, room, item_id)
        return get_locale_text(
            "i18n_chaos_expansion.props.saisen_box.touch_refund",
            gold=gold_back,
            item=get_item_display_name(item_id),
        )
    restore_sp(p, 1)
    return get_locale_text("i18n_chaos_expansion.props.saisen_box.touch_poor")


@register_prop_handler("scarlet_bookshelf")
def _touch_scarlet_bookshelf(run, room, cfg, p, fm, coord) -> str:
    if random.random() < 0.65:
        add_persistent_buff(p, "arcane_clarity", 1)
        item_id = random.choice(["magic_mushroom", "ancient_notes", "mini_hakkero"])
        ok, _ = add_bag_item(p, item_id)
        if not ok:
            add_effective_item(fm, room, item_id)
        return get_locale_text(
            "i18n_chaos_expansion.props.scarlet_bookshelf.touch_ok",
            item=get_item_display_name(item_id),
        )
    dmg = min(3, max(0, p.hp - 1))
    p.hp = max(1, p.hp - dmg)
    p.gold += 14
    restore_sp(p, 2)
    return get_locale_text("i18n_chaos_expansion.props.scarlet_bookshelf.touch_bonk", dmg=dmg, gold=14)


@register_prop_handler("tea_party_table")
def _touch_tea_party_table(run, room, cfg, p, fm, coord) -> str:
    before = p.hp
    p.hp = min(p.max_hp, p.hp + 10)
    sp = restore_sp(p, 3)
    old_ex = getattr(p, "exhaustion", 0)
    new_ex = reduce_exhaustion(p, 1)
    return get_locale_text(
        "i18n_chaos_expansion.props.tea_party_table.touch_ok",
        heal=p.hp - before,
        sp=sp,
        cured=max(0, old_ex - new_ex),
    )


@register_prop_handler("grief_seed_pedestal")
def _touch_grief_seed_pedestal(run, room, cfg, p, fm, coord) -> str:
    if random.random() < 0.5:
        old_ex = getattr(p, "exhaustion", 0)
        new_ex = reduce_exhaustion(p, 2)
        sp = restore_sp(p, 2)
        revealed = _reveal_any_special(fm, 1) if fm is not None else []
        target_coord = revealed[0] if revealed else coord
        return get_locale_text(
            "i18n_chaos_expansion.props.grief_seed_pedestal.touch_purify",
            cured=max(0, old_ex - new_ex),
            sp=sp,
            coord=target_coord,
        )
    item_id = random.choice(["grief_seed", "kyubey_contract"])
    ok, _ = add_bag_item(p, item_id)
    if not ok:
        add_effective_item(fm, room, item_id)
    return get_locale_text(
        "i18n_chaos_expansion.props.grief_seed_pedestal.touch_drop",
        item=get_item_display_name(item_id),
    )


@register_prop_handler("jewel_seed_container")
def _touch_jewel_seed_container(run, room, cfg, p, fm, coord) -> str:
    if random.random() < 0.6:
        add_persistent_buff(p, "ancient_ward", 1)
        sp = restore_sp(p, 3)
        return get_locale_text("i18n_chaos_expansion.props.jewel_seed_container.touch_stable", sp=sp)
    dmg = min(4, max(0, p.hp - 1))
    p.hp = max(1, p.hp - dmg)
    item_id = random.choice([i for i in CHAOS_GROUND_ITEMS if i in ("mana_cartridge", "yin_yang_orb")])
    ok, _ = add_bag_item(p, item_id)
    if not ok:
        add_effective_item(fm, room, item_id)
    return get_locale_text(
        "i18n_chaos_expansion.props.jewel_seed_container.touch_overload",
        dmg=dmg,
        item=get_item_display_name(item_id),
    )
