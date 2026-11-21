from typing import Optional
from ...data.buff_data import BUFF_CONFIG
from ...data.ultimate_prism_data import (
    BLIND_BUFF_ID,
    ULTIMATE_PRISM_CONFIG,
    ULTIMATE_PRISM_YOG_MARKERS,
)
from ...core.progress.achievement_service import AchievementService
from ...core.text.events import locale_text
from ...core.text.pipeline import render_text_node
from ...models.state import Card, GameRun
from ..buffs.base import is_positive_buff
from .registry import register_card


def _is_yog_sothoth_enemy(name: str) -> bool:
    return any(marker in (name or "") for marker in ULTIMATE_PRISM_YOG_MARKERS)


@register_card("ultimate_prism")
class UltimatePrismCard(Card):
    def execute(self, run: GameRun, target: Optional[str], engine) -> str:
        stun_turns = int(ULTIMATE_PRISM_CONFIG["stun_turns"])
        normal_dmg = int(ULTIMATE_PRISM_CONFIG["radiant_damage"])
        yog_dmg = int(ULTIMATE_PRISM_CONFIG["yog_radiant_damage"])
        blind_turns = int(ULTIMATE_PRISM_CONFIG["blind_turns"])
        stun_cfg = BUFF_CONFIG.get("stun", {})
        blind_cfg = BUFF_CONFIG.get(BLIND_BUFF_ID, {})

        for idx, enemy in enumerate(list(run.enemies), 1):
            if enemy.hp <= 0:
                continue
            positive_buffs = [b for b in enemy.buffs if is_positive_buff(b.id)]
            if positive_buffs:
                enemy.buffs = [b for b in enemy.buffs if not is_positive_buff(b.id)]
                engine._log_event(
                    run,
                    locale_text(
                        "i18n_prism.card.play_strip_line",
                        params={"name": enemy.name, "count": len(positive_buffs)},
                    ),
                )
            engine._add_buff_to(
                enemy,
                "stun",
                stun_cfg.get("name", "stun"),
                stun_cfg.get("desc", ""),
                stun_turns,
            )
            if _is_yog_sothoth_enemy(enemy.name):
                engine._log_event(
                    run,
                    locale_text(
                        "i18n_prism.card.play_yog_line",
                        params={"name": enemy.name},
                    ),
                )
                engine._damage_target(
                    run,
                    f"e{idx}",
                    yog_dmg,
                    source="p0",
                    damage_type="radiant",
                    card=self,
                )
            else:
                engine._damage_target(
                    run,
                    f"e{idx}",
                    normal_dmg,
                    source="p0",
                    damage_type="radiant",
                    card=self,
                )
                engine._log_event(
                    run,
                    locale_text(
                        "i18n_prism.card.play_normal_line",
                        params={"name": enemy.name, "dmg": normal_dmg},
                    ),
                )

        engine._add_buff_to(
            run.player,
            BLIND_BUFF_ID,
            blind_cfg.get("name", BLIND_BUFF_ID),
            blind_cfg.get("desc", ""),
            blind_turns,
        )

        if not getattr(run.player, "is_mercenary", False) and getattr(engine, "save_manager", None) is not None:
            owner_uid = run.uid_for(run.player) or run.user_id
            if owner_uid:
                AchievementService(engine.save_manager).record_stat(
                    owner_uid,
                    "ultimate_prism_played",
                    1,
                    mode="add",
                    run=run,
                )

        return render_text_node(locale_text("i18n_prism.card.play_result"))


@register_card("prism_refraction_beam")
class PrismRefractionBeamCard(Card):
    def execute(self, run: GameRun, target: Optional[str], engine) -> str:
        dmg = int(getattr(self, "base_dmg", ULTIMATE_PRISM_CONFIG["merc_beam_damage"]))
        for idx, enemy in enumerate(list(run.enemies), 1):
            if enemy.hp > 0:
                engine._damage_target(run, f"e{idx}", dmg, source="p0", damage_type="radiant", card=self)
        return render_text_node(locale_text("i18n_prism.merc_cards.beam_result", params={"dmg": dmg}))


@register_card("prism_mirror_ward")
class PrismMirrorWardCard(Card):
    def execute(self, run: GameRun, target: Optional[str], engine) -> str:
        shield = int(getattr(self, "shield_amount", ULTIMATE_PRISM_CONFIG["merc_ward_shield"]))
        engine._gain_shield(run, "p0", shield)
        owner_uid = getattr(run.player, "mercenary_owner", "")
        if owner_uid and owner_uid in run.party_order:
            owner = run.players.get(owner_uid)
            if owner is not None and owner.hp > 0 and not owner.downed:
                slot = run.party_order.index(owner_uid) + 1
                engine._gain_shield(run, f"a{slot}", shield)
        return render_text_node(locale_text("i18n_prism.merc_cards.ward_result", params={"shield": shield}))


@register_card("prism_resonant_facet")
class PrismResonantFacetCard(Card):
    def execute(self, run: GameRun, target: Optional[str], engine) -> str:
        dmg = int(getattr(self, "base_dmg", ULTIMATE_PRISM_CONFIG["merc_facet_damage"]))
        draw_cnt = int(getattr(self, "draw_count", ULTIMATE_PRISM_CONFIG["merc_facet_draw"]))
        t = target or engine._get_first_alive_enemy(run)
        t_name = engine._get_target_name(run, t)
        engine._damage_target(run, t, dmg, source="p0", damage_type="radiant", card=self)
        engine._draw_cards(run.player, draw_cnt, run)
        return render_text_node(
            locale_text(
                "i18n_prism.merc_cards.facet_result",
                params={"target": t_name, "dmg": dmg, "draw": draw_cnt},
            )
        )
