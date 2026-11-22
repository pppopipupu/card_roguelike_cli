from ..text.locale_data import get_locale_text

DEFAULT_SIZE = "medium"

SIZE_KEYS = (
    "micro",
    "tiny",
    "small",
    "medium",
    "large",
    "huge",
    "gargantuan",
    "colossal",
    "not_applicable",
)

SIZE_ORDER = {
    "micro": 0,
    "tiny": 1,
    "small": 2,
    "medium": 3,
    "large": 4,
    "huge": 5,
    "gargantuan": 6,
    "colossal": 7,
}

TEST_ENEMY_SIZES = {
    "测试假人": "medium",
    "备用假人": "medium",
    "木桩": "medium",
    "新手训练木偶": "medium",
}

NON_CONFIG_ENEMY_SIZES = {
    "Gate_Guardian": "large",
    "【觉醒】pppopipupu": "micro",
    "【万物归一】虚空之门·尤格-索托斯": "colossal",
    "时空残影": "not_applicable",
    "星辉教团·持烛教徒": "medium",
    "咏唱者": "medium",
    "执刃者": "medium",
    "守夜人": "medium",
    "疯癫祭司": "medium",
    "内殿守卫": "large",
    "镜中残影": "not_applicable",
    "叛教哨兵": "medium",
    "雪原狼": "medium",
    "霜牙巨狼": "large",
    "冰封少女·欧吕尔的化身": "gargantuan",
    "噬念心魔": "medium",
    "静默守门者": "large",
    "锻炉残响": "huge",
    "狂怒铁匠·托林": "medium",
    "黑市掮客·莫斯": "medium",
    "狂乱学者·艾拉": "medium",
    "绝望斥候·里昂": "medium",
    "幽暗守坛人·赛伦": "medium",
    "秘境行商·维克多": "medium",
    "暴走店长·布鲁诺": "medium",
}


def normalize_size(value: str | None) -> str:
    if not value:
        return DEFAULT_SIZE
    cleaned = str(value).strip()
    lowered = cleaned.lower()
    if lowered in SIZE_KEYS:
        return lowered
    for key in SIZE_KEYS:
        if get_locale_text(f"i18n_size.names.{key}") == cleaned:
            return key
    return DEFAULT_SIZE


def get_size_label(value: str | None) -> str:
    return get_locale_text(f"i18n_size.names.{normalize_size(value)}")


def is_size_at_most(value: str | None, max_size: str = "large") -> bool:
    canon = normalize_size(value)
    limit = normalize_size(max_size)
    if canon not in SIZE_ORDER or limit not in SIZE_ORDER:
        return False
    return SIZE_ORDER[canon] <= SIZE_ORDER[limit]


def resolve_enemy_size(name: str, explicit_size: str | None = None) -> str:
    if explicit_size:
        return normalize_size(explicit_size)
    from ..enemies.enemy_data import ENEMY_CONFIG
    cfg = ENEMY_CONFIG.get(name)
    if cfg and cfg.get("size"):
        return normalize_size(cfg["size"])
    if name in NON_CONFIG_ENEMY_SIZES:
        return normalize_size(NON_CONFIG_ENEMY_SIZES[name])
    if name in TEST_ENEMY_SIZES:
        return normalize_size(TEST_ENEMY_SIZES[name])
    return DEFAULT_SIZE


def resolve_minion_size(minion_id: str, name: str = "", explicit_size: str | None = None) -> str:
    if explicit_size:
        return normalize_size(explicit_size)
    from .minions.minion_data import MINION_CONFIG
    base_id = minion_id[:-1] if minion_id.endswith("+") and minion_id not in MINION_CONFIG else minion_id
    cfg = MINION_CONFIG.get(minion_id) or MINION_CONFIG.get(base_id)
    if cfg and cfg.get("size"):
        return normalize_size(cfg["size"])
    return DEFAULT_SIZE
