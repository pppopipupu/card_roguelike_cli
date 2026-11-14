from ...data.minion_data import MINION_CONFIG
from .minion_base import MinionTemplate
from .basic_minions import (
    CardsPlayedEntryDamageTemplate,
    FamiliarAssist,
    FamiliarCharge,
    GateGuardStrike,
    GateGuardTemplate,
    GolemOverload,
    GolemRepair,
    IcerainbowwShield,
    IcerainbowwSpray,
    MercenaryBattlecry,
    MercenaryHeavyStrike,
    MercenaryTemplate,
    ShieldGuardBash,
    ShieldGuardDefend,
    ShieldGuardTemplate,
    WaterLance,
    WaterTouch,
)
from .officer_minions import (
    AuroraEmperorJudgment,
    BannerBearerBuff,
    BannerBearerTemplate,
    BladeDancerSlash,
    BladeDancerTemplate,
    CommanderPatrolCaptainTemplate,
    GarrisonLeaderTemplate,
    GarrisonLeaderWall,
    PatrolCaptainOrder,
    RecruitVanguardTemplate,
    RoyalGuardTemplate,
    SoldierTokenTemplate,
    SquadSkirmisherTemplate,
    SteelcladTacticianStrike,
    SteelcladTacticianTemplate,
    ValiantHeraldSignal,
    ValiantHeraldTemplate,
)
from .anna_minions import AnneVanishSkill

ALL_MINIONS = {
    "mercenary": MercenaryTemplate(
        "mercenary",
        MINION_CONFIG["mercenary"]["name"],
        [
            MercenaryHeavyStrike(
                MINION_CONFIG["mercenary"]["skills"][0]["name"],
                MINION_CONFIG["mercenary"]["skills"][0]["cost_a"],
                MINION_CONFIG["mercenary"]["skills"][0]["cost_ba"],
                MINION_CONFIG["mercenary"]["skills"][0]["desc"]
            ),
            MercenaryBattlecry(
                MINION_CONFIG["mercenary"]["skills"][1]["name"],
                MINION_CONFIG["mercenary"]["skills"][1]["cost_a"],
                MINION_CONFIG["mercenary"]["skills"][1]["cost_ba"],
                MINION_CONFIG["mercenary"]["skills"][1]["desc"]
            )
        ]
    ),
    "shield_guard": ShieldGuardTemplate(
        "shield_guard",
        MINION_CONFIG["shield_guard"]["name"],
        [
            ShieldGuardDefend(
                MINION_CONFIG["shield_guard"]["skills"][0]["name"],
                MINION_CONFIG["shield_guard"]["skills"][0]["cost_a"],
                MINION_CONFIG["shield_guard"]["skills"][0]["cost_ba"],
                MINION_CONFIG["shield_guard"]["skills"][0]["desc"]
            ),
            ShieldGuardBash(
                MINION_CONFIG["shield_guard"]["skills"][1]["name"],
                MINION_CONFIG["shield_guard"]["skills"][1]["cost_a"],
                MINION_CONFIG["shield_guard"]["skills"][1]["cost_ba"],
                MINION_CONFIG["shield_guard"]["skills"][1]["desc"]
            )
        ]
    ),
    "find_familiar": MinionTemplate(
        "find_familiar",
        MINION_CONFIG["find_familiar"]["name"],
        [
            FamiliarAssist(
                MINION_CONFIG["find_familiar"]["skills"][0]["name"],
                MINION_CONFIG["find_familiar"]["skills"][0]["cost_a"],
                MINION_CONFIG["find_familiar"]["skills"][0]["cost_ba"],
                MINION_CONFIG["find_familiar"]["skills"][0]["desc"]
            ),
            FamiliarCharge(
                MINION_CONFIG["find_familiar"]["skills"][1]["name"],
                MINION_CONFIG["find_familiar"]["skills"][1]["cost_a"],
                MINION_CONFIG["find_familiar"]["skills"][1]["cost_ba"],
                MINION_CONFIG["find_familiar"]["skills"][1]["desc"]
            )
        ]
    ),
    "water_elemental": MinionTemplate(
        "water_elemental",
        MINION_CONFIG["water_elemental"]["name"],
        [
            WaterTouch(
                MINION_CONFIG["water_elemental"]["skills"][0]["name"],
                MINION_CONFIG["water_elemental"]["skills"][0]["cost_a"],
                MINION_CONFIG["water_elemental"]["skills"][0]["cost_ba"],
                MINION_CONFIG["water_elemental"]["skills"][0]["desc"]
            ),
            WaterLance(
                MINION_CONFIG["water_elemental"]["skills"][1]["name"],
                MINION_CONFIG["water_elemental"]["skills"][1]["cost_a"],
                MINION_CONFIG["water_elemental"]["skills"][1]["cost_ba"],
                MINION_CONFIG["water_elemental"]["skills"][1]["desc"]
            )
        ]
    ),
    "arcane_golem": MinionTemplate(
        "arcane_golem",
        MINION_CONFIG["arcane_golem"]["name"],
        [
            GolemOverload(
                MINION_CONFIG["arcane_golem"]["skills"][0]["name"],
                MINION_CONFIG["arcane_golem"]["skills"][0]["cost_a"],
                MINION_CONFIG["arcane_golem"]["skills"][0]["cost_ba"],
                MINION_CONFIG["arcane_golem"]["skills"][0]["desc"]
            ),
            GolemRepair(
                MINION_CONFIG["arcane_golem"]["skills"][1]["name"],
                MINION_CONFIG["arcane_golem"]["skills"][1]["cost_a"],
                MINION_CONFIG["arcane_golem"]["skills"][1]["cost_ba"],
                MINION_CONFIG["arcane_golem"]["skills"][1]["desc"]
            )
        ]
    ),
    "minion_icerainboww": MinionTemplate(
        "minion_icerainboww",
        MINION_CONFIG["minion_icerainboww"]["name"],
        [
            IcerainbowwSpray(
                MINION_CONFIG["minion_icerainboww"]["skills"][0]["name"],
                MINION_CONFIG["minion_icerainboww"]["skills"][0]["cost_a"],
                MINION_CONFIG["minion_icerainboww"]["skills"][0]["cost_ba"],
                MINION_CONFIG["minion_icerainboww"]["skills"][0]["desc"]
            ),
            IcerainbowwShield(
                MINION_CONFIG["minion_icerainboww"]["skills"][1]["name"],
                MINION_CONFIG["minion_icerainboww"]["skills"][1]["cost_a"],
                MINION_CONFIG["minion_icerainboww"]["skills"][1]["cost_ba"],
                MINION_CONFIG["minion_icerainboww"]["skills"][1]["desc"]
            )
        ]
    ),
    "gate_guard": GateGuardTemplate(
        "gate_guard",
        MINION_CONFIG["gate_guard"]["name"],
        [
            GateGuardStrike(
                MINION_CONFIG["gate_guard"]["skills"][0]["name"],
                MINION_CONFIG["gate_guard"]["skills"][0]["cost_a"],
                MINION_CONFIG["gate_guard"]["skills"][0]["cost_ba"],
                MINION_CONFIG["gate_guard"]["skills"][0]["desc"]
            )
        ]
    ),
    "elf_archer_xiaomei": CardsPlayedEntryDamageTemplate(
        "elf_archer_xiaomei",
        MINION_CONFIG["elf_archer_xiaomei"]["name"],
        []
    ),
    "manaeria_queen_anne": MinionTemplate(
        "manaeria_queen_anne",
        MINION_CONFIG["manaeria_queen_anne"]["name"],
        [
            AnneVanishSkill(
                MINION_CONFIG["manaeria_queen_anne"]["skills"][0]["name"],
                MINION_CONFIG["manaeria_queen_anne"]["skills"][0]["cost_a"],
                MINION_CONFIG["manaeria_queen_anne"]["skills"][0]["cost_ba"],
                MINION_CONFIG["manaeria_queen_anne"]["skills"][0]["desc"],
            )
        ]
    ),
    "holy_celestial_millika": MinionTemplate(
        "holy_celestial_millika",
        MINION_CONFIG["holy_celestial_millika"]["name"],
        []
    ),
    "officer_recruit_vanguard": RecruitVanguardTemplate(
        "officer_recruit_vanguard",
        MINION_CONFIG["officer_recruit_vanguard"]["name"],
        []
    ),
    "officer_banner_bearer": BannerBearerTemplate(
        "officer_banner_bearer",
        MINION_CONFIG["officer_banner_bearer"]["name"],
        [
            BannerBearerBuff(
                MINION_CONFIG["officer_banner_bearer"]["skills"][0]["name"],
                MINION_CONFIG["officer_banner_bearer"]["skills"][0]["cost_a"],
                MINION_CONFIG["officer_banner_bearer"]["skills"][0]["cost_ba"],
                MINION_CONFIG["officer_banner_bearer"]["skills"][0]["desc"]
            )
        ]
    ),
    "commander_patrol_captain": CommanderPatrolCaptainTemplate(
        "commander_patrol_captain",
        MINION_CONFIG["commander_patrol_captain"]["name"],
        [
            PatrolCaptainOrder(
                MINION_CONFIG["commander_patrol_captain"]["skills"][0]["name"],
                MINION_CONFIG["commander_patrol_captain"]["skills"][0]["cost_a"],
                MINION_CONFIG["commander_patrol_captain"]["skills"][0]["cost_ba"],
                MINION_CONFIG["commander_patrol_captain"]["skills"][0]["desc"]
            )
        ]
    ),
    "officer_royal_guard": RoyalGuardTemplate(
        "officer_royal_guard",
        MINION_CONFIG["officer_royal_guard"]["name"],
        []
    ),
    "commander_garrison_leader": GarrisonLeaderTemplate(
        "commander_garrison_leader",
        MINION_CONFIG["commander_garrison_leader"]["name"],
        [
            GarrisonLeaderWall(
                MINION_CONFIG["commander_garrison_leader"]["skills"][0]["name"],
                MINION_CONFIG["commander_garrison_leader"]["skills"][0]["cost_a"],
                MINION_CONFIG["commander_garrison_leader"]["skills"][0]["cost_ba"],
                MINION_CONFIG["commander_garrison_leader"]["skills"][0]["desc"]
            )
        ]
    ),
    "officer_squad_skirmisher": SquadSkirmisherTemplate(
        "officer_squad_skirmisher",
        MINION_CONFIG["officer_squad_skirmisher"]["name"],
        []
    ),
    "commander_valiant_herald": ValiantHeraldTemplate(
        "commander_valiant_herald",
        MINION_CONFIG["commander_valiant_herald"]["name"],
        [
            ValiantHeraldSignal(
                MINION_CONFIG["commander_valiant_herald"]["skills"][0]["name"],
                MINION_CONFIG["commander_valiant_herald"]["skills"][0]["cost_a"],
                MINION_CONFIG["commander_valiant_herald"]["skills"][0]["cost_ba"],
                MINION_CONFIG["commander_valiant_herald"]["skills"][0]["desc"]
            )
        ]
    ),
    "commander_steelclad_tactician": SteelcladTacticianTemplate(
        "commander_steelclad_tactician",
        MINION_CONFIG["commander_steelclad_tactician"]["name"],
        [
            SteelcladTacticianStrike(
                MINION_CONFIG["commander_steelclad_tactician"]["skills"][0]["name"],
                MINION_CONFIG["commander_steelclad_tactician"]["skills"][0]["cost_a"],
                MINION_CONFIG["commander_steelclad_tactician"]["skills"][0]["cost_ba"],
                MINION_CONFIG["commander_steelclad_tactician"]["skills"][0]["desc"]
            )
        ]
    ),
    "officer_blade_dancer": BladeDancerTemplate(
        "officer_blade_dancer",
        MINION_CONFIG["officer_blade_dancer"]["name"],
        [
            BladeDancerSlash(
                MINION_CONFIG["officer_blade_dancer"]["skills"][0]["name"],
                MINION_CONFIG["officer_blade_dancer"]["skills"][0]["cost_a"],
                MINION_CONFIG["officer_blade_dancer"]["skills"][0]["cost_ba"],
                MINION_CONFIG["officer_blade_dancer"]["skills"][0]["desc"]
            )
        ]
    ),
    "commander_aurora_emperor": MinionTemplate(
        "commander_aurora_emperor",
        MINION_CONFIG["commander_aurora_emperor"]["name"],
        [
            AuroraEmperorJudgment(
                MINION_CONFIG["commander_aurora_emperor"]["skills"][0]["name"],
                MINION_CONFIG["commander_aurora_emperor"]["skills"][0]["cost_a"],
                MINION_CONFIG["commander_aurora_emperor"]["skills"][0]["cost_ba"],
                MINION_CONFIG["commander_aurora_emperor"]["skills"][0]["desc"]
            )
        ]
    ),
    "officer_soldier_token": SoldierTokenTemplate(
        "officer_soldier_token",
        MINION_CONFIG["officer_soldier_token"]["name"],
        []
    ),
    "neutral_tau": MinionTemplate(
        "neutral_tau",
        MINION_CONFIG["neutral_tau"]["name"],
        []
    )
}

upgraded_minions = {}
for mid, temp in ALL_MINIONS.items():
    upgraded_id = f"{mid}+"
    if upgraded_id in MINION_CONFIG:
        upgraded_skills = []
        for idx, orig_skill in enumerate(temp.skills):
            SkillClass = orig_skill.__class__
            skill_cfg = MINION_CONFIG[upgraded_id]["skills"][idx]
            upgraded_skill = SkillClass(
                skill_cfg["name"],
                skill_cfg["cost_a"],
                skill_cfg["cost_ba"],
                skill_cfg["desc"]
            )
            upgraded_skills.append(upgraded_skill)
        upgraded_minions[upgraded_id] = MinionTemplate(
            upgraded_id,
            MINION_CONFIG[upgraded_id]["name"],
            upgraded_skills
        )
ALL_MINIONS.update(upgraded_minions)

MINION_SKILLS = {}
for mid, temp in ALL_MINIONS.items():
    MINION_SKILLS[mid] = [
        {"name": s.name, "cost_a": s.cost_a, "cost_ba": s.cost_ba, "desc": s.desc}
        for s in temp.skills
    ]
