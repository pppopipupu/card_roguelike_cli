import argparse
import csv
import json
import re
import shutil
from pathlib import Path

from .accounts import AccountStore

PLAYER_FILE_PREFIXES = ("user_", "stats_", "duel_decks_")
PLAYER_FILE_PATTERN = re.compile(r"^(?:user|stats|duel_decks)_(.+)\.json$")
DUEL_GAME_PATTERN = re.compile(r"^duel_(?!registry|decks_).+\.json$")


def collect_ids(data_dir: Path) -> list[str]:
    ids: set[str] = set()
    if not data_dir.exists():
        return []
    for path in data_dir.iterdir():
        if not path.is_file():
            continue
        match = PLAYER_FILE_PATTERN.match(path.name)
        if match:
            ids.add(match.group(1))
    registry = data_dir / "duel_registry.json"
    if registry.exists():
        try:
            payload = json.loads(registry.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            payload = {}
        if isinstance(payload, dict):
            ids.update(str(key) for key in payload if str(key))
    return sorted(ids)


def read_display_name(data_dir: Path, legacy_id: str) -> str:
    path = data_dir / f"stats_{legacy_id}.json"
    if not path.exists():
        return legacy_id
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return legacy_id
    name = payload.get("player_name")
    if isinstance(name, str) and name.strip():
        return name.strip()[:64]
    return legacy_id


def copy_player_files(
    data_dir: Path,
    player_dir: Path,
    legacy_id: str,
    player_uuid: str,
    force: bool,
) -> list[str]:
    copied: list[str] = []
    for prefix in PLAYER_FILE_PREFIXES:
        source = data_dir / f"{prefix}{legacy_id}.json"
        if not source.exists():
            continue
        target = player_dir / f"{prefix}{player_uuid}.json"
        if target.exists() and not force:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied.append(target.name)
    return copied


def merge_duel_registry(
    data_dir: Path,
    player_dir: Path,
    mappings: dict[str, str],
    force: bool,
) -> int:
    source = data_dir / "duel_registry.json"
    if not source.exists():
        return 0
    try:
        legacy = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return 0
    if not isinstance(legacy, dict):
        return 0
    target = player_dir / "duel_registry.json"
    current: dict[str, str] = {}
    if target.exists():
        try:
            payload = json.loads(target.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                current = {str(key): str(value) for key, value in payload.items()}
        except (OSError, ValueError):
            current = {}
    changed = 0
    for legacy_id, game_id in legacy.items():
        player_uuid = mappings.get(str(legacy_id))
        if not player_uuid:
            continue
        if player_uuid in current and not force:
            continue
        value = str(game_id)
        if current.get(player_uuid) != value:
            current[player_uuid] = value
            changed += 1
    if changed:
        player_dir.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(current, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return changed


def copy_duel_games(data_dir: Path, player_dir: Path, force: bool) -> list[str]:
    copied: list[str] = []
    for source in data_dir.iterdir():
        if not source.is_file() or not DUEL_GAME_PATTERN.match(source.name):
            continue
        target = player_dir / source.name
        if target.exists() and not force:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied.append(target.name)
    return copied


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import legacy AstrBot players and save files into the backend."
    )
    parser.add_argument("--data-dir", required=True, help="Legacy plugin data directory")
    parser.add_argument("--db", required=True, help="accounts.sqlite3 path")
    parser.add_argument("--player-dir", required=True, help="New player save directory")
    parser.add_argument("--csv", required=True, help="Output CSV path")
    parser.add_argument(
        "--force", action="store_true", help="Overwrite existing target save files"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Print mappings without writing"
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    player_dir = Path(args.player_dir)
    legacy_ids = collect_ids(data_dir)
    rows: list[tuple[str, str, str, int]] = []
    mappings: dict[str, str] = {}
    copied_duels = 0
    registry_changed = 0

    if args.dry_run:
        for legacy_id in legacy_ids:
            rows.append(
                ("dry-run", legacy_id, read_display_name(data_dir, legacy_id), 0)
            )
    else:
        store = AccountStore(Path(args.db), player_dir)
        try:
            for legacy_id in legacy_ids:
                display_name = read_display_name(data_dir, legacy_id)
                existing = store.get_by_im(legacy_id)
                if existing:
                    store.touch(existing["uuid"], display_name)
                    account = store.get_by_im(legacy_id) or existing
                else:
                    account = store.get_or_create_im(legacy_id, display_name)
                player_uuid = account["uuid"]
                mappings[legacy_id] = player_uuid
                copied = copy_player_files(
                    data_dir, player_dir, legacy_id, player_uuid, args.force
                )
                rows.append(
                    (
                        player_uuid,
                        legacy_id,
                        account["display_name"] or "",
                        len(copied),
                    )
                )
            registry_changed = merge_duel_registry(
                data_dir, player_dir, mappings, args.force
            )
            copied_duels = len(copy_duel_games(data_dir, player_dir, args.force))
        finally:
            store.close()

    output = Path(args.csv)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["uuid", "im_user_id", "display_name", "copied_files"])
        writer.writerows(rows)

    print(
        f"imported={len(rows)} copied_duels={copied_duels} "
        f"registry_changed={registry_changed} csv={output}"
    )


if __name__ == "__main__":
    main()
