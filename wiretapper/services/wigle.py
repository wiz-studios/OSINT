from __future__ import annotations

from typing import Any

from .http import get


def bluetooth_search(
    *,
    api_name: str,
    api_token: str,
    lat: float,
    lon: float,
    delta: float = 0.01,
) -> list[dict[str, Any]]:
    response = get(
        "https://api.wigle.net/api/v2/bluetooth/search",
        params={
            "latrange1": lat - delta,
            "latrange2": lat + delta,
            "longrange1": lon - delta,
            "longrange2": lon + delta,
        },
        auth=(api_name, api_token),
    )
    if response.status_code != 200:
        return []
    return response.json().get("results", []) or []


def network_search(
    *,
    api_name: str,
    api_token: str,
    lat: float,
    lon: float,
    delta: float = 0.01,
) -> list[dict[str, Any]]:
    response = get(
        "https://api.wigle.net/api/v2/network/search",
        params={
            "latrange1": lat - delta,
            "latrange2": lat + delta,
            "longrange1": lon - delta,
            "longrange2": lon + delta,
        },
        auth=(api_name, api_token),
    )
    if response.status_code != 200:
        return []
    return response.json().get("results", []) or []


def search_by_bssid(*, api_name: str, api_token: str, bssid: str) -> list[dict[str, Any]]:
    response = get(
        "https://api.wigle.net/api/v2/network/search",
        params={"netid": bssid},
        auth=(api_name, api_token),
    )
    return response.json().get("results", []) or []


def search_by_ssid(*, api_name: str, api_token: str, ssid: str) -> list[dict[str, Any]]:
    response = get(
        "https://api.wigle.net/api/v2/network/search",
        params={"ssid": ssid},
        auth=(api_name, api_token),
    )
    return response.json().get("results", []) or []
