import ast
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RUNTIME_DIRS = ["game/core", "game/entities", "game/models", "game/renderer", "server"]
SCAN_DIRS = ["game", "server"]
CHINESE = re.compile(r"[\u4e00-\u9fff]")
KEY_CALL = re.compile(r"(?:get_locale_text|get_text|\bt)\(\s*[\"']([^\"']+)[\"']")
REGISTRY_CALLS = {
    "register_enemy",
    "register_card",
    "register_relic",
    "register_buff",
    "register_amulet",
    "register_minion",
    "register_event",
    "register_command",
    "register_action",
    "register_potion",
}
ALIAS_KEYWORDS = {"names", "aliases", "ids", "actions", "command_ids"}
STATE_CALLS = {"EnemyState", "PlayerState", "BuffState", "MinionState", "AmuletState"}
IDENTIFIER_VALUES = {"选择", "随从 ", "使用 "}
IDENTIFIER_DICT_KEYS = {"id", "name", "key", "action", "type", "class", "subclass"}
STRUCTURAL_CALLS = {
    "replace_structured_number",
    "adjust_intent_desc_with_modifiers",
    "append_card_suffix",
    "startswith",
    "split",
    "find",
    "replace",
    "get",
    "getattr",
}


def iter_py(base):
    for path, dirs, files in os.walk(os.path.join(ROOT, base)):
        dirs[:] = [name for name in dirs if name != "__pycache__"]
        for name in files:
            if name.endswith(".py") and not relative(os.path.join(path, name)).startswith("game/test/"):
                yield os.path.join(path, name)


def relative(path):
    return os.path.relpath(path, ROOT).replace("\\", "/")


def is_runtime(path):
    rel = relative(path)
    return any(rel.startswith(base + "/") for base in RUNTIME_DIRS)


def call_name(node):
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return ""


def parents_map(tree):
    parents = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    return parents


def assigned_names(node, parents):
    names = []
    current = parents.get(node)
    while current is not None:
        if isinstance(current, (ast.Assign, ast.AnnAssign)):
            targets = current.targets if isinstance(current, ast.Assign) else [current.target]
            for target in targets:
                if isinstance(target, ast.Name):
                    names.append(target.id)
        elif isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            break
        current = parents.get(current)
    return names


def is_identifier_string(node, parents):
    if node.value in IDENTIFIER_VALUES:
        return True
    parent = parents.get(node)
    if isinstance(parent, ast.Dict) and node in parent.keys:
        return True
    if isinstance(parent, ast.Dict) and node in parent.values:
        for key, value in zip(parent.keys, parent.values):
            if value is node and isinstance(key, ast.Constant) and key.value in IDENTIFIER_DICT_KEYS:
                return True
    if isinstance(parent, ast.keyword) and parent.arg in ALIAS_KEYWORDS:
        return True
    if isinstance(parent, ast.keyword) and parent.arg == "name":
        grand = parents.get(parent)
        if isinstance(grand, ast.Call) and call_name(grand) in STATE_CALLS:
            return True
    if isinstance(parent, ast.Call) and (
        call_name(parent) in REGISTRY_CALLS or call_name(parent) in STRUCTURAL_CALLS
    ):
        return True
    if isinstance(parent, ast.Compare):
        return True
    if isinstance(parent, ast.Subscript):
        return True
    if isinstance(parent, ast.Assign):
        for target in parent.targets:
            if isinstance(target, ast.Attribute) and target.attr in ("name", "selected_class", "selected_subclass"):
                return True
    if isinstance(parent, (ast.List, ast.Tuple, ast.Set)):
        grand = parents.get(parent)
        if isinstance(grand, ast.Compare):
            return True
        if isinstance(grand, ast.keyword) and grand.arg in ALIAS_KEYWORDS:
            return True
        if isinstance(grand, ast.Call) and (
            call_name(grand) in REGISTRY_CALLS or call_name(grand) in STRUCTURAL_CALLS
        ):
            return True
        if isinstance(grand, ast.For):
            return True
    for name in assigned_names(node, parents):
        upper = name.upper()
        if any(part in upper for part in ("ID", "IDS", "ALIAS", "ACTION", "CLASS", "KEY", "NAME", "COMMAND", "OPTIONS", "PATTERN", "PARTS")):
            return True
    return False


def scan_files():
    problems = []
    total_chinese = 0
    total_files = 0
    for base in SCAN_DIRS:
        for path in iter_py(base):
            with open(path, "r", encoding="utf-8") as handle:
                text = handle.read()
            lines = text.splitlines()
            if len(lines) > 1000:
                problems.append(f"{relative(path)}: {len(lines)} lines")
            for index, line in enumerate(lines, 1):
                if line.lstrip().startswith("#"):
                    problems.append(f"{relative(path)}:{index}: comment")
                if "from_cid" in line:
                    problems.append(f"{relative(path)}:{index}: from_cid")
                if "_getframe" in line:
                    problems.append(f"{relative(path)}:{index}: _getframe")
                if re.search(r"except\s*:", line):
                    problems.append(f"{relative(path)}:{index}: bare except")
            try:
                tree = ast.parse(text)
            except SyntaxError as exc:
                problems.append(f"{relative(path)}: syntax {exc}")
                continue
            if is_runtime(path):
                found = 0
                parents = parents_map(tree)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Constant) and isinstance(node.value, str):
                        if CHINESE.search(node.value) and not is_identifier_string(node, parents):
                            problems.append(f"{relative(path)}:{node.lineno}: chinese literal")
                            found += 1
                if found:
                    total_files += 1
                    total_chinese += found
    return problems, total_files, total_chinese


def scan_locale_keys():
    sys.path.insert(0, ROOT)
    from game.core.i18n.locale_manager import LocaleManager
    LocaleManager.load_locale("zh_cn")
    data = LocaleManager.get_all_translations()
    missing = []
    for base in RUNTIME_DIRS:
        for path in iter_py(base):
            with open(path, "r", encoding="utf-8") as handle:
                text = handle.read()
            for key in KEY_CALL.findall(text):
                if key.endswith("."):
                    continue
                current = data
                found = True
                for part in key.split("."):
                    if isinstance(current, dict) and part in current:
                        current = current[part]
                    else:
                        found = False
                        break
                if not found:
                    missing.append(f"{relative(path)}: {key}")
    from game.data.grid_map_config import (
        DIRECT_REVEAL_ADJACENT_TYPES,
        LANDMARK_CONFIGS,
        PASSABLE_ROOM_TYPES,
        PERMANENT_ICON_TYPES,
        QUEST_RELIC_CONFIG,
        ROOM_ICONS,
        SECRET_RITUAL_PROTOCOLS,
    )
    from game.data.room_interact_data import OBSTACLE_STYLES, ROGUE_ITEMS, ROOM_ENVIRONMENTS, ROOM_NPCS, ROOM_PROPS
    from game.core.cli import command_router
    from game.core.cli.base import CommandHandler

    def _has_key(key_path):
        cur = data
        for part in key_path.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                return False
        return True

    room_types = set(ROOM_ICONS) | set(PASSABLE_ROOM_TYPES) | set(DIRECT_REVEAL_ADJACENT_TYPES) | set(PERMANENT_ICON_TYPES)
    for rtype in sorted(room_types):
        for prefix in ("i18n_grid_map.room_name", "i18n_grid_map.legend"):
            k = f"{prefix}.{rtype}"
            if not _has_key(k):
                missing.append(f"dynamic_config: {k}")

    for qcfg in QUEST_RELIC_CONFIG.values():
        for fld in ("name_key", "desc_key"):
            if not _has_key(qcfg[fld]):
                missing.append(f"dynamic_config: {qcfg[fld]}")
    for lcfg in LANDMARK_CONFIGS.values():
        for fld in ("name_key", "desc_key", "npc_key"):
            if not _has_key(lcfg[fld]):
                missing.append(f"dynamic_config: {lcfg[fld]}")
    for proto in (*SECRET_RITUAL_PROTOCOLS, "awakened_compass"):
        k = f"i18n_grid_map.ritual_protocol.{proto}"
        if not _has_key(k):
            missing.append(f"dynamic_config: {k}")

    for envs in ROOM_ENVIRONMENTS.values():
        for env_id in envs:
            k = f"i18n_room_interact.env.{env_id}"
            if not _has_key(k):
                missing.append(f"dynamic_config: {k}")
    for pid, pcfg in ROOM_PROPS.items():
        for k in (pcfg["name_key"], f"i18n_room_interact.props.{pid}.scene", f"i18n_room_interact.props.{pid}.done_scene"):
            if not _has_key(k):
                missing.append(f"dynamic_config: {k}")
    for ncfg in ROOM_NPCS.values():
        if not _has_key(ncfg["name_key"]):
            missing.append(f"dynamic_config: {ncfg['name_key']}")
    for ocfg in OBSTACLE_STYLES.values():
        if not _has_key(ocfg["name_key"]):
            missing.append(f"dynamic_config: {ocfg['name_key']}")
    for icfg in ROGUE_ITEMS.values():
        for fld in ("name_key", "desc_key"):
            if not _has_key(icfg[fld]):
                missing.append(f"dynamic_config: {icfg[fld]}")

    from game.data.item_lore_data import ITEM_LORE
    from game.core.inventory.item_lore import REVEAL_RULES
    for ilore in ITEM_LORE.values():
        if not _has_key(ilore["intro_key"]):
            missing.append(f"dynamic_config: {ilore['intro_key']}")
        secret_cfg = ilore.get("secret")
        if secret_cfg:
            for fld in ("hint_key", "reveal_key"):
                if not _has_key(secret_cfg[fld]):
                    missing.append(f"dynamic_config: {secret_cfg[fld]}")
        for rule in (ilore.get("hidden"), (secret_cfg or {}).get("reveal")):
            if rule and rule not in REVEAL_RULES:
                missing.append(f"dynamic_config: reveal rule {rule}")

    for cls in set(CommandHandler.registry.values()):
        for st in getattr(cls, "allowed_states", []):
            k = f"i18n_help.state_{st}"
            if not _has_key(k):
                missing.append(f"dynamic_config: {k}")
        hk = getattr(cls, "help_key", None)
        if hk:
            for sub in ("name", "usage", "brief", "desc", "example"):
                k = f"i18n_help.commands.{hk}.{sub}"
                if not _has_key(k):
                    missing.append(f"dynamic_config: {k}")

    return missing


def main():
    problems, files, lines = scan_files()
    missing = scan_locale_keys()
    for item in problems[:200]:
        print(item)
    for item in missing[:200]:
        print("missing locale key", item)
    print(f"chinese_runtime_files={files} chinese_runtime_lines={lines}")
    print(f"problems={len(problems)} missing_keys={len(missing)}")
    return 1 if problems or missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
