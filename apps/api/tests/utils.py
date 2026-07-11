import re

from httpx import AsyncClient, Response

API = "/api/v0"


def extract_code(body: str) -> str:
    match = re.search(r"login code is: (\d{6})", body)
    assert match, f"no login code found in email body: {body!r}"
    return match.group(1)


def extract_magic_token(body: str) -> str:
    match = re.search(r"token=([A-Za-z0-9_-]+)", body)
    assert match, f"no magic token found in email body: {body!r}"
    return match.group(1)


def wrong_code(code: str) -> str:
    return "000000" if code != "000000" else "000001"


async def request_code(client: AsyncClient, email: str) -> Response:
    response = await client.post(f"{API}/auth/request-code", json={"email": email})
    assert response.status_code == 202
    return response
