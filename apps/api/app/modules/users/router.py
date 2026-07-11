from fastapi import APIRouter, HTTPException

from app.config import SettingsDep
from app.db import DbSession
from app.email import EmailDep
from app.modules.auth.deps import AdminUser, CurrentUser
from app.modules.users import service
from app.modules.users.schemas import UserCreate, UserRead

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
async def read_me(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)


@router.post("", status_code=201)
async def create_user(
    payload: UserCreate,
    admin: AdminUser,
    db: DbSession,
    provider: EmailDep,
    settings: SettingsDep,
) -> UserRead:
    try:
        user = await service.create_user(
            db, payload, actor=admin, provider=provider, settings=settings
        )
    except service.EmailAlreadyRegistered:
        raise HTTPException(
            status_code=409, detail="Email already registered"
        ) from None
    return UserRead.model_validate(user)


@router.get("")
async def list_users(admin: AdminUser, db: DbSession) -> list[UserRead]:
    return [UserRead.model_validate(user) for user in await service.list_users(db)]
