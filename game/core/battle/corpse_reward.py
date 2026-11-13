import random

from ...data.corpse_config import CorpseConfig
from ...data.locale_data import get_locale_text
from ...models.state import GameRun


def handle_corpse_win(owner, run: GameRun):
    corpse_id = run.node_data.get("corpse_id")
    dead_name = str(run.node_data.get("corpse_dead_name", get_locale_text("i18n_battle_misc.corpse_default_dead_name")))
    cause = str(run.node_data.get("corpse_cause", get_locale_text("i18n_battle_misc.corpse_default_cause")))
    corpse = owner.engine.save_manager.corpses.claim(corpse_id, run.user_id)
    map_engine = getattr(owner.engine, "map_engine", None)
    if not corpse:
        if map_engine is not None:
            map_engine.return_to_grid_map(run)
            run.node_data["notice"] = get_locale_text("i18n_battle_misc.corpse_already_looted")
        else:
            run.node_type = "grid_map"
            run.node_data = {}
        owner.engine.save_manager.save_save(run.user_id, run)
        return
    gp_reward = int(corpse.get("gp_reward", 0))
    stats = owner.engine.save_manager.load_stats(run.user_id)
    stats.gp += gp_reward
    owner.engine.save_manager.save_stats(run.user_id, stats)
    deck = list(corpse.get("deck", []))
    cards = random.sample(deck, min(CorpseConfig.REWARD_CARD_POOL, len(deck))) if deck else []
    run.node_type = "corpse_reward"
    run.enemies.clear()
    run.node_data = {
        "corpse_reward": True,
        "corpse_id": corpse_id,
        "dead_name": dead_name,
        "cause": cause,
        "gp": gp_reward,
        "cards": cards,
        "picks_left": CorpseConfig.REWARD_CARD_PICKS,
        "picked": [],
        "notice": get_locale_text(
            "i18n_battle_misc.corpse_reward_notice",
            dead_name=dead_name,
            gp_reward=gp_reward,
            cause=cause,
            picks=CorpseConfig.REWARD_CARD_PICKS,
        ),
    }
    owner.engine.save_manager.save_save(run.user_id, run)
    owner.engine.save_manager.corpses.remove(corpse_id)
