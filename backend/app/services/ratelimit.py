from __future__ import annotations

from collections import defaultdict
from time import time

from app.errors import AccrueError


class SlidingWindowLimiter:
    def __init__(self, limit: int, window_seconds: int = 60) -> None:
        self.limit = limit
        self.window = window_seconds
        self.events: dict[str, list[float]] = defaultdict(list)

    def hit(self, key: str) -> None:
        now = time()
        bucket = [stamp for stamp in self.events[key] if now - stamp < self.window]
        if len(bucket) >= self.limit:
            raise AccrueError("RATE_LIMITED", "Too many analyze requests. Wait a moment and retry.", 429)
        bucket.append(now)
        self.events[key] = bucket
