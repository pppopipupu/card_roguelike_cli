import asyncio
import hmac
import threading
from dataclasses import dataclass

import jwt

from game.data.locale_data import get_locale_text

from .config import Settings


class AuthError(Exception):
    def __init__(self, message: str, status_code: int = 401, code: str = "auth"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code


@dataclass(frozen=True)
class Principal:
    kind: str
    user_id: str
    display_name: str = ""
    email: str = ""


def _display_name_from_claims(payload: dict) -> str:
    metadata = payload.get("user_metadata") or {}
    for key in ("user_name", "preferred_username", "full_name", "name"):
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()[:64]
    email = payload.get("email")
    if isinstance(email, str) and email:
        return email.split("@", 1)[0][:64]
    return ""


class AuthService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._lock = threading.Lock()
        self._jwks_client = jwt.PyJWKClient(
            settings.supabase_jwks_url,
            cache_keys=True,
            lifespan=300,
            timeout=10,
        )

    def _decode(self, token: str) -> dict:
        try:
            header = jwt.get_unverified_header(token)
        except jwt.PyJWTError as exc:
            raise AuthError(get_locale_text("i18n_server_core.auth.invalid_token")) from exc
        algorithm = header.get("alg", "")
        if algorithm == "HS256":
            if not self.settings.supabase_jwt_secret:
                raise AuthError(get_locale_text("i18n_server_core.auth.missing_hs256_secret"), 503)
            key = self.settings.supabase_jwt_secret
        else:
            if algorithm not in ("RS256", "ES256", "EdDSA"):
                raise AuthError(get_locale_text("i18n_server_core.auth.unsupported_algorithm"))
            try:
                key = self._jwks_client.get_signing_key_from_jwt(token).key
            except Exception as exc:
                raise AuthError(
                    get_locale_text("i18n_server_core.auth.jwks_fetch_failed"), 503
                ) from exc
        try:
            return jwt.decode(
                token,
                key,
                algorithms=[algorithm],
                audience=self.settings.supabase_jwt_audience,
                issuer=self.settings.supabase_jwt_issuer,
                options={"require": ["exp", "sub"]},
            )
        except jwt.PyJWTError as exc:
            raise AuthError(get_locale_text("i18n_server_core.auth.token_expired")) from exc

    async def verify_bearer(self, token: str) -> Principal:
        if not token:
            raise AuthError(get_locale_text("i18n_server_core.auth.missing_token"))
        payload = await asyncio.to_thread(self._verify_locked, token)
        subject = payload.get("sub")
        if not isinstance(subject, str) or not subject:
            raise AuthError(get_locale_text("i18n_server_core.auth.missing_subject"))
        return Principal(
            kind="web",
            user_id=subject,
            display_name=_display_name_from_claims(payload),
            email=payload.get("email") or "",
        )

    def _verify_locked(self, token: str) -> dict:
        with self._lock:
            return self._decode(token)

    def verify_im(self, token: str, im_user_id: str) -> Principal:
        if not self.settings.im_token:
            raise AuthError(get_locale_text("i18n_server_core.auth.im_disabled"), 503)
        if not token or not hmac.compare_digest(token, self.settings.im_token):
            raise AuthError(get_locale_text("i18n_server_core.auth.im_token_invalid"))
        if not im_user_id or len(im_user_id) > 128:
            raise AuthError(get_locale_text("i18n_server_core.auth.im_user_invalid"))
        return Principal(kind="im", user_id=im_user_id)

    def verify_admin(self, token: str) -> bool:
        if not self.settings.admin_token:
            return False
        if not token:
            return False
        return hmac.compare_digest(token, self.settings.admin_token)
