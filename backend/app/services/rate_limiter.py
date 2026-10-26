"""In-memory rate limiting and abuse protection for NammaPrayana APIs.

Provides sliding-window rate limiting per client IP address.
Suitable for single-worker or standard deployments; easily replaced or
backed by Redis (e.g. slowapi) for horizontally scaled multi-worker clusters.
"""

import threading
import time
from collections import defaultdict, deque
from fastapi import HTTPException, Request


def get_client_ip(request: Request) -> str:
    """Extract real client IP, respecting X-Forwarded-For if behind a reverse proxy."""
    forwarded = request.headers.get("x-forwarded-for") or request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"


class SlidingWindowRateLimiter:
    """Thread-safe sliding-window rate limiter per client IP."""

    def __init__(self, limit: int, window_seconds: int, error_message: str):
        self.limit = limit
        self.window_seconds = window_seconds
        self.error_message = error_message
        self._records = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, request: Request) -> None:
        ip = get_client_ip(request)
        now = time.time()
        cutoff = now - self.window_seconds

        with self._lock:
            q = self._records[ip]
            while q and q[0] < cutoff:
                q.popleft()

            if len(q) >= self.limit:
                retry_after = int(q[0] + self.window_seconds - now) + 1
                raise HTTPException(
                    status_code=429,
                    detail=self.error_message,
                    headers={"Retry-After": str(max(1, retry_after))},
                )

            q.append(now)

    def reset(self, ip: str | None = None) -> None:
        """Reset history (useful for automated testing)."""
        with self._lock:
            if ip:
                self._records.pop(ip, None)
            else:
                self._records.clear()


# Pre-configured rate limiters
auth_limiter = SlidingWindowRateLimiter(
    limit=20,
    window_seconds=60,
    error_message="Too many authentication requests. Please wait a moment before trying again.",
)

itinerary_limiter = SlidingWindowRateLimiter(
    limit=10,
    window_seconds=60,
    error_message="Itinerary generation rate limit reached (maximum 10 per minute). Please retry shortly.",
)

sahayak_limiter = SlidingWindowRateLimiter(
    limit=30,
    window_seconds=60,
    error_message="AI Assistant rate limit reached (maximum 30 per minute). Please retry shortly.",
)


def rate_limit_auth(request: Request) -> None:
    auth_limiter.check(request)


def rate_limit_itinerary(request: Request) -> None:
    itinerary_limiter.check(request)


def rate_limit_sahayak(request: Request) -> None:
    sahayak_limiter.check(request)
