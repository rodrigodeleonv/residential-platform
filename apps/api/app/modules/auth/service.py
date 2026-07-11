import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import API_PREFIX, Settings
from app.email import EmailMessage, EmailProvider
from app.modules.audit import service as audit
from app.modules.auth.models import AuthSession, LoginCode
from app.modules.users.models import User


def hash_token(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _now() -> datetime:
    return datetime.now(UTC)


async def issue_login_code(
    db: AsyncSession, user: User, settings: Settings
) -> tuple[str, str]:
    """Create a one-time credential; returns (code, magic_token) in plain text."""
    code = f"{secrets.randbelow(1_000_000):06d}"
    magic_token = secrets.token_urlsafe(32)
    db.add(
        LoginCode(
            user_id=user.id,
            code_hash=hash_token(code),
            magic_token_hash=hash_token(magic_token),
            expires_at=_now() + timedelta(minutes=settings.login_code_ttl_minutes),
        )
    )
    await db.flush()
    return code, magic_token


def _login_email(
    user: User, code: str, magic_token: str, settings: Settings, *, invitation: bool
) -> EmailMessage:
    link = f"{settings.app_base_url}{API_PREFIX}/auth/magic?token={magic_token}"
    greeting = (
        f"Hello {user.full_name}, you have been invited to Residential Platform."
        if invitation
        else f"Hello {user.full_name},"
    )
    return EmailMessage(
        to=user.email,
        subject="Your login code"
        if not invitation
        else "Welcome to Residential Platform",
        body=(
            f"{greeting}\n\n"
            f"Your login code is: {code}\n"
            f"Or open this link to sign in directly: {link}\n\n"
            f"The code and link expire in {settings.login_code_ttl_minutes} minutes."
        ),
    )


async def send_login_email(
    db: AsyncSession,
    user: User,
    provider: EmailProvider,
    settings: Settings,
    *,
    invitation: bool = False,
) -> None:
    code, magic_token = await issue_login_code(db, user, settings)
    await provider.send(
        _login_email(user, code, magic_token, settings, invitation=invitation)
    )


async def request_login_code(
    db: AsyncSession, email: str, provider: EmailProvider, settings: Settings
) -> None:
    """Silently does nothing for unknown/inactive emails (no account enumeration)."""
    user = await db.scalar(
        select(User).where(User.email == email.lower(), User.is_active)
    )
    if user is not None:
        await send_login_email(db, user, provider, settings)


async def verify_code(
    db: AsyncSession, email: str, code: str, settings: Settings
) -> str | None:
    """Return a new session token if the code is valid for that email."""
    user = await db.scalar(
        select(User).where(User.email == email.lower(), User.is_active)
    )
    if user is None:
        return None
    login_code = await db.scalar(
        select(LoginCode)
        .where(
            LoginCode.user_id == user.id,
            LoginCode.consumed_at.is_(None),
            LoginCode.expires_at > _now(),
            LoginCode.attempts < settings.login_code_max_attempts,
        )
        .order_by(LoginCode.created_at.desc())
        .limit(1)
    )
    if login_code is None:
        return None
    if login_code.code_hash != hash_token(code):
        login_code.attempts += 1
        return None
    return await _open_session(db, login_code, user, settings)


async def verify_magic_token(
    db: AsyncSession, token: str, settings: Settings
) -> str | None:
    """Return a new session token if the magic-link token is valid."""
    login_code = await db.scalar(
        select(LoginCode).where(
            LoginCode.magic_token_hash == hash_token(token),
            LoginCode.consumed_at.is_(None),
            LoginCode.expires_at > _now(),
        )
    )
    if login_code is None:
        return None
    user = await db.get(User, login_code.user_id)
    if user is None or not user.is_active:
        return None
    return await _open_session(db, login_code, user, settings)


async def _open_session(
    db: AsyncSession, login_code: LoginCode, user: User, settings: Settings
) -> str:
    login_code.consumed_at = _now()
    token = secrets.token_urlsafe(32)
    db.add(
        AuthSession(
            user_id=user.id,
            token_hash=hash_token(token),
            expires_at=_now() + timedelta(days=settings.session_ttl_days),
        )
    )
    await audit.record(db, "login", actor_id=user.id)
    await db.flush()
    return token


async def get_user_by_session_token(db: AsyncSession, token: str) -> User | None:
    return await db.scalar(
        select(User)
        .join(AuthSession, AuthSession.user_id == User.id)
        .where(
            AuthSession.token_hash == hash_token(token),
            AuthSession.expires_at > _now(),
            User.is_active,
        )
    )


async def logout(db: AsyncSession, token: str) -> None:
    auth_session = await db.scalar(
        select(AuthSession).where(AuthSession.token_hash == hash_token(token))
    )
    if auth_session is not None:
        await audit.record(db, "logout", actor_id=auth_session.user_id)
        await db.delete(auth_session)
