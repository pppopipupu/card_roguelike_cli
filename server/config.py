import os
from dataclasses import dataclass
from pathlib import Path


def _split(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(",") if part.strip())


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    db_path: Path
    player_dir: Path
    supabase_url: str
    supabase_jwks_url: str
    supabase_jwt_issuer: str
    supabase_jwt_audience: str
    supabase_jwt_secret: str
    im_token: str
    origin_key: str
    allowed_origins: tuple[str, ...]
    im_prefixes: tuple[str, ...]
    max_command_length: int = 4000

    @classmethod
    def from_env(cls) -> "Settings":
        root = Path(__file__).resolve().parent.parent
        data_dir = Path(os.getenv("ROGUE_DATA_DIR", str(root / "data" / "server"))).resolve()
        supabase_url = os.getenv(
            "SUPABASE_URL", "https://lwulrjhnzkjswhjqqbxg.supabase.co"
        ).rstrip("/")
        jwks_url = os.getenv(
            "SUPABASE_JWKS_URL", f"{supabase_url}/auth/v1/.well-known/jwks.json"
        )
        issuer = os.getenv("SUPABASE_JWT_ISSUER", f"{supabase_url}/auth/v1")
        audience = os.getenv("SUPABASE_JWT_AUD", "authenticated")
        origins = _split(
            os.getenv(
                "ROGUE_ALLOWED_ORIGINS",
                "http://localhost:5173,http://127.0.0.1:5173,https://rogue.114514256.xyz",
            )
        )
        prefixes = _split(os.getenv("ROGUE_IM_PREFIXES", ".rogue,/rogue"))
        return cls(
            data_dir=data_dir,
            db_path=Path(os.getenv("ROGUE_DB_PATH", str(data_dir / "accounts.sqlite3"))),
            player_dir=Path(os.getenv("ROGUE_PLAYER_DIR", str(data_dir / "players"))),
            supabase_url=supabase_url,
            supabase_jwks_url=jwks_url,
            supabase_jwt_issuer=issuer,
            supabase_jwt_audience=audience,
            supabase_jwt_secret=os.getenv("SUPABASE_JWT_SECRET", ""),
            im_token=os.getenv("ROGUE_IM_TOKEN", ""),
            origin_key=os.getenv("ROGUE_ORIGIN_KEY", ""),
            allowed_origins=origins,
            im_prefixes=prefixes,
            max_command_length=int(os.getenv("ROGUE_MAX_COMMAND_LENGTH", "4000")),
        )
