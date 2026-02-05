from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class _Bucket:
    capacity: int
    refill_per_s: float
    tokens: float
    updated_at: float

    def allow(self, cost: float = 1.0) -> bool:
        now = time.monotonic()
        elapsed = max(0.0, now - self.updated_at)
        self.updated_at = now
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_per_s)
        if self.tokens >= cost:
            self.tokens -= cost
            return True
        return False


_BUCKETS: dict[str, _Bucket] = {}


def allow(key: str, *, per_minute: int) -> bool:
    # Token bucket: capacity=per_minute, refill continuously.
    bucket = _BUCKETS.get(key)
    if bucket is None or bucket.capacity != per_minute:
        bucket = _Bucket(
            capacity=per_minute,
            refill_per_s=per_minute / 60.0,
            tokens=float(per_minute),
            updated_at=time.monotonic(),
        )
        _BUCKETS[key] = bucket
    return bucket.allow(1.0)

