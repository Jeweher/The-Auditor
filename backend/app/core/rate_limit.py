"""
File: app/core/rate_limit.py
Folder: backend/app/core
Purpose: A minimal in-memory sliding-window rate limiter for public,
         unauthenticated endpoints. Good enough for a single-process dev/
         small-deployment server; not shared across multiple workers or
         instances — swap for a Redis-backed limiter before scaling out
         horizontally.
"""

import time
from collections import defaultdict, deque


class InMemoryRateLimiter:
    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self._max = max_requests
        self._window = window_seconds
        self._hits: dict[str, deque] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.time()
        bucket = self._hits[key]
        while bucket and now - bucket[0] > self._window:
            bucket.popleft()
        if len(bucket) >= self._max:
            return False
        bucket.append(now)
        return True


# 15 questions per hour per IP for the public TISAX Teacher widget.
public_assistant_rate_limiter = InMemoryRateLimiter(max_requests=15, window_seconds=3600)

# 5 resend requests per hour per IP for email verification.
resend_verification_rate_limiter = InMemoryRateLimiter(max_requests=5, window_seconds=3600)