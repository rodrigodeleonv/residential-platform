import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable

from fastapi import HTTPException, Request


class RateLimiter:
    """Sliding-window counter kept in process memory.

    The API runs as a single process (one uvicorn worker), so no shared
    store is needed; swap this for one if the app is ever replicated.
    """

    def __init__(self, limit: int, window_seconds: float) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._hits: defaultdict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        """Record a hit and report whether the key is still within its limit."""
        now = time.monotonic()
        hits = self._hits[key]
        while hits and hits[0] <= now - self.window_seconds:
            hits.popleft()
        if len(hits) >= self.limit:
            return False
        hits.append(now)
        return True


def rate_limit(scope: str) -> Callable[[Request], Awaitable[None]]:
    """Dependency that throttles an endpoint per client IP."""

    async def check(request: Request) -> None:
        limiter: RateLimiter = request.app.state.auth_rate_limiter
        client_ip = request.client.host if request.client else "unknown"
        if not limiter.allow(f"{scope}:{client_ip}"):
            raise HTTPException(
                status_code=429, detail="Too many attempts, try again later"
            )

    return check
