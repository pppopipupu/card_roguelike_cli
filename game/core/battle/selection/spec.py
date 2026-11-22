import re
from dataclasses import dataclass
from typing import Any, Callable, Optional

SELECTOR_ALLY_MG_QUERY_RE = re.compile(r"^a(\d+)mg:(.+)$")
SELECTOR_ALLY_MG_IDX_RE = re.compile(r"^a(\d+)mg(\d+)$")
SELECTOR_ALLY_M_QUERY_RE = re.compile(r"^a(\d+)m:(.+)$")
SELECTOR_ALLY_M_IDX_RE = re.compile(r"^a(\d+)m(\d+)$")
SELECTOR_ALLY_IDX_RE = re.compile(r"^a(\d+)$")
SELECTOR_ALLY_QUERY_RE = re.compile(r"^a:(.+)$")
SELECTOR_MG_QUERY_RE = re.compile(r"^mg:(.+)$")
SELECTOR_MG_IDX_RE = re.compile(r"^mg(\d+)$")
SELECTOR_EG_QUERY_RE = re.compile(r"^eg:(.+)$")
SELECTOR_EG_IDX_RE = re.compile(r"^eg(\d+)$")
SELECTOR_PREFIX_QUERY_RE = re.compile(r"^(ex|dc|dr|h|m|e):(.+)$")
SELECTOR_PREFIX_IDX_RE = re.compile(r"^(ex|dc|dr|h|m|e)(\d+)$")
SELECTOR_OWN_P_IDX_RE = re.compile(r"^p(\d+)$")

PREFIX_SCOPE_MAP = {
    "ex": "exhaust",
    "dc": "discard",
    "dr": "draw",
    "h": "hand",
    "m": "own_minion",
    "e": "enemy",
}

PILE_ATTR_MAP = {
    "hand": "hand",
    "exhaust": "exhaust_pile",
    "discard": "discard_pile",
    "draw": "draw_pile",
}

GRAVEYARD_SCOPES = {"minion_graveyard", "enemy_graveyard", "ally_minion_graveyard"}
PILE_SCOPES = {"hand", "exhaust", "discard", "draw"}
GRID_SCOPES = {"enemy", "own_minion", "ally_minion", "ally_player"}


@dataclass
class ParsedSelector:
    scope: str
    ally_slot: Optional[int] = None
    index: Optional[int] = None
    query: Optional[str] = None
    raw: str = ""


@dataclass
class SelectionStepSpec:
    step_id: str
    kind: str
    min_count: int = 1
    max_count: int = 1
    required: bool = True
    auto_single: bool = True
    allow_simple_auto: bool = False
    exclude_playing_card: bool = False
    filter_fn: Optional[Callable[[Any, Any, Any], bool]] = None
    options: Optional[list[dict]] = None
    card_pool_fn: Optional[Callable[[Any], list[Any]]] = None
    sample_count: int = 3
    pick_count: int = 1
    prompt_key: str = "i18n_cli_core.select_prompt_default"
    continue_key: str = "i18n_cli_core.select_continue_default"
    error_key: str = "i18n_cli_core.select_required_default"
    invalid_index_key: str = "i18n_cli_core.select_invalid_index_default"
    empty_key: str = "i18n_cli_core.select_empty_default"
