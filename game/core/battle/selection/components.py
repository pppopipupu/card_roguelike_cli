from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from ....data.text.locale_data import get_locale_text
from .spec import SelectionStepSpec

SelectionSpec = dict


@dataclass
class ChoiceOption:
    """单个可选项目的声明，供抉择类卡牌复用。"""

    id: str
    label_key: str
    params: dict = field(default_factory=dict)
    disabled: bool = False
    value: str = ""
    match_aliases: tuple[str, ...] = ()

    def to_candidate(self, index: int) -> dict:
        """将声明转换为选择候选字典。"""
        label = get_locale_text(self.label_key, **self.params)
        value = self.value or self.id
        return {
            "uid": f"option:{index}:{value}",
            "value": value,
            "label": label,
            "match_name": label,
            "aliases": list(self.match_aliases),
            "scope": "option",
            "source_idx": index,
            "ally_slot": None,
        }


@dataclass
class SelectionResult:
    """统一的卡牌选择结果，封装来源下标与卡牌身份。"""

    selections: dict[str, list]
    cancelled: bool = False

    @classmethod
    def from_raw(cls, raw: dict, cancelled: bool = False) -> "SelectionResult":
        """从原始选择字典构造结果包装。"""
        return cls(selections=dict(raw or {}), cancelled=cancelled)

    def _items(self, step_id: str) -> list[dict]:
        return list(self.selections.get(step_id, []) or [])

    def choice(self, step_id: str) -> Optional[str]:
        """读取单步抉择的字符串值。"""
        items = self._items(step_id)
        return items[0].get("value") if items else None

    def target(self, step_id: str) -> Optional[str]:
        """读取单步目标引用，如 e1、a2 或 p0。"""
        items = self._items(step_id)
        return items[0].get("value") if items else None

    def labels(self, step_id: str) -> list[str]:
        """读取选中项的展示名称列表。"""
        return [item.get("label", "") for item in self._items(step_id)]

    def pop_cards(self, pile: list, step_id: str) -> list:
        """从牌堆中安全弹出该步骤选中的卡牌。"""
        from .pile_ops import pop_selected_pile_cards
        return pop_selected_pile_cards(pile, self._items(step_id))

    def find_card_indices(self, pile: list, step_id: str) -> list[int]:
        """在当前牌堆中定位该步骤选中的卡牌，按身份而非旧下标匹配。"""
        from ....models.state import ensure_card_state
        matched: list[int] = []
        used: set[int] = set()
        for item in self._items(step_id):
            card_id = item.get("card_id")
            upgraded = bool(item.get("upgraded", False))
            gems = list(item.get("gems", []) or [])
            chosen = None
            src_idx = item.get("source_idx")
            if isinstance(src_idx, int) and 0 <= src_idx < len(pile) and src_idx not in used:
                state = ensure_card_state(pile[src_idx])
                if state.id == card_id and bool(state.upgraded) == upgraded and list(state.gems or []) == gems:
                    chosen = src_idx
            if chosen is None:
                for index, raw_card in enumerate(pile):
                    if index in used:
                        continue
                    state = ensure_card_state(raw_card)
                    if state.id == card_id and bool(state.upgraded) == upgraded and list(state.gems or []) == gems:
                        chosen = index
                        break
            if chosen is not None:
                used.add(chosen)
                matched.append(chosen)
        return matched


def choice_step(
    step_id: str,
    options: list[ChoiceOption],
    *,
    prompt_key: str = "i18n_cli_core.select_prompt_default",
    continue_key: str = "",
    error_key: str = "i18n_cli_core.select_required_default",
    invalid_index_key: str = "i18n_cli_core.select_invalid_index_default",
    min_count: int = 1,
    max_count: int = 1,
) -> SelectionStepSpec:
    """构造抉择步骤，禁用项不会进入候选列表。"""
    enabled = [opt for opt in options if not opt.disabled]
    return SelectionStepSpec(
        step_id=step_id,
        kind="option",
        min_count=min_count,
        max_count=max_count,
        required=True,
        auto_single=True,
        options=[opt.to_candidate(idx) for idx, opt in enumerate(enabled)],
        prompt_key=prompt_key,
        continue_key=continue_key,
        error_key=error_key,
        invalid_index_key=invalid_index_key,
    )


def choose_one_spec(
    options: list[ChoiceOption],
    *,
    step_id: str = "choice",
    prompt_key: str = "i18n_cli_core.select_prompt_default",
    error_key: str = "i18n_cli_core.select_required_default",
    invalid_index_key: str = "i18n_cli_core.select_invalid_index_default",
    cancel_key: str = "i18n_cli_core.select_cancelled",
    can_cancel: bool = True,
) -> SelectionSpec:
    """构造单步抉择规格，供三选一等卡牌复用。"""
    return {
        "phase": "pre_play",
        "can_cancel": can_cancel,
        "cancel_key": cancel_key,
        "steps": [
            choice_step(
                step_id,
                options,
                prompt_key=prompt_key,
                error_key=error_key,
                invalid_index_key=invalid_index_key,
            )
        ],
    }


def pile_card_step(
    step_id: str,
    pile: str,
    *,
    min_count: int = 1,
    max_count: int = 1,
    required: bool = True,
    exclude_playing_card: bool = False,
    filter_fn: Optional[Callable] = None,
    prompt_key: str = "i18n_cli_core.select_prompt_default",
    continue_key: str = "",
    error_key: str = "i18n_cli_core.select_required_default",
    invalid_index_key: str = "i18n_cli_core.select_invalid_index_default",
    empty_key: str = "i18n_cli_core.select_empty_default",
) -> SelectionStepSpec:
    """构造从指定牌堆选牌的步骤。"""
    return SelectionStepSpec(
        step_id=step_id,
        kind=pile,
        min_count=min_count,
        max_count=max_count,
        required=required,
        auto_single=True,
        exclude_playing_card=exclude_playing_card,
        filter_fn=filter_fn,
        prompt_key=prompt_key,
        continue_key=continue_key,
        error_key=error_key,
        invalid_index_key=invalid_index_key,
        empty_key=empty_key,
    )


def discover_from_pile_spec(
    *,
    step_id: str,
    source: str,
    max_count: int,
    prompt_key: str,
    continue_key: str = "",
    error_key: str = "",
    invalid_index_key: str = "",
    empty_key: str = "",
    filter_fn: Optional[Callable] = None,
) -> SelectionSpec:
    """从指定牌堆中发现卡牌的规格，淘汰手写四层字典。"""
    step = pile_card_step(
        step_id,
        source,
        max_count=max_count,
        filter_fn=filter_fn,
        prompt_key=prompt_key,
        continue_key=continue_key,
        error_key=error_key,
        invalid_index_key=invalid_index_key,
        empty_key=empty_key,
    )
    return {
        "phase": "pre_play",
        "can_cancel": True,
        "cancel_key": "i18n_cli_core.err_cancel_discover",
        "empty_abort_check": True,
        "steps": [step],
    }


def discover_from_pool_spec(
    card_pool_fn: Callable[[Any], list[Any]],
    *,
    step_id: str = "pool",
    sample_count: int = 3,
    pick_count: int = 1,
    prompt_key: str = "i18n_cli_core.select_prompt_default",
    continue_key: str = "",
    error_key: str = "i18n_cli_core.select_required_default",
    invalid_index_key: str = "i18n_cli_core.select_invalid_index_default",
    cancel_key: str = "i18n_cli_core.select_cancelled",
    can_cancel: bool = True,
) -> SelectionSpec:
    """构造动态卡池发掘规格，创建会话时固化随机候选快照。"""
    step = SelectionStepSpec(
        step_id=step_id,
        kind="generated_card",
        min_count=pick_count,
        max_count=pick_count,
        required=True,
        auto_single=False,
        card_pool_fn=card_pool_fn,
        sample_count=sample_count,
        pick_count=pick_count,
        prompt_key=prompt_key,
        continue_key=continue_key,
        error_key=error_key,
        invalid_index_key=invalid_index_key,
    )
    return {
        "phase": "pre_play",
        "can_cancel": can_cancel,
        "cancel_key": cancel_key,
        "steps": [step],
    }


def discard_hand_spec(
    *,
    step_id: str,
    min_count: int,
    max_count: int,
    prompt_key: str,
    error_key: str,
    invalid_index_key: str,
    exclude_playing_card: bool = False,
    with_enemy_target: bool = False,
    enemy_target_step_id: str = "discard_target",
    enemy_target_allow_simple_auto: bool = False,
    phase: str = "pre_play",
    can_cancel: bool = True,
) -> SelectionSpec:
    """构造弃牌选择规格；需要目标时按“先目标、后弃牌”排序。"""
    steps = []
    if with_enemy_target:
        steps.append(
            target_step(
                enemy_target_step_id,
                "enemy",
                allow_simple_auto=enemy_target_allow_simple_auto,
            )
        )
    steps.append(
        pile_card_step(
            step_id,
            "hand",
            min_count=min_count,
            max_count=max_count,
            exclude_playing_card=exclude_playing_card,
            prompt_key=prompt_key,
            error_key=error_key,
            invalid_index_key=invalid_index_key,
        )
    )
    return {"phase": phase, "can_cancel": can_cancel, "steps": steps}


def target_step(
    step_id: str,
    kind: str = "enemy",
    *,
    allow_simple_auto: bool = False,
    filter_fn: Optional[Callable] = None,
    prompt_key: str = "i18n_battle_misc.select_target_prompt",
    error_key: str = "i18n_battle_core.enemy_target_missing",
    invalid_index_key: str = "i18n_battle_core.invalid_target",
) -> SelectionStepSpec:
    """构造通用目标选择步骤。"""
    return SelectionStepSpec(
        step_id=step_id,
        kind=kind,
        min_count=1,
        max_count=1,
        required=True,
        auto_single=True,
        allow_simple_auto=allow_simple_auto,
        filter_fn=filter_fn,
        prompt_key=prompt_key,
        error_key=error_key,
        invalid_index_key=invalid_index_key,
    )
