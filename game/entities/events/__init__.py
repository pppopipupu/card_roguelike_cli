from typing import Optional
from ...data.map_config import MapConfig
from .base import EventOption, EventTemplate
from .registry import EVENT_OPTIONS_REGISTRY
from ...data.event_data import EVENT_CONFIG
from ...data.locale_data import get_locale_text

from .fountain import *
from .knight import *
from .altar import *
from .lost_maze import *
from .abandoned_mine import *
from .phantom_mage import *
from .goblin_gamble import *
from .fairy_tea import *
from .void_contract import *
from .forge_furnace import *
from .leave import *
from .portal_chamber import *
from .chaos_events import *


ALL_EVENTS = [
    EventTemplate(
        "fountain",
        EVENT_CONFIG["fountain"]["description"],
        [
            DrinkFountainOption(get_locale_text("i18n_events_c.opt_fountain_drink"), "drink_fountain"),
            CoinFountainOption(get_locale_text("i18n_events_c.opt_fountain_coin"), "coin_fountain"),
            ObserveFountainOption(get_locale_text("i18n_events_c.opt_fountain_observe"), "observe_fountain"),
            LeaveEventOption(get_locale_text("i18n_events_c.opt_leave_quiet"), "leave_event", "fountain")
        ]
    ),
    EventTemplate(
        "knight",
        EVENT_CONFIG["knight"]["description"],
        [
            HelpKnightOption(get_locale_text("i18n_events_c.opt_knight_help"), "help_knight"),
            RobKnightOption(get_locale_text("i18n_events_c.opt_knight_rob"), "rob_knight"),
            AskKnightOption(get_locale_text("i18n_events_c.opt_knight_ask"), "ask_knight"),
            LeaveEventOption(get_locale_text("i18n_events_c.opt_knight_ignore"), "leave_event", "knight")
        ]
    ),
    EventTemplate(
        "altar",
        EVENT_CONFIG["altar"]["description"],
        [
            AbsorbAltarOption(get_locale_text("i18n_events_c.opt_altar_absorb"), "absorb_altar"),
            BreakAltarOption(get_locale_text("i18n_events_c.opt_altar_break"), "break_altar"),
            MeditateAltarOption(get_locale_text("i18n_events_c.opt_altar_meditate"), "meditate_altar"),
            LeaveEventOption(get_locale_text("i18n_events_c.opt_altar_detour"), "leave_event", "altar")
        ]
    ),
    EventTemplate(
        "lost_maze",
        EVENT_CONFIG["lost_maze"]["description"],
        [
            MazeFireOption(get_locale_text("i18n_events_c.opt_maze_fire"), "maze_fire"),
            MazeWaterOption(get_locale_text("i18n_events_c.opt_maze_water"), "maze_water"),
            MazeMarkOption(get_locale_text("i18n_events_c.opt_maze_mark"), "maze_mark")
        ]
    ),
    EventTemplate(
        "abandoned_mine",
        EVENT_CONFIG["abandoned_mine"]["description"],
        [
            RideCartOption(get_locale_text("i18n_events_c.opt_mine_cart"), "ride_cart"),
            ClimbLadderOption(get_locale_text("i18n_events_c.opt_mine_ladder"), "climb_ladder")
        ]
    ),
    EventTemplate(
        "phantom_mage",
        EVENT_CONFIG["phantom_mage"]["description"],
        [
            ReadScrollOption(get_locale_text("i18n_events_c.opt_phantom_read"), "read_scroll"),
            ResonateScrollOption(get_locale_text("i18n_events_c.opt_phantom_resonate"), "resonate_scroll"),
            DispelPhantomOption(get_locale_text("i18n_events_c.opt_phantom_dispel"), "dispel_phantom"),
            LeaveEventOption(get_locale_text("i18n_events_c.opt_leave_quiet"), "leave_event", "phantom_mage")
        ]
    ),
    EventTemplate(
        "goblin_gamble",
        EVENT_CONFIG["goblin_gamble"]["description"],
        [
            GambleSmallOption(get_locale_text("i18n_events_c.opt_goblin_small"), "gamble_small"),
            GambleLargeOption(get_locale_text("i18n_events_c.opt_goblin_large"), "gamble_large"),
            RobGoblinOption(get_locale_text("i18n_events_c.opt_goblin_rob"), "rob_goblin"),
            LeaveEventOption(get_locale_text("i18n_events_c.opt_goblin_refuse"), "leave_event", "goblin_gamble")
        ]
    ),
    EventTemplate(
        "fairy_tea",
        EVENT_CONFIG["fairy_tea"]["description"],
        [
            DrinkNectarOption(get_locale_text("i18n_events_c.opt_fairy_nectar"), "drink_nectar"),
            EatCookieOption(get_locale_text("i18n_events_c.opt_fairy_cookie"), "eat_cookie"),
            ListenMusicOption(get_locale_text("i18n_events_c.opt_fairy_music"), "listen_music"),
            LeaveEventOption(get_locale_text("i18n_events_c.opt_fairy_decline"), "leave_event", "fairy_tea")
        ],
        min_stage=2,
        max_stage=12
    ),
    EventTemplate(
        "void_contract",
        EVENT_CONFIG["void_contract"]["description"],
        [
            ContractRelicOption(get_locale_text("i18n_events_c.opt_contract_relic"), "contract_relic"),
            ContractLegendOption(get_locale_text("i18n_events_c.opt_contract_legend"), "contract_legend"),
            AbsorbVoidOption(get_locale_text("i18n_events_c.opt_absorb_void"), "absorb_void"),
            LeaveEventOption(get_locale_text("i18n_events_c.opt_contract_refuse"), "leave_event", "void_contract")
        ],
        min_stage=14,
        max_stage=MapConfig.COMMON_EVENT_MAX_STAGE
    ),
    EventTemplate(
        "forge_furnace",
        EVENT_CONFIG["forge_furnace"]["description"],
        [
            ForgeFireOption(get_locale_text("i18n_events_c.opt_forge_fire"), "forge_fire"),
            OverloadForgeOption(get_locale_text("i18n_events_c.opt_forge_overload"), "overload_forge"),
            ForgeBackfireOption(get_locale_text("i18n_events_c.opt_forge_backfire"), "forge_backfire"),
            ShatterForgeOption(get_locale_text("i18n_events_c.opt_forge_shatter"), "shatter_forge"),
            LeaveEventOption(get_locale_text("i18n_events_c.opt_forge_leave"), "leave_event", "forge_furnace")
        ],
        min_stage=2,
        max_stage=MapConfig.COMMON_EVENT_MAX_STAGE
    ),
    EventTemplate(
        "portal_chamber",
        EVENT_CONFIG["portal_chamber"]["description"],
        [
            ContractPortalOption(get_locale_text("i18n_events_c.opt_portal_contract"), "contract_portal"),
            ArcanePortalOption(get_locale_text("i18n_events_c.opt_portal_arcane"), "arcane_portal"),
            LeaveEventOption(get_locale_text("i18n_events_c.opt_portal_leave"), "leave_event", "portal_chamber")
        ],
        min_stage=27,
        max_stage=30
    ),
    EventTemplate(
        "void_library",
        EVENT_CONFIG["void_library"]["description"],
        [
            ReadVoidTomeOption(get_locale_text("i18n_events_c.opt_library_read"), "read_void_tome"),
            BurnVoidBooksOption(get_locale_text("i18n_events_c.opt_library_burn"), "burn_void_books"),
            SacrificeMindOption(get_locale_text("i18n_events_c.opt_library_sacrifice"), "sacrifice_mind")
        ],
        min_stage=6,
        max_stage=16
    ),
    EventTemplate(
        "goblin_blackmarket",
        EVENT_CONFIG["goblin_blackmarket"]["description"],
        [
            BuyBlackmarketRelicOption(get_locale_text("i18n_events_c.opt_blackmarket_buy"), "buy_blackmarket_relic"),
            RobBlackmarketOption(get_locale_text("i18n_events_c.opt_blackmarket_rob"), "rob_blackmarket"),
            SellFleshOption(get_locale_text("i18n_events_c.opt_blackmarket_sell"), "sell_flesh")
        ],
        min_stage=14,
        max_stage=MapConfig.COMMON_EVENT_MAX_STAGE
    ),
    EventTemplate(
        "time_fountain_trial",
        EVENT_CONFIG["time_fountain_trial"]["description"],
        [
            DrinkTimeSandOption(get_locale_text("i18n_events_c.opt_time_sand"), "drink_time_sand"),
            AccelerateCinderOption(get_locale_text("i18n_events_c.opt_time_accelerate"), "accelerate_cinder"),
            TouchTimeRiftOption(get_locale_text("i18n_events_c.opt_time_rift"), "touch_time_rift")
        ],
        min_stage=27,
        max_stage=31
    ),
    EventTemplate(
        "astral_caravan_disaster",
        EVENT_CONFIG["astral_caravan_disaster"]["description"],
        [
            LootWreckageOption(get_locale_text("i18n_events_c.opt_caravan_loot"), "loot_wreckage"),
            RepairEngineOption(get_locale_text("i18n_events_c.opt_caravan_repair"), "repair_engine"),
            BraveStormOption(get_locale_text("i18n_events_c.opt_caravan_storm"), "brave_storm")
        ],
        min_stage=27,
        max_stage=30
    ),
    EventTemplate(
        "nameless_tombstone",
        EVENT_CONFIG["nameless_tombstone"]["description"],
        [
            DigGraveOption(get_locale_text("i18n_events_c.opt_tomb_dig"), "dig_grave"),
            ReadEpitaphOption(get_locale_text("i18n_events_c.opt_tomb_read"), "read_epitaph"),
            CarveOwnNameOption(get_locale_text("i18n_events_c.opt_tomb_carve"), "carve_own_name")
        ],
        min_stage=30,
        max_stage=31
    )
]

def get_option_by_action(action: str) -> Optional[EventOption]:
    cls = EVENT_OPTIONS_REGISTRY.get(action)
    if cls:
        return cls()
    return None
