from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditLog


async def record(
    db: AsyncSession,
    event: str,
    *,
    actor_id: int | None = None,
    target_user_id: int | None = None,
    data: dict[str, Any] | None = None,
) -> None:
    """Add an audit entry to the caller's transaction (committed or rolled back with it)."""
    db.add(
        AuditLog(
            event=event, actor_id=actor_id, target_user_id=target_user_id, data=data
        )
    )
