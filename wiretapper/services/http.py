from __future__ import annotations

from typing import Any

import requests

from ..errors import UpstreamError

DEFAULT_TIMEOUT_S = 10
_SESSION = requests.Session()
_SESSION.headers.update(
    {
        "User-Agent": "WireTapper/0.0 (+https://github.com/h9zdev/WireTapper)",
        "Accept": "application/json,text/plain;q=0.9,*/*;q=0.1",
    }
)


def _raise_for_status(response: requests.Response) -> None:
    if 200 <= response.status_code < 300:
        return
    raise UpstreamError(
        f"Upstream API error: HTTP {response.status_code}",
        status_code=response.status_code,
    )


def _request(method: str, url: str, **kwargs: Any) -> requests.Response:
    try:
        response = _SESSION.request(method, url, timeout=DEFAULT_TIMEOUT_S, **kwargs)
    except requests.RequestException as exc:
        raise UpstreamError("Upstream request failed") from exc
    _raise_for_status(response)
    return response


def get(
    url: str, *, params: dict[str, Any] | None = None, auth: Any | None = None
) -> requests.Response:
    return _request("GET", url, params=params, auth=auth)


def post_json(url: str, *, payload: dict[str, Any]) -> requests.Response:
    return _request("POST", url, json=payload)


def get_json(url: str, *, params: dict[str, Any] | None = None) -> requests.Response:
    return _request("GET", url, params=params)
