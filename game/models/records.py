from dataclasses import dataclass
from typing import Dict, List, TypedDict


@dataclass
class PlayerProfile:
    user_id: str
    name: str
    player_handle: str
    im_account: str
    selected_class: str
    selected_subclass: str
    gp: int
    active_run_id: str
    active_lobby_id: str
    in_town: bool
    mtime: float
    player_id: str = ""


class Lobby(TypedDict):
    lobby_id: str
    leader_id: str
    members: List[str]
    invited: List[str]
    ready: Dict[str, bool]
    created_at: str
