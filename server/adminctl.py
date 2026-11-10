import sys

from game.data.locale_data import get_locale_text

from .accounts import AccountStore
from .config import Settings


def _enabled(text: str) -> bool:
    return text.strip().lower() in ("on", "true", "1", "开启", "启用")


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(get_locale_text("i18n_server_core.adminctl.usage"))
        return 1
    action = argv[1].lower()
    settings = Settings.from_env()
    store = AccountStore(settings.db_path, settings.player_dir)
    try:
        if action == "list":
            print(get_locale_text("i18n_server_core.adminctl.list_header"))
            for row in store.list_all():
                status = get_locale_text(
                    "i18n_server_core.common.yes"
                    if row["is_admin"]
                    else "i18n_server_core.common.no"
                )
                print(
                    get_locale_text(
                        "i18n_server_core.adminctl.list_row",
                        uuid=row["uuid"],
                        im_user_id=row["im_user_id"] or "-",
                        web_user_id=row["web_user_id"] or "-",
                        is_admin=status,
                    )
                )
            return 0
        if action == "set" and len(argv) == 4:
            identity = argv[2]
            if not store.set_admin_by_identity(identity, _enabled(argv[3])):
                print(
                    get_locale_text(
                        "i18n_server_core.adminctl.not_found", identity=identity
                    )
                )
                return 1
            print(
                get_locale_text(
                    "i18n_server_core.adminctl.updated", identity=identity
                )
            )
            return 0
        print(get_locale_text("i18n_server_core.adminctl.usage"))
        return 1
    finally:
        store.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
