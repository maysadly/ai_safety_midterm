"""Rate limit for /api/chat: at most N requests per key in the last 60 seconds.

The key is the hashed client IP (see main.py). Sliding window: for every key we
keep the times of its recent requests and drop those older than a minute.
Switched off with RATE_LIMIT_ENABLED=false in .env for experiment runs.
"""

import threading
import time
from collections import defaultdict, deque


class RateLimiter:
    def __init__(self, limit_per_minute: int, clock=time.monotonic):
        self.limit = limit_per_minute
        self.clock = clock  # replaceable in tests
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = self.clock()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] >= 60:
                hits.popleft()
            if len(hits) >= self.limit:
                return False
            hits.append(now)
            return True
