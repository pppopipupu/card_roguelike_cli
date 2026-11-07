import argparse
import csv
import re
from pathlib import Path

from .accounts import AccountStore

PATTERN = re.compile(r"^(?:user|stats)_(.+)\.json$")


def collect_ids(data_dir: Path) -> list[str]:
    ids: set[str] = set()
    if not data_dir.exists():
        return []
    for path in data_dir.iterdir():
        if not path.is_file():
            continue
        match = PATTERN.match(path.name)
        if match:
            ids.add(match.group(1))
    return sorted(ids)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import legacy AstrBot player IDs into the accounts database."
    )
    parser.add_argument("--data-dir", required=True, help="Legacy plugin data directory")
    parser.add_argument("--db", required=True, help="accounts.sqlite3 path")
    parser.add_argument("--player-dir", required=True, help="New player save directory")
    parser.add_argument("--csv", required=True, help="Output CSV path")
    parser.add_argument(
        "--dry-run", action="store_true", help="Print mappings without writing"
    )
    args = parser.parse_args()

    legacy_ids = collect_ids(Path(args.data_dir))
    rows: list[tuple[str, str]] = []

    if args.dry_run:
        for legacy_id in legacy_ids:
            rows.append(("dry-run", legacy_id))
    else:
        store = AccountStore(Path(args.db), Path(args.player_dir))
        try:
            for legacy_id in legacy_ids:
                existing = store.get_by_im(legacy_id)
                account = existing or store.get_or_create_im(legacy_id)
                rows.append((account["uuid"], legacy_id))
        finally:
            store.close()

    output = Path(args.csv)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["uuid", "im_user_id"])
        writer.writerows(rows)

    print(f"imported={len(rows)} csv={output}")


if __name__ == "__main__":
    main()
