import hmac
import logging
import os
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .auth import AuthError, AuthService, Principal
from .config import Settings
from .service import RogueService

logger = logging.getLogger("rogue.server")


class ActionRequest(BaseModel):
    command: str = Field(default="", max_length=4000)
    channel: Optional[str] = None
    name: Optional[str] = Field(default=None, max_length=64)
    force: bool = False
    prefixes: Optional[list[str]] = Field(default=None, max_length=8)


def _error(status_code: int, text: str, error: str, account: Optional[dict] = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "ok": False,
            "handled": True,
            "text": text,
            "error": error,
            "state": None,
            "account": account,
        },
    )


def _check_origin(request: Request, settings: Settings) -> None:
    if not settings.origin_key:
        return
    provided = request.headers.get("x-rogue-origin-key", "")
    if not provided or not hmac.compare_digest(provided, settings.origin_key):
        raise AuthError("请求来源校验失败。", 403, "origin")


async def _authenticate(request: Request, settings: Settings, auth: AuthService) -> Principal:
    _check_origin(request, settings)
    authorization = request.headers.get("authorization", "")
    if authorization.lower().startswith("bearer "):
        return await auth.verify_bearer(authorization[7:].strip())
    im_token = request.headers.get("x-rogue-im-token", "")
    im_user = request.headers.get("x-rogue-im-user", "")
    if im_token or im_user:
        return auth.verify_im(im_token, im_user)
    raise AuthError("缺少认证信息。")


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    settings = settings or Settings.from_env()
    service = RogueService(settings)
    auth = AuthService(settings)

    app = FastAPI(
        title="Card Roguelike Action API",
        version="2.0.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.service = service
    app.state.settings = settings
    app.state.auth = auth

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.allowed_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Rogue-IM-Token",
            "X-Rogue-IM-User",
            "X-Rogue-Admin-Token",
            "X-Rogue-Origin-Key",
        ],
        max_age=600,
    )

    @app.get("/healthz")
    async def healthz() -> dict:
        return {"ok": True, "service": "rogue", "v": 1}

    @app.post("/api/v1/action")
    async def action(payload: ActionRequest, request: Request):
        try:
            principal = await _authenticate(request, settings, auth)
        except AuthError as exc:
            return _error(exc.status_code, f"❌ {exc.message}", exc.code)
        except Exception:
            logger.exception("authentication failed")
            return _error(500, "❌ 服务器内部错误。", "internal")

        channel = (payload.channel or principal.kind).lower()
        if channel not in ("web", "im"):
            return _error(400, "❌ 无效的通道。", "bad_channel")
        if channel != principal.kind:
            return _error(403, "❌ 认证方式与请求通道不一致。", "channel_mismatch")

        is_admin = auth.verify_admin(request.headers.get("x-rogue-admin-token", ""))
        try:
            result = await service.handle(
                principal=principal,
                command=payload.command,
                channel=channel,
                display_name=payload.name or "",
                force=payload.force,
                is_admin=is_admin,
                prefixes=tuple(payload.prefixes) if payload.prefixes else None,
            )
            return JSONResponse(status_code=200, content=result)
        except AuthError as exc:
            return _error(exc.status_code, f"❌ {exc.message}", exc.code)
        except Exception:
            logger.exception("action failed")
            return _error(500, "❌ 服务器内部错误。", "internal")

    return app


def run() -> None:
    import uvicorn

    uvicorn.run(
        "server.app:create_app",
        factory=True,
        host=os.getenv("ROGUE_HOST", "127.0.0.1"),
        port=int(os.getenv("ROGUE_PORT", "8787")),
        workers=1,
        log_level=os.getenv("ROGUE_LOG_LEVEL", "info"),
    )


if __name__ == "__main__":
    run()
