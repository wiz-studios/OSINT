from __future__ import annotations

import random
from typing import Any

from flask import Blueprint, current_app, jsonify, render_template, request

from . import cache, ratelimit
from .config import Settings
from .data import DUMMY_DATA
from .errors import UpstreamError
from .services import opencellid, shodan, wigle

bp = Blueprint("wiretapper", __name__)


def _settings() -> Settings:
    settings = current_app.config.get("WIRETAPPER_SETTINGS")
    if not isinstance(settings, Settings):
        raise RuntimeError("WIRETAPPER_SETTINGS missing or invalid")
    return settings


def _client_key() -> str:
    forwarded = (request.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
    return forwarded or request.remote_addr or "unknown"


def _enforce_rate_limit(bucket: str, *, per_minute: int) -> None:
    key = f"{bucket}:{_client_key()}"
    if not ratelimit.allow(key, per_minute=per_minute):
        raise PermissionError("Rate limit exceeded. Please slow down.")


def classify_device(name: str | None, original_type: str) -> str:
    if not name:
        return original_type
    name_upper = name.upper()
    if any(
        k in name_upper
        for k in [
            "CAR",
            "FORD",
            "TOYOTA",
            "BMW",
            "TESLA",
            "SYNC",
            "MAZDA",
            "HONDA",
            "UCONNECT",
            "HYUNDAI",
            "LEXUS",
            "NISSAN",
        ]
    ):
        return "car"
    if any(
        k in name_upper
        for k in ["TV", "BRAVIA", "VIZIO", "SAMSUNG", "LG", "ROKU", "FIRE", "SMARTVIEW", "KDL-"]
    ):
        return "tv"
    if any(
        k in name_upper
        for k in [
            "HEADPHONE",
            "EARBUD",
            "BOSE",
            "SONY",
            "BEATS",
            "AUDIO",
            "AIRPOD",
            "JBL",
            "SENNHEISER",
        ]
    ):
        return "headphone"
    if any(
        k in name_upper for k in ["DASHCAM", "DASH CAM", "DVR", "70MAI", "VIOFO", "GARMIN DASH"]
    ):
        return "dashcam"
    if any(
        k in name_upper
        for k in [
            "CAM",
            "SURVEILLANCE",
            "SECURITY",
            "NEST",
            "RING",
            "ARLO",
            "HIKVISION",
            "DAHUA",
            "REOLINK",
        ]
    ):
        return "camera"
    if any(k in name_upper for k in ["WATCH", "FITBIT", "GARMIN", "WHOOP"]):
        return "iot"
    return original_type


def _dummy_devices_for_nearby(*, lat: float, lon: float, mode: str) -> list[dict[str, Any]]:
    if mode == "bluetooth":
        return [
            {
                "lat": lat + random.uniform(-0.002, 0.002),
                "lon": lon + random.uniform(-0.002, 0.002),
                "ssid": "Tesla Model 3",
                "type": "car",
                "vendor": "Tesla Motors",
            },
            {
                "lat": lat + random.uniform(-0.002, 0.002),
                "lon": lon + random.uniform(-0.002, 0.002),
                "ssid": "Sony WH-1000XM4",
                "type": "headphone",
                "vendor": "Sony Corp.",
            },
            {
                "lat": lat + random.uniform(-0.002, 0.002),
                "lon": lon + random.uniform(-0.002, 0.002),
                "ssid": "Samsung QLED 75",
                "type": "tv",
                "vendor": "Samsung Electronics",
            },
            {
                "lat": lat + random.uniform(-0.002, 0.002),
                "lon": lon + random.uniform(-0.002, 0.002),
                "ssid": "Hidden_BT_Tracker",
                "type": "bluetooth",
                "vendor": "Unknown",
            },
        ]
    return [
        {
            "lat": lat + random.uniform(-0.001, 0.001),
            "lon": lon + random.uniform(-0.001, 0.001),
            "ssid": "CYBER_SURVEILLANCE_ROUTER",
            "type": "router",
            "vendor": "Cisco Systems",
        },
        {
            "lat": lat + random.uniform(-0.001, 0.001),
            "lon": lon + random.uniform(-0.001, 0.001),
            "ssid": "DASHCAM_V3",
            "type": "camera",
            "vendor": "Nextbase",
        },
        {
            "lat": lat + random.uniform(-0.001, 0.001),
            "lon": lon + random.uniform(-0.001, 0.001),
            "ssid": "5G_TOWER_B4",
            "type": "cell_tower",
            "vendor": "Ericsson",
        },
    ]


@bp.get("/map-w")
def wifi_map():
    return render_template("wifi-search.html")


@bp.get("/api/status")
def api_status():
    settings = _settings()
    return jsonify(
        {
            "providers": {
                "wigle": bool(settings.wigle_api_name and settings.wigle_api_token),
                "opencellid": bool(settings.opencellid_api_key),
                "shodan": bool(settings.shodan_api_key),
            },
            "limits": {"rate_limit_rpm": settings.rate_limit_rpm},
            "cache_ttl_s": {
                "nearby": settings.cache_ttl_nearby_s,
                "search": settings.cache_ttl_search_s,
                "towers": settings.cache_ttl_towers_s,
            },
            "cache": cache.stats(),
        }
    )


@bp.get("/nearby")
def nearby():
    settings = _settings()

    lat = request.args.get("lat", type=float)
    lon = request.args.get("lon", type=float)
    mode = request.args.get("mode", "wifi")

    if not lat or not lon:
        return jsonify({"error": "Missing coordinates"}), 400

    devices: list[dict[str, Any]] = []
    meta: dict[str, Any] = {"cached": False}

    try:
        _enforce_rate_limit("nearby", per_minute=settings.rate_limit_rpm)
    except PermissionError as e:
        return jsonify({"error": str(e)}), 429

    if mode == "bluetooth":
        if settings.wigle_api_name and settings.wigle_api_token:
            cache_key = f"wigle:bt:{lat:.4f}:{lon:.4f}"
            cached = cache.get(cache_key)
            if cached is None:
                try:
                    cached = wigle.bluetooth_search(
                        api_name=settings.wigle_api_name,
                        api_token=settings.wigle_api_token,
                        lat=lat,
                        lon=lon,
                    )
                except UpstreamError as e:
                    return jsonify({"error": str(e)}), 502
                cache.set(cache_key, cached, ttl_s=settings.cache_ttl_nearby_s)
            else:
                meta["cached"] = True

            for device in cached:
                name = device.get("name") or device.get("netid")
                classified_type = classify_device(str(name) if name else None, "bluetooth")
                devices.append(
                    {
                        "lat": device.get("trilat"),
                        "lon": device.get("trilong"),
                        "ssid": name,
                        "bssid": device.get("netid"),
                        "vendor": device.get("type")
                        or (
                            "Bluetooth Node"
                            if classified_type == "bluetooth"
                            else classified_type.replace("_", " ").title()
                        ),
                        "signal": device.get("level"),
                        "timestamp": device.get("lastupdt"),
                        "type": classified_type,
                    }
                )
    else:
        if settings.wigle_api_name and settings.wigle_api_token:
            cache_key = f"wigle:wifi:{lat:.4f}:{lon:.4f}"
            cached = cache.get(cache_key)
            if cached is None:
                try:
                    cached = wigle.network_search(
                        api_name=settings.wigle_api_name,
                        api_token=settings.wigle_api_token,
                        lat=lat,
                        lon=lon,
                    )
                except UpstreamError as e:
                    return jsonify({"error": str(e)}), 502
                cache.set(cache_key, cached, ttl_s=settings.cache_ttl_nearby_s)
            else:
                meta["cached"] = True

            for network in cached:
                name = network.get("ssid")
                classified_type = classify_device(str(name) if name else None, "router")
                devices.append(
                    {
                        "lat": network.get("trilat"),
                        "lon": network.get("trilong"),
                        "ssid": name,
                        "bssid": network.get("netid"),
                        "vendor": network.get("vendor"),
                        "signal": network.get("level"),
                        "timestamp": network.get("lastupdt"),
                        "type": classified_type,
                    }
                )

        if settings.opencellid_api_key:
            cache_key = f"unwired:{lat:.4f}:{lon:.4f}"
            data = cache.get(cache_key)
            if data is None:
                try:
                    data = opencellid.unwiredlabs_process(
                        token=settings.opencellid_api_key, lat=lat, lon=lon
                    )
                except UpstreamError as e:
                    return jsonify({"error": str(e)}), 502
                cache.set(cache_key, data, ttl_s=settings.cache_ttl_nearby_s)
            else:
                meta["cached"] = True
            if data and data.get("status") == "ok":
                for cell in data.get("cells", []) or []:
                    devices.append(
                        {
                            "lat": cell.get("lat"),
                            "lon": cell.get("lon"),
                            "cell_id": str(cell.get("cellid")),
                            "signal": cell.get("signal"),
                            "accuracy": cell.get("accuracy"),
                            "timestamp": cell.get("updated"),
                            "type": "cell_tower",
                        }
                    )

        if settings.shodan_api_key:
            cache_key = f"shodan:geo:{lat:.4f}:{lon:.4f}"
            cached = cache.get(cache_key)
            if cached is None:
                try:
                    cached = shodan.host_search(
                        api_key=settings.shodan_api_key,
                        query=f"geo:{lat},{lon},1",
                        limit=5,
                    )
                except UpstreamError as e:
                    return jsonify({"error": str(e)}), 502
                cache.set(cache_key, cached, ttl_s=settings.cache_ttl_nearby_s)
            else:
                meta["cached"] = True

            for banner in cached:
                info = banner.get("data", "")
                location = banner.get("location", {}) or {}
                devices.append(
                    {
                        "lat": location.get("latitude"),
                        "lon": location.get("longitude"),
                        "ip": banner.get("ip_str"),
                        "info": str(info)[:50],
                        "type": classify_device(str(info) if info else None, "iot_device"),
                    }
                )

    if not devices:
        devices = _dummy_devices_for_nearby(lat=lat, lon=lon, mode=mode)

    return jsonify({"devices": devices, "meta": meta})


@bp.get("/api/geo/towers")
def get_towers():
    settings = _settings()

    lat = request.args.get("lat", type=float)
    lon = request.args.get("lon", type=float)
    if not lat or not lon:
        lat = 51.505
        lon = -0.09

    if not settings.opencellid_api_key:
        return jsonify({"error": "Missing OPENCELLID_API_KEY"}), 400

    try:
        _enforce_rate_limit("towers", per_minute=settings.rate_limit_rpm)
    except PermissionError as e:
        return jsonify({"error": str(e)}), 429

    min_lat = lat - 0.05
    max_lat = lat + 0.05
    min_lon = lon - 0.05
    max_lon = lon + 0.05
    bbox = f"{min_lat},{min_lon},{max_lat},{max_lon}"

    cache_key = f"opencellid:area:{bbox}"
    data = cache.get(cache_key)
    if data is None:
        try:
            data = opencellid.get_in_area(key=settings.opencellid_api_key, bbox=bbox)
        except UpstreamError as e:
            return jsonify({"error": str(e)}), 502
        if data is None:
            return jsonify({"error": "Upstream API error"}), 502
        cache.set(cache_key, data, ttl_s=settings.cache_ttl_towers_s)

    cells = data.get("cells", []) if isinstance(data, dict) else data
    towers: list[dict[str, Any]] = []
    if isinstance(cells, list):
        for cell in cells:
            towers.append(
                {
                    "id": str(cell.get("cellid", "Unknown")),
                    "lat": float(cell.get("lat")),
                    "lon": float(cell.get("lon")),
                    "lac": cell.get("lac", 0),
                    "mcc": cell.get("mcc", 0),
                    "mnc": cell.get("mnc", 0),
                    "signal": cell.get("signal", 0),
                    "radio": cell.get("radio", "gsm"),
                }
            )
    return jsonify(towers)


@bp.get("/api/geo/celltower")
def get_celltower_click():
    settings = _settings()

    lat = request.args.get("lat", type=float)
    lon = request.args.get("lon", type=float)
    if not lat or not lon:
        return jsonify({"error": "Missing coordinates"}), 400

    try:
        _enforce_rate_limit("celltower", per_minute=settings.rate_limit_rpm)
    except PermissionError as e:
        return jsonify({"error": str(e)}), 429

    min_lat = lat - 0.01
    max_lat = lat + 0.01
    min_lon = lon - 0.01
    max_lon = lon + 0.01
    bbox = f"{min_lon},{min_lat},{max_lon},{max_lat}"

    cache_key = f"opencellid:ajax:{bbox}"
    data = cache.get(cache_key)
    if data is None:
        try:
            data = opencellid.ajax_get_cells(bbox=bbox)
        except UpstreamError as e:
            return jsonify({"error": str(e)}), 502
        if not data:
            return jsonify({"error": "Upstream API error"}), 502
        cache.set(cache_key, data, ttl_s=settings.cache_ttl_towers_s)

    towers: list[dict[str, Any]] = []
    features = data.get("features", []) if isinstance(data, dict) else []
    for feature in features:
        props = feature.get("properties", {}) or {}
        geom = feature.get("geometry", {}) or {}
        coords = geom.get("coordinates", [0, 0])
        towers.append(
            {
                "id": str(props.get("cellid", props.get("unit", "Unknown"))),
                "lat": float(coords[1]),
                "lon": float(coords[0]),
                "lac": props.get("area", 0),
                "mcc": props.get("mcc", 0),
                "mnc": props.get("net", 0),
                "signal": props.get("samples", 0),
                "radio": props.get("radio", "gsm"),
            }
        )
    return jsonify(towers)


@bp.get("/searchzz")
def search():
    settings = _settings()

    search_type = request.args.get("type")
    query = request.args.get("query")
    if not search_type or not query:
        return jsonify({"error": "Missing search parameters"}), 400

    devices: list[dict[str, Any]] = []

    try:
        _enforce_rate_limit("search", per_minute=settings.rate_limit_rpm)
    except PermissionError as e:
        return jsonify({"error": str(e)}), 429

    if search_type == "location":
        try:
            lat, lon = map(float, query.split(","))
        except Exception:
            return jsonify({"error": "Invalid location format"}), 400

        if settings.wigle_api_name and settings.wigle_api_token:
            cache_key = f"search:wigle:loc:{lat:.4f}:{lon:.4f}"
            cached = cache.get(cache_key)
            if cached is None:
                try:
                    cached = wigle.network_search(
                        api_name=settings.wigle_api_name,
                        api_token=settings.wigle_api_token,
                        lat=lat,
                        lon=lon,
                    )
                except UpstreamError as e:
                    return jsonify({"error": str(e)}), 502
                cache.set(cache_key, cached, ttl_s=settings.cache_ttl_search_s)

            for network in cached:
                devices.append(
                    {
                        "lat": network.get("trilat"),
                        "lon": network.get("trilong"),
                        "ssid": network.get("ssid"),
                        "bssid": network.get("netid"),
                        "vendor": network.get("vendor"),
                        "signal": network.get("level"),
                        "timestamp": network.get("lastupdt"),
                        "type": "router",
                    }
                )

        if settings.opencellid_api_key:
            cache_key = f"search:unwired:loc:{lat:.4f}:{lon:.4f}"
            data = cache.get(cache_key)
            if data is None:
                try:
                    data = opencellid.unwiredlabs_process(
                        token=settings.opencellid_api_key, lat=lat, lon=lon
                    )
                except UpstreamError as e:
                    return jsonify({"error": str(e)}), 502
                cache.set(cache_key, data, ttl_s=settings.cache_ttl_search_s)
            if data and data.get("status") == "ok":
                for cell in data.get("cells", []) or []:
                    devices.append(
                        {
                            "lat": cell.get("lat"),
                            "lon": cell.get("lon"),
                            "cell_id": str(cell.get("cellid")),
                            "signal": cell.get("signal"),
                            "accuracy": cell.get("accuracy"),
                            "timestamp": cell.get("updated"),
                            "type": "cell_tower",
                        }
                    )

    elif search_type == "bssid":
        if settings.wigle_api_name and settings.wigle_api_token:
            cache_key = f"search:wigle:bssid:{query}"
            cached = cache.get(cache_key)
            if cached is None:
                try:
                    cached = wigle.search_by_bssid(
                        api_name=settings.wigle_api_name,
                        api_token=settings.wigle_api_token,
                        bssid=query,
                    )
                except UpstreamError as e:
                    return jsonify({"error": str(e)}), 502
                cache.set(cache_key, cached, ttl_s=settings.cache_ttl_search_s)

            for network in cached:
                devices.append(
                    {
                        "lat": network.get("trilat"),
                        "lon": network.get("trilong"),
                        "ssid": network.get("ssid"),
                        "bssid": network.get("netid"),
                        "vendor": network.get("vendor"),
                        "signal": network.get("level"),
                        "timestamp": network.get("lastupdt"),
                        "type": "router",
                    }
                )

    elif search_type == "ssid":
        if settings.wigle_api_name and settings.wigle_api_token:
            cache_key = f"search:wigle:ssid:{query}"
            cached = cache.get(cache_key)
            if cached is None:
                try:
                    cached = wigle.search_by_ssid(
                        api_name=settings.wigle_api_name,
                        api_token=settings.wigle_api_token,
                        ssid=query,
                    )
                except UpstreamError as e:
                    return jsonify({"error": str(e)}), 502
                cache.set(cache_key, cached, ttl_s=settings.cache_ttl_search_s)

            for network in cached:
                devices.append(
                    {
                        "lat": network.get("trilat"),
                        "lon": network.get("trilong"),
                        "ssid": network.get("ssid"),
                        "bssid": network.get("netid"),
                        "vendor": network.get("vendor"),
                        "signal": network.get("level"),
                        "timestamp": network.get("lastupdt"),
                        "type": "router",
                    }
                )

    elif search_type == "network":
        if settings.shodan_api_key:
            cache_key = f"search:shodan:{query}"
            cached = cache.get(cache_key)
            if cached is None:
                try:
                    cached = shodan.host_search(api_key=settings.shodan_api_key, query=query)
                except UpstreamError as e:
                    return jsonify({"error": str(e)}), 502
                cache.set(cache_key, cached, ttl_s=settings.cache_ttl_search_s)

            for host in cached:
                devices.append(
                    {
                        "lat": (host.get("location", {}) or {}).get("latitude"),
                        "lon": (host.get("location", {}) or {}).get("longitude"),
                        "ip": host.get("ip_str"),
                        "vendor": host.get("org"),
                        "type": host.get("product", "iot"),
                    }
                )

    if not devices and search_type in {"location", "ssid", "bssid", "network"}:
        if search_type == "location":
            lat, lon = map(float, query.split(","))
            devices = [
                d for d in DUMMY_DATA if abs(d["lat"] - lat) < 0.1 and abs(d["lon"] - lon) < 0.1
            ]
        elif search_type == "ssid":
            devices = [d for d in DUMMY_DATA if (d.get("ssid", "") or "").lower() == query.lower()]
        elif search_type == "bssid":
            devices = [d for d in DUMMY_DATA if (d.get("bssid", "") or "").lower() == query.lower()]
        elif search_type == "network":
            devices = [d for d in DUMMY_DATA if (d.get("ip", "") or "") == query]

    return jsonify({"devices": devices})
