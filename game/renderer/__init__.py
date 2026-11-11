from ..models.state import GameRun, UserStats
from ..data.locale_data import get_locale_text
from .menu import render_menu, render_card_library, render_relic_library, render_deck, render_stats, render_tutorial, render_changelog
from .help import render_help_index, render_help_detail
from .potion import render_potion_list
from .battle import render_battle, render_detailed_battle, render_draw_pile, render_discard_pile, render_exhaust_pile, render_minion_graveyard, render_enemy_graveyard

from .map import render_map_select, render_start_ancient, render_ancient
from .explore import render_event, render_shop, render_rest, render_reward, render_treasure, render_card_select, render_boss_chest, render_corpse_reward, render_life_merchant
from .query import render_query_info

from .town import render_town
from .bag import render_bag

class GameRenderer:


    @staticmethod
    def render_bag(stats: UserStats) -> str:
        return render_bag(stats)

    @staticmethod
    def render_town(stats: UserStats, room_data: dict) -> str:
        return render_town(stats, room_data)

    @staticmethod
    def render_menu(stats: UserStats = None) -> str:
        return render_menu(stats)

    @staticmethod
    def render_help_index(sections: list) -> str:
        return render_help_index(sections)

    @staticmethod
    def render_help_detail(entry: dict) -> str:
        return render_help_detail(entry)

    @staticmethod
    def render_potion_list(run: GameRun) -> str:
        return render_potion_list(run)

    @staticmethod
    def render_tutorial() -> str:
        return render_tutorial()

    @staticmethod
    def render_changelog() -> str:
        return render_changelog()


    @staticmethod
    def render_card_library() -> str:
        return render_card_library()

    @staticmethod
    def render_relic_library() -> str:
        return render_relic_library()

    @staticmethod
    def render_deck(run: GameRun) -> str:
        return render_deck(run)

    @staticmethod
    def render_game(run: GameRun) -> str:
        if not run:
            return render_menu()
        nt = run.node_type
        if nt == "battle":
            return render_battle(run)
        elif nt == "event":
            return render_event(run)
        elif nt == "shop":
            return render_shop(run)
        elif nt == "life_merchant":
            return render_life_merchant(run)
        elif nt == "rest":
            return render_rest(run)
        elif nt == "reward":
            return render_reward(run)
        elif nt == "map_select":
            return render_map_select(run)
        elif nt == "start_ancient":
            return render_start_ancient(run)
        elif nt == "ancient":
            return render_ancient(run)
        elif nt == "treasure":
            return render_treasure(run)
        elif nt == "card_select":
            return render_card_select(run)
        elif nt == "corpse_reward":
            return render_corpse_reward(run)
        elif nt == "boss_chest":
            return render_boss_chest(run)
        elif nt == "gem_insert":
            return run.node_data.get("text", "") + "\n\n" + render_deck(run)
        elif nt == "cafe":
            from ..core.cafe_engine import CafeEngine
            return CafeEngine(None, None).render_cafe(run)
        return get_locale_text("i18n_renderer_extra.unknown_state")

    @staticmethod
    def render_query_info(query_str: str, user_id: str | None = None) -> str:
        return render_query_info(query_str, user_id)

    @staticmethod
    def render_detailed_battle(run: GameRun) -> str:
        return render_detailed_battle(run)

    @staticmethod
    def render_stats(stats: UserStats, include_mode: bool = True) -> str:
        return render_stats(stats, include_mode)


    @staticmethod
    def render_draw_pile(run: GameRun) -> str:
        return render_draw_pile(run)

    @staticmethod
    def render_discard_pile(run: GameRun) -> str:
        return render_discard_pile(run)

    @staticmethod
    def render_exhaust_pile(run: GameRun) -> str:
        return render_exhaust_pile(run)

    @staticmethod
    def render_minion_graveyard(run: GameRun) -> str:
        return render_minion_graveyard(run)

    @staticmethod
    def render_enemy_graveyard(run: GameRun) -> str:
        return render_enemy_graveyard(run)
