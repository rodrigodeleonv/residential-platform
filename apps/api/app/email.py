from dataclasses import dataclass
from typing import Annotated, Protocol

from fastapi import Depends, Request

from app.config import Settings


@dataclass(frozen=True, slots=True)
class EmailMessage:
    to: str
    subject: str
    body: str


class EmailProvider(Protocol):
    async def send(self, message: EmailMessage) -> None: ...


class ConsoleEmailProvider:
    """Development provider: prints emails to stdout instead of sending them."""

    async def send(self, message: EmailMessage) -> None:
        print(
            f"--- email to {message.to} ---\n{message.subject}\n\n{message.body}\n---"
        )


def create_email_provider(settings: Settings) -> EmailProvider:
    match settings.email_provider:
        case "console":
            return ConsoleEmailProvider()


def get_email_provider(request: Request) -> EmailProvider:
    return request.app.state.email_provider


EmailDep = Annotated[EmailProvider, Depends(get_email_provider)]
