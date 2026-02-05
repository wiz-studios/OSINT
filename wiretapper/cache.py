from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any


@dataclass
class _CacheItem:
    expires_at: float
    value: Any


_CACHE: dict[str, _CacheItem] = {}


def get(key: str) -> Any | None:
    item = _CACHE.get(key)
    if item is None:
        return None
    if time.monotonic() >= item.expires_at:
        _CACHE.pop(key, None)
        return None
    return item.value


def set(key: str, value: Any, *, ttl_s: float) -> None:
    _CACHE[key] = _CacheItem(expires_at=time.monotonic() + ttl_s, value=value)


def stats() -> dict[str, int]:
    # Best-effort (doesn't eagerly purge everything).
    return {"items": len(_CACHE)}
