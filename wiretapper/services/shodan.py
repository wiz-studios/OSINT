from __future__ import annotations

from typing import Any

from .http import get


def host_search(*, api_key: str, query: str, limit: int | None = None) -> list[dict[str, Any]]:
    params: dict[str, Any] = {"key": api_key, "query": query}
    if limit is not None:
        params["limit"] = limit
    response = get("https://api.shodan.io/shodan/host/search", params=params)
    return response.json().get("matches", []) or []
