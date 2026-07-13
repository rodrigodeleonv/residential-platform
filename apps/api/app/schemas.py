from typing import Self

from pydantic import BaseModel, ConfigDict


class MoneyRead(BaseModel):
    """Read schema whose amounts carry the deployment-wide currency."""

    model_config = ConfigDict(from_attributes=True)

    currency: str = ""

    @classmethod
    def of(cls, obj: object, currency: str) -> Self:
        read = cls.model_validate(obj)
        read.currency = currency
        return read
