from pydantic import BaseModel, EmailStr


class RequestCode(BaseModel):
    email: EmailStr


class VerifyCode(BaseModel):
    email: EmailStr
    code: str
