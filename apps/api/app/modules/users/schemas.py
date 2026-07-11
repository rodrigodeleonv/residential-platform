from pydantic import BaseModel, ConfigDict, EmailStr

from app.modules.users.models import Role


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    phone: str | None = None
    roles: set[Role] = set()
    send_invitation: bool = True


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    phone: str | None
    is_active: bool
    roles: set[Role]
