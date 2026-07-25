from collections import defaultdict, deque
from collections.abc import Callable
from threading import Lock
from time import monotonic

from fastapi import HTTPException, Request, status


class SlidingWindowRateLimiter:
    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def dependency(self, *, limit: int, window_seconds: int) -> Callable[[Request], None]:
        def check(request: Request) -> None:
            forwarded = request.headers.get("x-forwarded-for", "")
            client = forwarded.split(",", maxsplit=1)[0].strip()
            if not client:
                client = request.client.host if request.client else "unknown"
            key = f"{request.url.path}:{client}"
            now = monotonic()

            with self._lock:
                events = self._events[key]
                while events and events[0] <= now - window_seconds:
                    events.popleft()
                if len(events) >= limit:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Too many requests. Please wait and try again.",
                    )
                events.append(now)

        return check


rate_limiter = SlidingWindowRateLimiter()
