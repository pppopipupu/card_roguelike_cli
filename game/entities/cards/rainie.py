import random
from typing import Optional

from ...core.inventory.deck_service import DeckService
from ...data.entities.buffs.buff_data import BUFF_CONFIG
from ...data.text.locale_data import get_locale_text
from ...models.state import AmuletState, BuffState, Card, CardState, ensure_card_state
from ..tags import LyricsTag
from .registry import CARD_CLASS_REGISTRY

RAINIE_LOVE_ID = "rainie_love"
RAINIE_RAIN_WISH_ID = "rainie_lyric_rain_wish"
RAINIE_RAINBOW_ID = "rainie_lyric_rainbow"
RAINIE_LYRIC_IDS = (
    "rainie_lyric_listen",
    "rainie_lyric_clear",
    "rainie_lyric_breath",
    "rainie_lyric_rain_wish",
    "rainie_lyric_miss",
    "rainie_lyric_transparent",
    "rainie_lyric_rainie_love",
    "rainie_lyric_rain_outside",
    "rainie_lyric_accumulate",
    "rainie_lyric_memory",
    "rainie_lyric_secret",
    "rainie_lyric_continue",
    "rainie_lyric_believe",
    "rainie_lyric_rainbow",
)


class _RainieCardBase(Card):
    def _params(self) -> dict:
        return dict(getattr(self, "effect_params", None) or {})

    def _buff(self, entity, engine, buff_id: str, stacks: int = 1) -> BuffState:
        cfg = BUFF_CONFIG.get(buff_id, {})
        engine._add_buff_to(entity, buff_id, cfg.get("name", buff_id), cfg.get("desc", ""), stacks)
        return next((b for b in entity.buffs if b.id == buff_id), BuffState(buff_id, cfg.get("name", buff_id), stacks))

    def _set_source(self, entity, buff_id: str, uid: str) -> None:
        for buff in getattr(entity, "buffs", []) or []:
            if buff.id == buff_id:
                buff.source_uid = uid

    def _owner(self, run) -> tuple:
        p = run.player
        return p, run.uid_for(p)

    def _resolve_enemy(self, run, target):
        if target and str(target).startswith("e"):
            try:
                idx = int(str(target)[1:]) - 1
            except ValueError:
                idx = -1
            if 0 <= idx < len(run.enemies) and run.enemies[idx].hp > 0:
                return run.enemies[idx]
        for enemy in run.enemies:
            if enemy.hp > 0:
                return enemy
        return None


class RainieLyricCard(_RainieCardBase):
    def _next_lyric(self, run, engine) -> str:
        from ...core.battle.rainie_runtime import add_next_lyric, get_lyric_progress, set_lyric_progress
        p, _ = self._owner(run)
        progress = get_lyric_progress(run, p)
        index = self._form_index() if getattr(self, "effect", "") == "rain_wish" else int(getattr(self, "lyric_index", 0) or 0)
        if index <= 0 or index != progress or index >= 15:
            return ""
        chain = add_next_lyric(run, p, index, self._form_index() if index == 4 else 0)
        set_lyric_progress(run, p, index + 1)
        return chain

    def _form_index(self) -> int:
        state = getattr(self, "card_state", None)
        form = int(getattr(state, "lyric_form", 0) or 0) if state is not None else 0
        return 11 if form == 11 else 4

    def _apply_effect(self, run, engine, target: Optional[str] = None, choice: str = "") -> str:
        p, uid = self._owner(run)
        params = self._params()
        effect = str(getattr(self, "effect", "") or "")
        if effect == "listen":
            from ...core.battle.rainie_runtime import living_enemies
            turns = int(params.get("turns", 1) or 1)
            for enemy in living_enemies(run):
                self._buff(enemy, engine, "sleep_rain", turns)
                self._set_source(enemy, "sleep_rain", uid)
                engine._sync_enemy_intents(enemy)
            return get_locale_text("i18n_rainie.effects.listen", turns=turns)
        if effect == "eye_drops":
            from ...core.battle.rainie_runtime import clear_debuffs, damage_all, living_enemies, strip_enemy_defenses
            cleaned = clear_debuffs(p)
            stripped = 0
            for enemy in living_enemies(run):
                stripped += strip_enemy_defenses(enemy)
            self._buff(p, engine, "eight_k_sharp", 1)
            self._set_source(p, "eight_k_sharp", uid)
            drops = int(params.get("drops", 3) or 3)
            drop_damage = int(params.get("drop_damage", 1) or 1)
            damage_all(run, engine, drop_damage, damage_type="cold", source="p0", card=self, times=drops)
            return get_locale_text("i18n_rainie.effects.eye_drops", cleaned=cleaned, stripped=stripped, drops=drops, damage=drop_damage)
        if effect == "breath":
            from ...core.battle.rainie_runtime import steal_regular_debuffs
            enemy = self._resolve_enemy(run, target)
            if enemy is None:
                return get_locale_text("i18n_rainie.no_enemy")
            self._buff(enemy, engine, "breath_osmosis", 1)
            self._set_source(enemy, "breath_osmosis", uid)
            stolen = steal_regular_debuffs(engine, run, p, enemy)
            if stolen <= 0:
                heal = int(params.get("clean_heal", 6) or 6)
                strength = int(params.get("clean_strength", 2) or 2)
                engine._heal_target(run, "p0", heal)
                self._buff(p, engine, "strength", strength)
                return get_locale_text("i18n_rainie.effects.breath_clean", heal=heal, strength=strength)
            return get_locale_text("i18n_rainie.effects.breath", stolen=stolen)
        if effect == "rain_wish":
            form = self._form_index()
            replay = int(params.get("replay_11", 2) if form == 11 else params.get("replay_4", 1))
            self._buff(p, engine, "rain_wish_amplify", 1)
            self._buff(p, engine, "rain_wish_amplify_post", 1)
            self._buff(p, engine, "rain_wish_no_shield_decay", 1)
            replay_buff = self._buff(p, engine, "rain_wish_replay_pending", replay)
            replay_buff.stacks2 = replay
            if form == 11:
                p.actions += 1
                p.bonus_actions += 1
                self._buff(p, engine, "rain_wish_retain_hand", 1)
                from ...core.battle.extra_turn_service import MODE_EXTRA, grant_extra_turn
                grant_extra_turn(run, uid, MODE_EXTRA, 1, source=self.id)
                return get_locale_text("i18n_rainie.effects.rain_wish_11")
            rain_buff = self._buff(p, engine, "rain_wish_rain_pending", 1)
            rain_buff.stacks2 = 1
            return get_locale_text("i18n_rainie.effects.rain_wish_4", damage=int(params.get("rain_damage", 6) or 6))
        if effect == "emo":
            from ...core.battle.rainie_runtime import living_enemies
            self._buff(p, engine, "emo_love_brain", 1)
            self._set_source(p, "emo_love_brain", uid)
            stacks = int(params.get("stacks", 2) or 2)
            for enemy in living_enemies(run):
                self._buff(enemy, engine, "missing_ex", stacks)
                self._set_source(enemy, "missing_ex", uid)
            return get_locale_text("i18n_rainie.effects.emo", stacks=stacks)
        if effect == "transparent":
            from ...core.battle.rainie_runtime import living_enemies
            from ..cards.ninja_base import resolve_card_effective_cost_a, resolve_card_effective_cost_ba
            from .base import ALL_CARDS
            self._buff(p, engine, "intangible", 1)
            self._buff(p, engine, "rainie_transparent", 1)
            self._set_source(p, "rainie_transparent", uid)
            for enemy in living_enemies(run):
                enemy.shield = 0
                self._buff(enemy, engine, "transparent_wrap", 1)
                self._set_source(enemy, "transparent_wrap", uid)
            rows = []
            for state in p.hand:
                card = ALL_CARDS.get(state)
                if card is None or getattr(card, "lyrics", False):
                    continue
                cost = max(0, resolve_card_effective_cost_a(card, state, p)) + max(0, resolve_card_effective_cost_ba(card, state, p))
                rows.append((cost, state))
            rows.sort(key=lambda item: item[0], reverse=True)
            top = int(params.get("top_cards", 2) or 2)
            changed = 0
            for _, state in rows[:top]:
                state.temp_cost_a = 0
                state.temp_cost_ba = 0
                state.temp_ethereal = True
                changed += 1
            return get_locale_text("i18n_rainie.effects.transparent", changed=changed)
        if effect == "courage":
            from ...core.battle.rainie_runtime import living_enemies
            shield_value = max(0, int(p.shield or 0))
            p.shield = 0
            total = shield_value * int(params.get("damage_per_shield", 2) or 2)
            hit = 0
            while hit < total:
                alive = living_enemies(run)
                if not alive:
                    break
                enemy = random.choice(alive)
                engine._damage_target(run, f"e{run.enemies.index(enemy) + 1}", 2, source="p0", damage_type="radiant", card=self)
                hit += 2
            self._buff(p, engine, "rainie_courage", 1)
            self._set_source(p, "rainie_courage", uid)
            return get_locale_text("i18n_rainie.effects.courage", shield=shield_value, damage=total)
        if effect == "window":
            from ...entities.amulets.amulets import rainie_window_swan_song
            countdown = int(params.get("countdown", 3) or 3)
            grid = engine._get_free_grid(p)
            if grid:
                p.amulets[grid] = AmuletState(
                    "rainie_window",
                    get_locale_text("i18n_rainie.window_name"),
                    countdown,
                    get_locale_text("i18n_rainie.window_desc"),
                )
                return get_locale_text("i18n_rainie.effects.window", grid=grid, countdown=countdown)
            msg = rainie_window_swan_song(run, engine)
            return get_locale_text("i18n_rainie.effects.window_broken", effect=msg)
        if effect == "accumulate":
            from ...core.battle.rainie_runtime import living_enemies
            stacks = int(params.get("stacks", 1) or 1)
            for enemy in living_enemies(run):
                buff = self._buff(enemy, engine, "dripping", stacks)
                buff.stacks2 = 1
                self._set_source(enemy, "dripping", uid)
            return get_locale_text("i18n_rainie.effects.accumulate", stacks=stacks)
        if effect == "memory":
            from ...core.battle.rainie_runtime import copy_exhausted_non_lyric, ensure_rain_wish_11, set_lyric_progress
            wish_msg = ensure_rain_wish_11(run, p)
            copy_msg = copy_exhausted_non_lyric(run, p)
            turns = int(params.get("turns", 3) or 3)
            self._buff(p, engine, "rainy_season", turns)
            self._set_source(p, "rainy_season", uid)
            set_lyric_progress(run, p, 11)
            parts = [wish_msg]
            if copy_msg:
                parts.append(copy_msg)
            parts.append(get_locale_text("i18n_rainie.effects.rainy_season", turns=turns))
            return "\n".join(parts)
        if effect == "secret":
            from ...core.battle.rainie_runtime import check_social_death, living_enemies
            from .base import ALL_CARDS
            secret_key = f"i18n_rainie.secrets.{random.randint(1, 6)}"
            parts = [get_locale_text(secret_key)]
            for enemy in list(living_enemies(run)):
                self._buff(enemy, engine, "social_death", 1)
                self._set_source(enemy, "social_death", uid)
                check = check_social_death(engine, run, enemy, p)
                if check:
                    parts.append(check)
            candidates = [
                cid for cid, card in ALL_CARDS.items()
                if card.rarity == "legendary"
                and not card.token
                and not getattr(card, "lyrics", False)
                and card.color in ("warrior", "wizard", "ninja", "wizard_warrior")
                and not getattr(card, "event_only", False)
                and not getattr(card, "life_merchant_only", False)
                and cid != self.id
            ]
            if candidates:
                chosen = random.choice(candidates)
                p.hand.append(CardState(
                    id=chosen,
                    temp_cost_a=0,
                    temp_cost_ba=0,
                    temp_ethereal=True,
                    temp_exhaust=True,
                ))
                parts.append(get_locale_text("i18n_rainie.effects.secret_card", name=ALL_CARDS[chosen].name))
            return "\n".join(parts)
        if effect == "infinite_refill":
            self._buff(p, engine, "infinite_refill", 1)
            self._set_source(p, "infinite_refill", uid)
            self._buff(p, engine, "rainie_cross_battle", 1)
            p.rainie_cross_battle = True
            return get_locale_text("i18n_rainie.effects.infinite_refill")
        if effect == "prophecy":
            return self._prophecy(run, engine, choice)
        if effect == "rainbow_wall":
            from ...data.cards.classes.wizard_card_data import WIZARD_CARD_CONFIG
            count = int(params.get("count", 100) or 0)
            card_id = str(params.get("card_id", "wizard_prismatic_wall"))
            cost = int(WIZARD_CARD_CONFIG.get(card_id, {}).get("cost_a", 0) or 0)
            for _ in range(count):
                state = DeckService.add_card_to_draw(p, card_id)
                state.battle_cost_delta_a = -cost
            return get_locale_text("i18n_rainie.effects.rainbow_wall", count=count)
        return ""

    def _prophecy(self, run, engine, choice: str) -> str:
        p, uid = self._owner(run)
        params = self._params()
        if choice not in ("1", "2", "3"):
            choice = "1"
        if choice == "1":
            from ...core.battle.rainie_runtime import find_card
            found = find_card(p, RAINIE_RAINBOW_ID)
            if found:
                pile_name, idx, state = found
                if pile_name != "hand":
                    getattr(p, f"{pile_name}_pile").pop(idx)
                    p.hand.append(state)
                state.replay = max(1, int(state.replay or 0))
                return get_locale_text("i18n_rainie.prophecy.rainbow_found", name=get_locale_text("i18n_rainie.cards.rainbow_name"))
            p.hand.append(CardState(id=RAINIE_RAINBOW_ID, temp_ethereal=True, replay=1))
            return get_locale_text("i18n_rainie.prophecy.rainbow_created", name=get_locale_text("i18n_rainie.cards.rainbow_name"))
        if choice == "2":
            from ...core.battle.rainie_runtime import living_enemies
            countdown = int(params.get("countdown", 2) or 2)
            for enemy in living_enemies(run):
                self._buff(enemy, engine, "i_believe_you_will_die", countdown)
                self._set_source(enemy, "i_believe_you_will_die", uid)
            return get_locale_text("i18n_rainie.prophecy.enemy_death", countdown=countdown, damage=int(params.get("damage", 55) or 55))
        self._buff(p, engine, "idealist_death_ward", 1)
        self._set_source(p, "idealist_death_ward", uid)
        self._buff(p, engine, "rain_wish_free_pending", 1)
        return get_locale_text("i18n_rainie.prophecy.miracle", shield=int(params.get("shield", 40) or 40))

    def _run_card(self, run, engine, target: Optional[str] = None, choice: str = "") -> str:
        p, _ = self._owner(run)
        parts = [self._apply_effect(run, engine, target=target, choice=choice)]
        draw_count = int(getattr(self, "draw_count", 0) or 0)
        if draw_count > 0:
            engine._draw_cards(p, draw_count, run)
            parts.append(get_locale_text("i18n_rainie.effects.draw", amount=draw_count))
        chain = self._next_lyric(run, engine)
        if chain:
            parts.append(chain)
        return "\n".join(part for part in parts if part)

    def execute(self, run, target, engine) -> str:
        return self._run_card(run, engine, target=target)

    def execute_with_selections(self, run, selections: dict, engine) -> str:
        from ...core.battle.selection import SelectionResult
        choice = SelectionResult.from_raw(selections).choice("prophecy_choice") or ""
        return self._run_card(run, engine, choice=choice)

    def get_selection_spec(self, run, engine) -> Optional[dict]:
        if getattr(self, "effect", "") != "prophecy":
            return None
        from ...core.battle.selection import ChoiceOption, choose_one_spec
        options = [
            ChoiceOption(
                id=str(index),
                label_key=f"i18n_rainie.prophecy.option_{index}",
                value=str(index),
                match_aliases=(name,),
            )
            for index, name in ((1, "彩虹"), (2, "敌人暴毙"), (3, "奇迹"))
        ]
        return choose_one_spec(
            options,
            step_id="prophecy_choice",
            cancel_key="i18n_cli_core.select_cancelled",
        )

class RainieLoveCard(_RainieCardBase):
    def execute(self, run, target, engine) -> str:
        from ...core.battle.rainie_runtime import add_card_to_draw, get_lyric_progress, set_lyric_progress
        p = run.player
        amount = int(self._params().get("amount", 1) or 1)
        for _ in range(amount):
            add_card_to_draw(p, "rainie_lyric_listen")
        if get_lyric_progress(run, p) <= 0:
            set_lyric_progress(run, p, 1)
        return get_locale_text("i18n_rainie.cards.rainie_love.result", amount=amount)


for _cid in RAINIE_LYRIC_IDS:
    CARD_CLASS_REGISTRY[_cid] = (RainieLyricCard, {})
    CARD_CLASS_REGISTRY[f"{_cid}+"] = (RainieLyricCard, {})
CARD_CLASS_REGISTRY[RAINIE_LOVE_ID] = (RainieLoveCard, {})
CARD_CLASS_REGISTRY[f"{RAINIE_LOVE_ID}+"] = (RainieLoveCard, {})
