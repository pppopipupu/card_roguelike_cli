from ...data.temple_config import TEMPLE_ACTIVE_FLAG
from ...data.outer_plane_config import OUTER_PLANE_ACTIVE_FLAG

def resolve_game_state(run, stats) -> str:
    if run is not None:
        if run.node_type == "battle":
            return "battle"
        if run.node_type == "grid_map":
            return "grid_map"
        if run.node_type == "cafe":
            return "cafe"
        return "explore"
    if stats is not None and stats.in_town:
        if stats.town_flags.get(TEMPLE_ACTIVE_FLAG):
            return "temple"
        if stats.town_flags.get(OUTER_PLANE_ACTIVE_FLAG):
            return "outer_plane"
        if stats.town_flags.get("current_dialog"):
            return "dialog"
        return "town"
    return "menu"
