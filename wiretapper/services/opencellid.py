from __future__ import annotations

from typing import Any

import requests

from .http import get, get_json, post_json


def unwiredlabs_process(*, token: str, lat: float, lon: float) -> dict[str, Any] | None:
    response = post_json(
        "https://us1.unwiredlabs.com/v2/process.php",
        payload={"token": token, "lat": lat, "lon": lon, "address": 0},
    )
    return response.json()


def get_in_area(*, key: str, bbox: str) -> dict[str, Any] | list[Any] | None:
    response = get(
        "http://opencellid.org/cell/getInArea",
        params={"key": key, "BBOX": bbox, "format": "json"},
    )
    try:
        return response.json()
    except requests.JSONDecodeError:
        return None


def ajax_get_cells(*, bbox: str) -> dict[str, Any] | None:
    response = get_json("https://www.opencellid.org/ajax/getCells.php", params={"bbox": bbox})
    return response.json()
