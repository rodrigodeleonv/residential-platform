from fastapi import APIRouter, Depends, Response
from fastapi.responses import JSONResponse

from app.config import Settings, SettingsDep
from app.db import DbSession
from app.email import EmailDep
from app.modules.auth import service
from app.modules.auth.deps import SESSION_COOKIE, SessionCookie
from app.modules.auth.schemas import RequestCode, VerifyCode
from app.rate_limit import rate_limit

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_session_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=settings.session_ttl_days * 24 * 3600,
        httponly=True,
        samesite="lax",
        secure=settings.environment == "production",
    )


def _invalid_credentials() -> JSONResponse:
    # Failed logins return a response instead of raising HTTPException so the
    # request transaction still commits (failed-attempt counters must persist).
    return JSONResponse(
        status_code=401, content={"detail": "Invalid or expired credentials"}
    )


@router.post(
    "/request-code",
    status_code=202,
    dependencies=[Depends(rate_limit("request-code"))],
)
async def request_code(
    payload: RequestCode, db: DbSession, provider: EmailDep, settings: SettingsDep
) -> dict[str, str]:
    await service.request_login_code(db, payload.email, provider, settings)
    return {"detail": "If the email is registered, a login code was sent"}


@router.post("/verify", dependencies=[Depends(rate_limit("verify"))])
async def verify_code(
    payload: VerifyCode, db: DbSession, settings: SettingsDep
) -> Response:
    token = await service.verify_code(db, payload.email, payload.code, settings)
    if token is None:
        return _invalid_credentials()
    response = JSONResponse({"detail": "Logged in"})
    _set_session_cookie(response, token, settings)
    return response


@router.get("/magic", dependencies=[Depends(rate_limit("magic"))])
async def magic_link(token: str, db: DbSession, settings: SettingsDep) -> Response:
    session_token = await service.verify_magic_token(db, token, settings)
    if session_token is None:
        return _invalid_credentials()
    response = JSONResponse({"detail": "Logged in"})
    _set_session_cookie(response, session_token, settings)
    return response


@router.post("/logout", status_code=204)
async def logout(db: DbSession, session_token: SessionCookie = None) -> Response:
    if session_token is not None:
        await service.logout(db, session_token)
    response = Response(status_code=204)
    response.delete_cookie(SESSION_COOKIE)
    return response
